"""CRUD de categorías."""
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from base_datos.models import Categoria

from ..forms import CategoriaForm

from .comunes import _get_empresa


@login_required
def categorias(request):
    empresa = _get_empresa(request)
    cats = Categoria.objects.filter(empresa=empresa).order_by('categoria')
    return render(request, 'pages/categorias/categorias.html', {'page': 'categorias', 'categorias': cats})


@login_required
def categoria_crear(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.id_categoria = str(uuid.uuid4())
            cat.empresa = empresa
            cat.save()
            messages.success(request, f'Categoría "{cat.categoria}" creada.')
            return redirect('categorias')
    else:
        form = CategoriaForm()
    return render(request, 'pages/categorias/categoria_form.html', {'form': form, 'page': 'categorias', 'accion': 'Nueva categoría'})


@login_required
def categoria_editar(request, pk):
    empresa = _get_empresa(request)
    cat = get_object_or_404(Categoria, id_categoria=pk, empresa=empresa)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, f'Categoría "{cat.categoria}" actualizada.')
            return redirect('categorias')
    else:
        form = CategoriaForm(instance=cat)
    return render(request, 'pages/categorias/categoria_form.html', {'form': form, 'page': 'categorias', 'accion': 'Editar categoría', 'objeto': cat})


@login_required
def categoria_eliminar(request, pk):
    empresa = _get_empresa(request)
    cat = get_object_or_404(Categoria, id_categoria=pk, empresa=empresa)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'Categoría eliminada.')
        return redirect('categorias')
    return render(request, 'pages/shared/confirm_delete.html', {
        'objeto': cat, 'nombre': cat.categoria, 'tipo': 'Categoría',
        'cancelar_url': 'categorias', 'page': 'categorias',
    })
