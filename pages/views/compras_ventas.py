"""Listado de facturas de compra y venta, agrupado y filtrable."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from base_datos.models import Factura

from .agrupamiento import MESES, _abrir_primer_camino, _agrupar, _money, _niveles_fecha
from .comunes import _get_empresa


def _chips_facturas(items):
    v = c = m = 0
    for f in items:
        if f.tipo == 'VENTA':
            v += f.total
        elif f.tipo == 'COMPRA':
            c += f.total
        else:
            m += f.total
    chips = []
    if v:
        chips.append({'clase': 'venta', 'texto': 'Ventas ' + _money(v)})
    if c:
        chips.append({'clase': 'compra', 'texto': 'Compras ' + _money(c)})
    if m:
        chips.append({'clase': 'merma', 'texto': 'Merma ' + _money(m)})
    return chips


@login_required
def compras_ventas(request):
    empresa = _get_empresa(request)
    base = Factura.objects.filter(empresa=empresa)

    # Años con facturas (para el selector, antes de filtrar)
    anios = [d.year for d in base.dates('fecha', 'year')]

    # Filtros: tipo + mes + año + rango desde/hasta (combinables, todos server-side)
    tipo  = request.GET.get('tipo', '')
    mes   = request.GET.get('mes', '')
    anio  = request.GET.get('anio', '')
    desde = parse_date(request.GET.get('desde') or '')
    hasta = parse_date(request.GET.get('hasta') or '')

    facturas = base.select_related('usuario').prefetch_related('lineas__articulo').order_by('-fecha')
    if tipo in ('VENTA', 'COMPRA', 'MERMA'):
        facturas = facturas.filter(tipo=tipo)
    if anio.isdigit():
        facturas = facturas.filter(fecha__year=int(anio))
    if mes.isdigit() and 1 <= int(mes) <= 12:
        facturas = facturas.filter(fecha__month=int(mes))
    if desde:
        facturas = facturas.filter(fecha__date__gte=desde)
    if hasta:
        facturas = facturas.filter(fecha__date__lte=hasta)

    facturas = list(facturas)
    total_ventas  = sum(f.total for f in facturas if f.tipo == 'VENTA')
    total_compras = sum(f.total for f in facturas if f.tipo == 'COMPRA')
    total_mermas  = sum(f.total for f in facturas if f.tipo == 'MERMA')

    grupos = _agrupar(facturas, _niveles_fecha(lambda f: timezone.localtime(f.fecha)), _chips_facturas)
    _abrir_primer_camino(grupos)

    return render(request, 'pages/compras_ventas/compras_ventas.html', {
        'page': 'compras_ventas',
        'grupos': grupos,
        'total_facturas': len(facturas),
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'total_mermas': total_mermas,
        'balance': total_ventas - total_compras,
        'anios': anios,
        'meses': MESES,
        'filtro_tipo': tipo,
        'filtro_mes': mes,
        'filtro_anio': anio,
        'filtro_desde': request.GET.get('desde', ''),
        'filtro_hasta': request.GET.get('hasta', ''),
        'filtrando': bool(tipo or mes or anio or desde or hasta),
    })
