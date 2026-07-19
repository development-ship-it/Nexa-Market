"""Cálculo de los datos del dashboard principal (tarjetas, gráfico, rankings)."""
from datetime import timedelta

from django.utils import timezone

from base_datos.models import Articulo, Factura, Stock


def _datos_dashboard(empresa):
    from django.db.models import Sum, Count, Q, Value, IntegerField
    from django.db.models.functions import Coalesce, ExtractHour

    hoy = timezone.localdate()

    facturas = Factura.objects.filter(empresa=empresa)
    ventas_hoy = facturas.filter(tipo='VENTA', fecha__date=hoy).aggregate(t=Sum('total'))['t'] or 0
    ventas_ayer = facturas.filter(tipo='VENTA', fecha__date=hoy - timedelta(days=1)).aggregate(t=Sum('total'))['t'] or 0
    variacion = round((ventas_hoy - ventas_ayer) / ventas_ayer * 100) if ventas_ayer else None
    facturas_hoy = facturas.filter(fecha__date=hoy).count()

    total_ventas = facturas.filter(tipo='VENTA').aggregate(t=Sum('total'))['t'] or 0
    total_compras = facturas.filter(tipo='COMPRA').aggregate(t=Sum('total'))['t'] or 0

    # Stock actual por artículo (entradas - salidas del libro de movimientos)
    articulos = (
        Articulo.objects
        .filter(empresa=empresa, activo=True)
        .annotate(
            entradas=Coalesce(
                Sum('movimientos__unidades', filter=Q(movimientos__tipo='ENTRADA')),
                Value(0), output_field=IntegerField()
            ),
            salidas=Coalesce(
                Sum('movimientos__unidades', filter=Q(movimientos__tipo='SALIDA')),
                Value(0), output_field=IntegerField()
            ),
        )
    )
    stock_total = 0
    stock_bajo = []
    for art in articulos:
        art.stock_actual = art.entradas - art.salidas
        stock_total += max(art.stock_actual, 0)
        umbral = art.stock_minimo if art.stock_minimo is not None else 5
        if art.stock_actual < umbral:
            stock_bajo.append(art)
    stock_bajo.sort(key=lambda a: a.stock_actual)
    stock_bajo_count = len(stock_bajo)
    stock_bajo = stock_bajo[:5]

    # Ventas por hora del día (conteo de ventas por hora, todo el historial):
    # muestra las horas más activas del negocio como un gráfico lineal.
    conteo_hora = {
        r['h']: r['c']
        for r in (
            facturas.filter(tipo='VENTA')
            .annotate(h=ExtractHour('fecha'))
            .values('h')
            .annotate(c=Count('id_nfactura'), t=Sum('total'))
        )
    }
    total_hora = {
        r['h']: r['t'] or 0
        for r in (
            facturas.filter(tipo='VENTA')
            .annotate(h=ExtractHour('fecha'))
            .values('h')
            .annotate(t=Sum('total'))
        )
    }
    max_conteo = max(conteo_hora.values(), default=0)
    ventas_por_hora = []
    for i, h in enumerate(range(24)):
        c = conteo_hora.get(h, 0)
        pct = round(c / max_conteo * 100) if max_conteo else 0
        ventas_por_hora.append({
            'hora': h,
            'label': f'{h:02d}h',
            'count': c,
            'total': total_hora.get(h, 0),
            'pct': pct,
            'x': round(i / 23 * 100, 2),          # posición X en el SVG (0–100)
            'y': round(100 - pct, 2),             # posición Y (invertida: más alto = más ventas)
            'mostrar_label': h % 3 == 0,          # etiquetar cada 3 horas
        })
    # Cadenas de puntos para el SVG (línea + área rellena)
    linea_puntos = ' '.join(f"{p['x']},{p['y']}" for p in ventas_por_hora)
    area_puntos = f"0,100 {linea_puntos} 100,100"
    hay_ventas_hora = max_conteo > 0

    # Top 5 productos más vendidos (unidades salidas, sin contar mermas)
    salidas_reales = (
        Stock.objects.filter(empresa=empresa, tipo='SALIDA').exclude(factura__tipo='MERMA')
    )
    productos_top = list(
        salidas_reales
        .values('articulo__nombre_articulo')
        .annotate(unidades=Sum('unidades'), total=Sum('total'))
        .order_by('-unidades')[:5]
    )
    max_prod = productos_top[0]['unidades'] if productos_top else 0
    for p in productos_top:
        p['pct'] = round((p['unidades'] or 0) / max_prod * 100) if max_prod else 0

    # Top 5 categorías más vendidas
    categorias_top = list(
        salidas_reales
        .values('articulo__categoria__categoria')
        .annotate(unidades=Sum('unidades'), total=Sum('total'))
        .order_by('-unidades')[:5]
    )
    max_cat = categorias_top[0]['unidades'] if categorias_top else 0
    for c in categorias_top:
        c['nombre'] = c['articulo__categoria__categoria'] or 'Sin categoría'
        c['pct'] = round((c['unidades'] or 0) / max_cat * 100) if max_cat else 0

    return {
        'ventas_hoy': ventas_hoy,
        'variacion': variacion,
        'stock_total': stock_total,
        'facturas_hoy': facturas_hoy,
        'stock_bajo': stock_bajo,
        'stock_bajo_count': stock_bajo_count,
        'ventas_por_hora': ventas_por_hora,
        'linea_puntos': linea_puntos,
        'area_puntos': area_puntos,
        'hay_ventas_hora': hay_ventas_hora,
        'productos_top': productos_top,
        'categorias_top': categorias_top,
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'balance': total_ventas - total_compras,
        'ultimas_facturas': list(facturas.select_related('usuario').order_by('-fecha')[:4]),
    }
