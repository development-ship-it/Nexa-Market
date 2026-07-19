"""Merma: da de baja stock por pérdida, vencimiento o rotura."""
import json
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from base_datos.cache import cachear
from base_datos.models import Articulo, Categoria, Factura, Stock

from .comunes import _get_empresa, _get_usuario


@login_required
def merma(request):
    """
    Registro de merma (pérdida/deterioro) desde la web.
    Genera una Factura tipo MERMA (MRM-XXXX) con precio de venta 0 y el
    precio de compra que corresponda; cada línea es una SALIDA de stock.
    El total de la factura es el costo perdido (para cuantificar la pérdida).
    """
    from django.db.models import Sum, Q, Value, IntegerField
    from django.db.models.functions import Coalesce

    empresa = _get_empresa(request)

    if request.method == 'POST':
        try:
            cart = json.loads(request.POST.get('cart_data', '[]'))
        except json.JSONDecodeError:
            cart = []

        lineas = []
        for item in cart:
            articulo = get_object_or_404(Articulo, id_articulo=item['id'], empresa=empresa)
            cantidad = int(item['cantidad'])
            if cantidad <= 0:
                continue
            costo_u = float(articulo.precio_compra or 0)
            lineas.append((articulo, cantidad, costo_u))

        if not lineas:
            messages.error(request, 'No seleccionaste productos para la merma.')
            return redirect('merma')

        usuario = _get_usuario(request)
        total_merma = sum(cantidad * costo for _, cantidad, costo in lineas)
        conteo = Factura.objects.filter(empresa=empresa, tipo='MERMA').count()
        numero = f'MRM-{conteo + 1:04d}'

        factura = Factura.objects.create(
            id_nfactura=str(uuid.uuid4()),
            empresa=empresa,
            usuario=usuario,
            numero_factura=numero,
            fecha=timezone.now(),
            total=total_merma,
            tipo='MERMA',
        )
        for articulo, cantidad, costo_u in lineas:
            Stock.objects.create(
                id_stock=str(uuid.uuid4()),
                articulo=articulo,
                empresa=empresa,
                usuario=usuario,
                tipo='SALIDA',
                unidades=cantidad,
                precio_unitario_compra=costo_u,
                precio_unitario_venta=0,   # merma: no hay venta
                total=costo_u * cantidad,  # costo perdido
                factura=factura,
                fecha_hora=timezone.now(),
            )

        messages.success(request, f'Merma {numero} registrada — Costo perdido: ${total_merma:,.0f}')
        return redirect('compras_ventas')

    def _cargar():
        articulos = list(
            Articulo.objects
            .filter(empresa=empresa, activo=True)
            .select_related('categoria')
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
        categorias = list(
            Categoria.objects
            .filter(empresa=empresa, estado=True, articulos__empresa=empresa, articulos__activo=True)
            .distinct()
            .order_by('categoria')
        )
        return articulos, categorias

    articulos, categorias = cachear(empresa.pk, 'merma_pos', _cargar)
    return render(request, 'pages/merma/merma.html', {
        'page': 'merma',
        'articulos': articulos,
        'categorias': categorias,
    })
