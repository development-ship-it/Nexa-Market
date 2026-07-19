"""Listado de movimientos de stock (entradas, salidas y mermas)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from base_datos.models import Stock

from .agrupamiento import _abrir_primer_camino, _agrupar, _money, _niveles_fecha
from .comunes import _get_empresa


def _chips_movimientos(items):
    ent = sal = mer = 0
    total_ventas = 0
    for mv in items:
        es_merma = bool(mv.factura_id and mv.factura and mv.factura.tipo == 'MERMA')
        if mv.tipo == 'ENTRADA':
            ent += 1
        elif es_merma:
            mer += 1
        else:
            sal += 1
            total_ventas += mv.total
    chips = []
    if ent:
        chips.append({'clase': 'compra', 'texto': f'{ent} entrada{"s" if ent != 1 else ""}'})
    if sal:
        chips.append({'clase': 'venta', 'texto': f'{sal} venta{"s" if sal != 1 else ""}'})
    if mer:
        chips.append({'clase': 'merma', 'texto': f'{mer} merma{"s" if mer != 1 else ""}'})
    if total_ventas:
        chips.append({'clase': 'venta', 'texto': _money(total_ventas)})
    return chips


@login_required
def movimientos(request):
    empresa = _get_empresa(request)
    tipo_filtro = request.GET.get('tipo', '')
    qs = (
        Stock.objects
        .filter(empresa=empresa)
        .select_related('articulo', 'articulo__categoria', 'factura', 'usuario')
        .order_by('-fecha_hora')
    )
    if tipo_filtro == 'ENTRADA':
        qs = qs.filter(tipo='ENTRADA')
    elif tipo_filtro == 'SALIDA':
        # Ventas reales: salidas que no provienen de una merma
        qs = qs.filter(tipo='SALIDA').exclude(factura__tipo='MERMA')
    elif tipo_filtro == 'MERMA':
        qs = qs.filter(factura__tipo='MERMA')

    movs = list(qs)
    grupos = _agrupar(movs, _niveles_fecha(lambda m: timezone.localtime(m.fecha_hora)), _chips_movimientos)
    _abrir_primer_camino(grupos)
    return render(request, 'pages/movimientos/movimientos.html', {
        'page': 'movimientos',
        'grupos': grupos,
        'total_movimientos': len(movs),
        'tipo_filtro': tipo_filtro,
    })
