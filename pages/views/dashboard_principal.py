"""Datos del dashboard principal: tarjetas del período y gráfico de ventas por hora.

Todo se calcula sobre el rango de fechas que trae `periodo` (ver
`dashboard_filtros.resolver_periodo`). El gráfico de ventas por hora es un
acumulado del período: suma cada hora a lo largo de todos sus días.
"""
from base_datos.models import Factura, Stock


def _datos_dashboard(empresa, periodo):
    from django.db.models import Sum, Count, F, FloatField
    from django.db.models.functions import ExtractHour

    desde, hasta = periodo['desde'], periodo['hasta']

    # ── Tarjetas: ventas, compras y n.º de ventas del período ──────────────────
    facturas = Factura.objects.filter(empresa=empresa)
    if desde and hasta:
        facturas = facturas.filter(fecha__date__gte=desde, fecha__date__lte=hasta)

    ventas = facturas.filter(tipo='VENTA')
    total_ventas = ventas.aggregate(t=Sum('total'))['t'] or 0
    total_compras = facturas.filter(tipo='COMPRA').aggregate(t=Sum('total'))['t'] or 0
    num_ventas = ventas.count()

    # ── Utilidad: margen real de lo vendido (precio venta − compra, por línea) ──
    # Solo salidas de venta reales (una SALIDA es venta si su factura no es merma).
    lineas = Stock.objects.filter(empresa=empresa, tipo='SALIDA').exclude(factura__tipo='MERMA')
    if desde and hasta:
        lineas = lineas.filter(fecha_hora__date__gte=desde, fecha_hora__date__lte=hasta)
    utilidad = lineas.aggregate(
        u=Sum((F('precio_unitario_venta') - F('precio_unitario_compra')) * F('unidades'),
              output_field=FloatField())
    )['u'] or 0

    # ── Ventas por hora: acumulado del período (monto por hora del día) ─────────
    por_hora = {
        r['h']: (r['t'] or 0, r['c'])
        for r in (
            ventas.annotate(h=ExtractHour('fecha')).values('h')
            .annotate(t=Sum('total'), c=Count('id_nfactura'))
        )
    }
    max_monto = max((v[0] for v in por_hora.values()), default=0)
    ventas_por_hora = []
    for i, h in enumerate(range(24)):
        monto, conteo = por_hora.get(h, (0, 0))
        pct = round(monto / max_monto * 100) if max_monto else 0
        ventas_por_hora.append({
            'hora': h,
            'label': f'{h:02d}h',
            'count': conteo,
            'total': monto,
            'pct': pct,
            'x': round(i / 23 * 100, 2),          # posición X en el SVG (0–100)
            'y': round(100 - pct, 2),             # Y invertida: más alto = más ventas
            'mostrar_label': h % 3 == 0,          # etiquetar cada 3 horas
        })
    linea_puntos = ' '.join(f"{p['x']},{p['y']}" for p in ventas_por_hora)
    area_puntos = f"0,100 {linea_puntos} 100,100"

    return {
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'utilidad': utilidad,
        'num_ventas': num_ventas,
        'ventas_por_hora': ventas_por_hora,
        'linea_puntos': linea_puntos,
        'area_puntos': area_puntos,
        'hay_ventas_hora': max_monto > 0,
    }
