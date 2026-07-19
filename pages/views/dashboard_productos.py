"""Cálculo de los datos de la pestaña Productos del dashboard."""
from base_datos.models import Stock


def _datos_productos(empresa):
    """Análisis de productos: más vendidos (unidades) y los que más ingresos dejan."""
    from django.db.models import Sum, F, FloatField

    salidas = (
        Stock.objects
        .filter(empresa=empresa, tipo='SALIDA')
        .exclude(factura__tipo='MERMA')
    )
    # Alias 'uds' (no 'unidades') para no chocar con F('unidades') en el costo
    filas = list(
        salidas.values('articulo__nombre_articulo', 'articulo__categoria__categoria')
        .annotate(
            uds=Sum('unidades'),
            ingresos=Sum('total'),
            costo=Sum(F('precio_unitario_compra') * F('unidades'), output_field=FloatField()),
        )
    )
    for f in filas:
        f['nombre'] = f['articulo__nombre_articulo'] or 'Sin nombre'
        f['categoria'] = f['articulo__categoria__categoria'] or 'Sin categoría'
        f['ingresos'] = f['ingresos'] or 0
        f['unidades'] = f['uds'] or 0
        f['ganancia'] = f['ingresos'] - (f['costo'] or 0)

    top_unidades = sorted(filas, key=lambda x: x['unidades'], reverse=True)[:8]
    max_u = top_unidades[0]['unidades'] if top_unidades else 0
    for x in top_unidades:
        x['pct'] = round(x['unidades'] / max_u * 100) if max_u else 0

    top_ingresos = sorted(filas, key=lambda x: x['ingresos'], reverse=True)[:8]
    max_i = top_ingresos[0]['ingresos'] if top_ingresos else 0
    for x in top_ingresos:
        x['pct'] = round(x['ingresos'] / max_i * 100) if max_i else 0

    return {
        'prod_top_unidades': top_unidades,
        'prod_top_ingresos': top_ingresos,
        'prod_tabla': sorted(filas, key=lambda x: x['ingresos'], reverse=True),
        'prod_total_ingresos': sum(f['ingresos'] for f in filas),
        'prod_total_ganancia': sum(f['ganancia'] for f in filas),
        'prod_total_unidades': sum(f['unidades'] for f in filas),
    }
