"""Helpers para agrupar listados por año/mes/día y armar los chips."""


MESES = [
    (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
    (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
    (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
]
MESES_DICT = dict(MESES)


DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _money(n):
    """Formato de dinero chileno: $1.234.567 (punto como separador de miles)."""
    return '$' + f'{n:,.0f}'.replace(',', '.')


def _niveles_fecha(getdt):
    """
    Funciones de nivel para el desglose jerárquico tipo AppSheet:
    Año → Mes → Semana → Día → Hora del día.
    `getdt(item)` devuelve el datetime local del item.
    """
    def anio(it):
        d = getdt(it); return d.year, str(d.year)

    def mes(it):
        d = getdt(it); return d.month, f'{d.month}.-{MESES_DICT[d.month]}'

    def semana(it):
        d = getdt(it); w = d.isocalendar()[1]; return w, f'Semana {w}'

    def dia(it):
        d = getdt(it)
        return d.toordinal(), f'{DIAS_SEMANA[d.weekday()]} {d.strftime("%d/%m")}'

    def hora(it):
        d = getdt(it); return d.hour, f'{d.hour:02d}:00 – {d.hour:02d}:59'

    return [anio, mes, semana, dia, hora]


def _agrupar(items, niveles, chips_de):
    """
    Agrupa `items` recursivamente según `niveles` (lista de funciones
    item -> (orden, etiqueta)). Devuelve nodos ordenados (reciente primero)
    con conteo, chips de resumen e hijos o items (en la hoja).
    """
    if not niveles:
        return None
    nivel = niveles[0]
    grupos = {}
    for it in items:
        orden, etiqueta = nivel(it)
        g = grupos.get(orden)
        if g is None:
            g = {'orden': orden, 'label': etiqueta, 'items': []}
            grupos[orden] = g
        g['items'].append(it)
    nodos = []
    for g in sorted(grupos.values(), key=lambda x: x['orden'], reverse=True):
        sub = g['items']
        hijos = _agrupar(sub, niveles[1:], chips_de)
        nodos.append({
            'label': g['label'],
            'count': len(sub),
            'chips': chips_de(sub),
            'hijos': hijos,
            'items': None if hijos else sub,
            'open': False,
        })
    return nodos


def _abrir_primer_camino(nodos):
    """Marca abierto el primer nodo de cada nivel (drill-down al más reciente)."""
    n = nodos
    while n:
        n[0]['open'] = True
        n = n[0]['hijos']
