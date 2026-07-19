"""CRUD de proveedores."""
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from base_datos.models import Proveedor

from ..forms import ProveedorForm

from .comunes import _get_empresa


@login_required
def proveedores(request):
    empresa = _get_empresa(request)
    provs = Proveedor.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    return render(request, 'pages/proveedores/proveedores.html', {'page': 'proveedores', 'proveedores': provs})


@login_required
def proveedor_crear(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            prov = form.save(commit=False)
            prov.id_proveedor = str(uuid.uuid4())
            prov.empresa = empresa
            prov.save()
            messages.success(request, f'Proveedor "{prov.nombre}" creado.')
            return redirect('proveedores')
    else:
        form = ProveedorForm()
    return render(request, 'pages/proveedores/proveedor_form.html', {'form': form, 'page': 'proveedores', 'accion': 'Nuevo proveedor'})


@login_required
def proveedor_editar(request, pk):
    empresa = _get_empresa(request)
    prov = get_object_or_404(Proveedor, id_proveedor=pk, empresa=empresa)
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=prov)
        if form.is_valid():
            form.save()
            messages.success(request, f'Proveedor "{prov.nombre}" actualizado.')
            return redirect('proveedores')
    else:
        form = ProveedorForm(instance=prov)
    return render(request, 'pages/proveedores/proveedor_form.html', {'form': form, 'page': 'proveedores', 'accion': 'Editar proveedor', 'objeto': prov})


@login_required
def proveedor_eliminar(request, pk):
    empresa = _get_empresa(request)
    prov = get_object_or_404(Proveedor, id_proveedor=pk, empresa=empresa)
    if request.method == 'POST':
        prov.activo = False
        prov.save()
        messages.success(request, f'Proveedor "{prov.nombre}" desactivado.')
        return redirect('proveedores')
    return render(request, 'pages/shared/confirm_delete.html', {
        'objeto': prov, 'nombre': prov.nombre, 'tipo': 'Proveedor',
        'cancelar_url': 'proveedores', 'page': 'proveedores',
    })
