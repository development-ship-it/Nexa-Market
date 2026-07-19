"""Vista de inventario: stock actual calculado desde los movimientos."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from base_datos.cache import cachear
from base_datos.models import Articulo

from .comunes import _get_empresa


@login_required
def inventario(request):
    from django.db.models import Sum, Q, Value, IntegerField
    from django.db.models.functions import Coalesce

    empresa = _get_empresa(request)

    def _cargar():
        articulos = list(
            Articulo.objects
            .filter(empresa=empresa, activo=True)
            .select_related('categoria', 'proveedor')
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
            .order_by('nombre_articulo')
        )
        for art in articulos:
            art.stock_actual = art.entradas - art.salidas
        return articulos

    return render(request, 'pages/inventario/inventario.html', {
        'page': 'inventario',
        'articulos': cachear(empresa.pk, 'inventario', _cargar),
    })
