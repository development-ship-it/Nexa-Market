"""CRUD de artículos y cálculo de precios mayoristas."""
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from base_datos.cache import cachear
from base_datos.models import Articulo, Proveedor

from ..forms import ArticuloForm

from .comunes import _get_empresa, _round10


def _aplicar_precios_mayor(articulo):
    """Redondea el precio de venta mayorista y recalcula su margen.
    La base es el precio de compra normal: no existe compra al por mayor."""
    pc = articulo.precio_compra
    pvm = _round10(articulo.precio_venta_mayor) if articulo.precio_venta_mayor else None
    articulo.precio_venta_mayor = pvm
    if pc and pvm:
        articulo.margen_ganancia_mayor = round((pvm - pc) / pc * 100, 2)


# ── PRODUCTOS ─────────────────────────────────────────────────────────────────

@login_required
def productos(request):
    empresa = _get_empresa(request)
    filtro = request.GET.get('proveedor', '')

    def _cargar():
        qs = (
            Articulo.objects
            .filter(empresa=empresa, activo=True)
            .select_related('categoria', 'proveedor')
            .order_by('nombre_articulo')
        )
        prov_filter, prov_nombre = filtro, ''
        if prov_filter:
            qs = qs.filter(proveedor__id_proveedor=prov_filter)
            try:
                prov_nombre = Proveedor.objects.get(id_proveedor=prov_filter).nombre
            except Proveedor.DoesNotExist:
                prov_filter = ''
        return list(qs), prov_filter, prov_nombre

    articulos, prov_filter, prov_nombre = cachear(empresa.pk, f'productos:{filtro}', _cargar)
    return render(request, 'pages/productos/productos.html', {
        'page': 'productos',
        'articulos': articulos,
        'prov_filter': prov_filter,
        'prov_nombre': prov_nombre,
    })


@login_required
def producto_crear(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = ArticuloForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            articulo = form.save(commit=False)
            articulo.id_articulo = str(uuid.uuid4())
            articulo.empresa = empresa
            pc = _round10(articulo.precio_compra or 0)
            pv = _round10(articulo.precio_venta or 0)
            articulo.precio_compra = pc
            articulo.precio_venta = pv
            articulo.margen_ganancia = round(((pv - pc) / pc * 100) if pc > 0 else 0, 2)
            _aplicar_precios_mayor(articulo)
            articulo.save()
            messages.success(request, f'Producto "{articulo.nombre_articulo}" creado correctamente.')
            return redirect('productos')
    else:
        form = ArticuloForm(empresa=empresa)
    return render(request, 'pages/productos/producto_form.html', {'form': form, 'page': 'productos', 'accion': 'Crear producto'})


@login_required
def producto_editar(request, pk):
    empresa = _get_empresa(request)
    articulo = get_object_or_404(Articulo, id_articulo=pk, empresa=empresa)
    if request.method == 'POST':
        form = ArticuloForm(request.POST, request.FILES, instance=articulo, empresa=empresa)
        if form.is_valid():
            obj = form.save(commit=False)
            pc = _round10(obj.precio_compra or 0)
            pv = _round10(obj.precio_venta or 0)
            obj.precio_compra = pc
            obj.precio_venta = pv
            obj.margen_ganancia = round(((pv - pc) / pc * 100) if pc > 0 else 0, 2)
            _aplicar_precios_mayor(obj)
            obj.save()
            messages.success(request, f'Producto "{obj.nombre_articulo}" actualizado.')
            return redirect('productos')
    else:
        form = ArticuloForm(instance=articulo, empresa=empresa)
    return render(request, 'pages/productos/producto_form.html', {'form': form, 'page': 'productos', 'accion': 'Editar producto', 'articulo': articulo})


@login_required
def producto_eliminar(request, pk):
    empresa = _get_empresa(request)
    articulo = get_object_or_404(Articulo, id_articulo=pk, empresa=empresa)
    if request.method == 'POST':
        articulo.activo = False
        articulo.save()
        messages.success(request, f'Producto "{articulo.nombre_articulo}" desactivado.')
        return redirect('productos')
    return render(request, 'pages/productos/producto_confirm_delete.html', {'articulo': articulo, 'page': 'productos'})
