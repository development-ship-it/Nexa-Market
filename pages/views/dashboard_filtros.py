"""Resuelve el filtro de período del dashboard a un rango de fechas.

El usuario elige una granularidad (día/semana/mes/año) sobre una fecha ancla
—que arranca en hoy— o marca «Histórico» para ver todo sin límite de fecha.
"""
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date

from .agrupamiento import MESES_DICT

PERIODOS = ('dia', 'semana', 'mes', 'anio')

# (valor, etiqueta) de los chips de granularidad, en orden
PERIODO_OPCIONES = [
    ('dia', 'Día'), ('semana', 'Semana'), ('mes', 'Mes'), ('anio', 'Año'),
]


def resolver_periodo(request):
    """Lee ?periodo, ?fecha y ?historico y los normaliza a un rango de fechas.

    Devuelve un dict con:
      historico  bool — si True, sin límite de fecha (desde/hasta = None)
      sel        'dia'|'semana'|'mes'|'anio' — la granularidad elegida (para el radio)
      fecha      date ancla (siempre presente, para repintar el input)
      desde,hasta  date o None — rango inclusivo aplicado a las consultas
      etiqueta   texto legible del período (para el encabezado)
      clave      string estable que identifica el filtro en la caché
    """
    historico = request.GET.get('historico') == '1'
    sel = request.GET.get('periodo', 'dia')
    if sel not in PERIODOS:
        sel = 'dia'
    hoy = timezone.localdate()
    fecha = parse_date(request.GET.get('fecha') or '') or hoy

    if historico:
        return {
            'historico': True, 'sel': sel, 'fecha': fecha,
            'desde': None, 'hasta': None,
            'etiqueta': 'Histórico (todas las fechas)', 'clave': 'hist',
        }

    if sel == 'dia':
        desde = hasta = fecha
        etiqueta = fecha.strftime('%d/%m/%Y')
    elif sel == 'semana':
        desde = fecha - timedelta(days=fecha.weekday())     # lunes de esa semana
        hasta = desde + timedelta(days=6)                   # domingo
        etiqueta = f'Semana del {desde.strftime("%d/%m")} al {hasta.strftime("%d/%m/%Y")}'
    elif sel == 'mes':
        desde = fecha.replace(day=1)
        hasta = _fin_de_mes(desde)
        etiqueta = f'{MESES_DICT[desde.month]} {desde.year}'
    else:  # anio
        desde = fecha.replace(month=1, day=1)
        hasta = fecha.replace(month=12, day=31)
        etiqueta = f'Año {fecha.year}'

    return {
        'historico': False, 'sel': sel, 'fecha': fecha,
        'desde': desde, 'hasta': hasta,
        'etiqueta': etiqueta, 'clave': f'{sel}:{fecha.isoformat()}',
    }


def _fin_de_mes(primero):
    """Último día del mes al que pertenece `primero` (que ya es día 1)."""
    if primero.month == 12:
        siguiente = primero.replace(year=primero.year + 1, month=1)
    else:
        siguiente = primero.replace(month=primero.month + 1)
    return siguiente - timedelta(days=1)
