"""Regla de negocio: el inventario nunca puede quedar negativo.

El stock no se guarda en el artículo, se calcula desde el libro de movimientos:
    disponible = SUM(ENTRADA) - SUM(SALIDA)

Toda operación que saque stock (venta, merma) tiene que pasar por
`revisar_disponibilidad` ANTES de escribir. La validación del navegador no
basta: la grilla del punto de venta viene de una página cacheada, así que su
stock puede estar desactualizado (otra caja, o la app móvil vendiendo a la vez).
"""
from base_datos.models import Articulo


def stock_disponible(empresa, ids):
    """{id_articulo: unidades disponibles} para los artículos indicados."""
    from django.db.models import Sum, Q, Value, IntegerField
    from django.db.models.functions import Coalesce

    filas = (
        Articulo.objects
        .filter(empresa=empresa, id_articulo__in=list(ids))
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
        .values_list('id_articulo', 'entradas', 'salidas')
    )
    return {pk: entradas - salidas for pk, entradas, salidas in filas}


def revisar_disponibilidad(empresa, pedidos):
    """Comprueba que se pueda sacar lo pedido sin dejar el stock en negativo.

    `pedidos` es una lista de (articulo, cantidad). Devuelve una lista de textos
    describiendo lo que falta — vacía significa que la operación puede seguir.
    """
    # Un mismo artículo puede venir en varias líneas: se suman antes de comparar.
    solicitado = {}
    nombres = {}
    for articulo, cantidad in pedidos:
        solicitado[articulo.pk] = solicitado.get(articulo.pk, 0) + cantidad
        nombres[articulo.pk] = articulo.nombre_articulo

    disponible = stock_disponible(empresa, solicitado.keys())

    faltantes = []
    for pk, cantidad in solicitado.items():
        hay = disponible.get(pk, 0)
        if cantidad > hay:
            if hay <= 0:
                faltantes.append(f'{nombres[pk]} (sin stock)')
            else:
                faltantes.append(f'{nombres[pk]} (quedan {hay}, pediste {cantidad})')
    return faltantes


def bloquear_articulos(empresa, ids):
    """Bloquea las filas de los artículos hasta el fin de la transacción.

    Si dos cajas venden la última unidad a la vez, la segunda espera aquí y
    recién entonces calcula el stock — ya con la primera venta descontada.
    """
    return list(
        Articulo.objects.select_for_update()
        .filter(empresa=empresa, id_articulo__in=list(ids))
        .values_list('id_articulo', flat=True)
    )
