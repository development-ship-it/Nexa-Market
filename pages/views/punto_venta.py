"""Punto de venta: cobra, descuenta stock y emite la factura."""
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
def punto_venta(request):
    from django.db.models import Sum, Q, Value, IntegerField
    from django.db.models.functions import Coalesce

    empresa = _get_empresa(request)

    if request.method == 'POST':
        try:
            cart = json.loads(request.POST.get('cart_data', '[]'))
        except json.JSONDecodeError:
            cart = []

        # Precio autoritativo desde la BD: aplica el mayorista si corresponde
        lineas = []
        for item in cart:
            articulo = get_object_or_404(Articulo, id_articulo=item['id'], empresa=empresa)
            cantidad = int(item['cantidad'])
            if cantidad <= 0:
                continue
            precio_u = float(articulo.precio_venta or 0)
            if (articulo.es_mayorista and articulo.precio_venta_mayor
                    and articulo.cantidad_minima_mayor
                    and cantidad >= articulo.cantidad_minima_mayor):
                precio_u = float(articulo.precio_venta_mayor)
            lineas.append((articulo, cantidad, precio_u))

        if not lineas:
            messages.error(request, 'El carrito está vacío.')
            return redirect('punto_venta')

        usuario = _get_usuario(request)
        total_venta = sum(cantidad * precio for _, cantidad, precio in lineas)
        conteo = Factura.objects.filter(empresa=empresa, tipo='VENTA').count()
        numero = f'VTA-{conteo + 1:04d}'

        factura = Factura.objects.create(
            id_nfactura=str(uuid.uuid4()),
            empresa=empresa,
            usuario=usuario,
            numero_factura=numero,
            fecha=timezone.now(),
            total=total_venta,
            tipo='VENTA',
        )
        for articulo, cantidad, precio_u in lineas:
            Stock.objects.create(
                id_stock=str(uuid.uuid4()),
                articulo=articulo,
                empresa=empresa,
                usuario=usuario,
                tipo='SALIDA',
                unidades=cantidad,
                precio_unitario_compra=float(articulo.precio_compra or 0),
                precio_unitario_venta=precio_u,
                total=precio_u * cantidad,
                factura=factura,
                fecha_hora=timezone.now(),
            )

        messages.success(request, f'Venta {numero} registrada — Total: ${total_venta:,.0f}')
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

    articulos, categorias = cachear(empresa.pk, 'pos_venta', _cargar)
    return render(request, 'pages/punto_venta/punto_venta.html', {
        'page': 'punto_venta',
        'articulos': articulos,
        'categorias': categorias,
    })
