"""Punto de compra: registra compras a proveedores y suma stock."""
import json
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from base_datos.cache import cachear
from base_datos.models import Articulo, Factura, Proveedor, Stock

from .comunes import _get_empresa, _get_usuario


@login_required
def punto_compra(request):
    empresa = _get_empresa(request)

    if request.method == 'POST':
        cart_json = request.POST.get('cart_data', '[]')
        try:
            cart = json.loads(cart_json)
        except json.JSONDecodeError:
            cart = []

        if not cart:
            messages.error(request, 'El carrito está vacío.')
            return redirect('punto_compra')

        usuario = _get_usuario(request)
        total_compra = sum(float(i['precio']) * int(i['cantidad']) for i in cart)

        conteo = Factura.objects.filter(empresa=empresa, tipo='COMPRA').count()
        numero = f'CMP-{conteo + 1:04d}'

        factura = Factura.objects.create(
            id_nfactura=str(uuid.uuid4()),
            empresa=empresa,
            usuario=usuario,
            numero_factura=numero,
            fecha=timezone.now(),
            total=total_compra,
            tipo='COMPRA',
        )

        for item in cart:
            articulo = get_object_or_404(Articulo, id_articulo=item['id'], empresa=empresa)
            cantidad = int(item['cantidad'])
            precio_u = float(item['precio'])
            precio_venta = float(item.get('precio_venta') or articulo.precio_venta)

            # Fecha de vencimiento opcional
            fecha_venc = None
            fv_str = item.get('fecha_vencimiento')
            if fv_str:
                d = parse_date(fv_str)
                if d:
                    fecha_venc = timezone.make_aware(
                        timezone.datetime.combine(d, timezone.datetime.min.time())
                    )

            Stock.objects.create(
                id_stock=str(uuid.uuid4()),
                articulo=articulo,
                empresa=empresa,
                usuario=usuario,
                tipo='ENTRADA',
                unidades=cantidad,
                precio_unitario_compra=precio_u,
                precio_unitario_venta=precio_venta,
                total=precio_u * cantidad,
                factura=factura,
                fecha_hora=timezone.now(),
                fecha_vencimiento=fecha_venc,
            )

        messages.success(request, f'Compra {numero} registrada — Total: ${total_compra:,.0f}')
        return redirect('compras_ventas')

    def _cargar():
        articulos = list(
            Articulo.objects
            .filter(empresa=empresa, activo=True)
            .select_related('categoria', 'proveedor')
            .order_by('nombre_articulo')
        )
        # Solo proveedores que tengan artículos activos en esta empresa
        proveedores_activos = list(
            Proveedor.objects
            .filter(empresa=empresa, activo=True, articulo__empresa=empresa, articulo__activo=True)
            .distinct()
            .order_by('nombre')
        )
        return articulos, proveedores_activos

    articulos, proveedores_activos = cachear(empresa.pk, 'pos_compra', _cargar)
    return render(request, 'pages/punto_compra/punto_compra.html', {
        'page': 'punto_compra',
        'articulos': articulos,
        'proveedores_activos': proveedores_activos,
    })
