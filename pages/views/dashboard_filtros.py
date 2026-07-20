"""Filtro de período del dashboard.

Modos, por orden de precedencia:
  hoy        casilla «Hoy» → solo el día de hoy
  rango      fechas «Desde/Hasta» → rango libre
  historico  casilla «Histórico» → todas las fechas
  cascada    año → meses (varios) → semanas (varias, si hay un solo mes)

La semana N de un mes es el bloque de 7 días: 1 = 1–7, 2 = 8–14, …
"""
import calendar

from django.utils import timezone
from django.utils.dateparse import parse_date

from .agrupamiento import MESES_DICT

MESES_OPCIONES = [
    (1, 'Ene'), (2, 'Feb'), (3, 'Mar'), (4, 'Abr'), (5, 'May'), (6, 'Jun'),
    (7, 'Jul'), (8, 'Ago'), (9, 'Sep'), (10, 'Oct'), (11, 'Nov'), (12, 'Dic'),
]


def _enteros(request, clave, validos):
    """Lee ?clave repetido y devuelve enteros válidos, sin duplicados y ordenados."""
    vistos = []
    for v in request.GET.getlist(clave):
        if v.isdigit() and int(v) in validos and int(v) not in vistos:
            vistos.append(int(v))
    return sorted(vistos)


def semanas_de_mes(anio, mes):
    """Bloques de 7 días del mes: [(1, 'Sem 1', '1–7'), (2, 'Sem 2', '8–14'), …]."""
    dias = calendar.monthrange(anio, mes)[1]
    bloques, num, ini = [], 1, 1
    while ini <= dias:
        fin = min(ini + 6, dias)
        bloques.append((num, f'Sem {num}', f'{ini}–{fin}'))
        num, ini = num + 1, ini + 7
    return bloques


def resolver_periodo(request, empresa):
    """Normaliza los parámetros del filtro a un dict con todo lo que la plantilla
    y las consultas necesitan (opciones de los chips y estado de cada modo)."""
    from base_datos.models import Factura

    hoy = timezone.localdate()
    anios = {d.year for d in Factura.objects.filter(empresa=empresa).dates('fecha', 'year')}
    anios.add(hoy.year)
    anios = sorted(anios, reverse=True)

    hoy_flag = request.GET.get('hoy') == '1'
    historico = request.GET.get('historico') == '1'
    desde = parse_date(request.GET.get('desde') or '')
    hasta = parse_date(request.GET.get('hasta') or '')
    if desde and hasta and desde > hasta:          # rango al revés: lo enderezamos
        desde, hasta = hasta, desde

    # Cascada: se calcula siempre para poder pintar los chips aunque no sea el modo activo.
    tocado = any(k in request.GET for k in ('anio', 'meses', 'semanas'))
    anio_raw = request.GET.get('anio', '')
    anio = int(anio_raw) if anio_raw.isdigit() and int(anio_raw) in anios else hoy.year
    meses = _enteros(request, 'meses', set(range(1, 13)))
    if not tocado:                                 # primera carga: arranca en el mes actual
        anio, meses = hoy.year, [hoy.month]
    mes_unico = meses[0] if len(meses) == 1 else None
    semanas_disp = semanas_de_mes(anio, mes_unico) if mes_unico else []
    semanas = _enteros(request, 'semanas', {s[0] for s in semanas_disp}) if mes_unico else []

    p = {
        'anio': anio, 'anios': anios,
        'meses': meses, 'meses_opciones': MESES_OPCIONES,
        'mes_unico': mes_unico, 'semanas': semanas, 'semanas_disp': semanas_disp,
        'desde': None, 'hasta': None,
    }
    if hoy_flag:
        p.update(modo='hoy', desde=hoy, hasta=hoy,
                 etiqueta=f'Hoy · {hoy:%d/%m/%Y}', clave=f'hoy:{hoy.isoformat()}')
    elif desde or hasta:
        p.update(modo='rango', desde=desde, hasta=hasta,
                 etiqueta=_etq_rango(desde, hasta), clave=f"r:{desde or ''}:{hasta or ''}")
    elif historico:
        p.update(modo='historico', etiqueta='Histórico (todas las fechas)', clave='hist')
    else:
        p.update(modo='cascada', etiqueta=_etq_cascada(anio, meses, mes_unico, semanas),
                 clave=f"{anio}.{'-'.join(map(str, meses))}.{'-'.join(map(str, semanas))}")
    return p


def aplicar_filtro(qs, campo, periodo):
    """Aplica el filtro de período a `qs` usando el campo de fecha indicado
    (`fecha` en Factura, `fecha_hora` en Stock)."""
    modo = periodo['modo']
    if modo == 'historico':
        return qs
    if modo in ('hoy', 'rango'):
        if periodo['desde']:
            qs = qs.filter(**{f'{campo}__date__gte': periodo['desde']})
        if periodo['hasta']:
            qs = qs.filter(**{f'{campo}__date__lte': periodo['hasta']})
        return qs
    # cascada
    qs = qs.filter(**{f'{campo}__year': periodo['anio']})
    if periodo['meses']:
        qs = qs.filter(**{f'{campo}__month__in': periodo['meses']})
    if periodo['mes_unico'] and periodo['semanas']:
        from django.db.models import Q
        rangos = Q()
        for w in periodo['semanas']:
            rangos |= Q(**{f'{campo}__day__gte': (w - 1) * 7 + 1, f'{campo}__day__lte': w * 7})
        qs = qs.filter(rangos)
    return qs


def _etq_rango(desde, hasta):
    if desde and hasta:
        return f'{desde:%d/%m/%Y} – {hasta:%d/%m/%Y}'
    if desde:
        return f'Desde {desde:%d/%m/%Y}'
    return f'Hasta {hasta:%d/%m/%Y}'


def _etq_cascada(anio, meses, mes_unico, semanas):
    if not meses:
        return f'Año {anio}'
    if mes_unico:
        base = f'{MESES_DICT[mes_unico]} {anio}'
        return f'{base} · {", ".join(f"Sem {w}" for w in semanas)}' if semanas else base
    cortos = dict(MESES_OPCIONES)
    return f'{", ".join(cortos[m] for m in meses)} {anio}'
