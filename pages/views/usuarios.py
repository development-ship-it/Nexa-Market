"""CRUD de usuarios de la empresa."""
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render

from base_datos.models import Categoria, Usuario

from ..forms import UsuarioForm

from .comunes import _get_empresa


@login_required
def usuarios(request):
    empresa = _get_empresa(request)
    lista = list(Usuario.objects.filter(empresa=empresa).order_by('-activo', 'nombre'))
    # Nombres de las categorías asignadas a cada usuario (id_categorias es JSON de PKs)
    cat_map = {c.id_categoria: c.categoria for c in Categoria.objects.filter(empresa=empresa)}
    for u in lista:
        ids = u.id_categorias or []
        u.categorias_nombres = [cat_map[i] for i in ids if i in cat_map]
    return render(request, 'pages/usuarios/usuarios.html', {
        'page': 'usuarios',
        'usuarios': lista,
    })


def _guardar_usuario(usuario, empresa, form):
    """Completa empresa + id_categorias (desde el multiselect) y guarda."""
    usuario.empresa = empresa
    usuario.id_categorias = [str(c.id_categoria) for c in form.cleaned_data['categorias']]
    usuario.save()


@login_required
def usuario_crear(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, empresa=empresa)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.id_usuario = str(uuid.uuid4())
            _guardar_usuario(usuario, empresa, form)
            messages.success(request, f'Usuario "{usuario.nombre}" creado.')
            return redirect('usuarios')
    else:
        form = UsuarioForm(empresa=empresa)
    return render(request, 'pages/usuarios/usuario_form.html', {
        'form': form, 'page': 'usuarios', 'accion': 'Nuevo usuario',
    })


@login_required
def usuario_editar(request, pk):
    empresa = _get_empresa(request)
    usuario = get_object_or_404(Usuario, id_usuario=pk, empresa=empresa)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario, empresa=empresa)
        if form.is_valid():
            obj = form.save(commit=False)
            _guardar_usuario(obj, empresa, form)
            cache.delete(f'usuario_web:{request.user.pk}')  # por si editó su propio acceso
            messages.success(request, f'Usuario "{obj.nombre}" actualizado.')
            return redirect('usuarios')
    else:
        form = UsuarioForm(instance=usuario, empresa=empresa)
    return render(request, 'pages/usuarios/usuario_form.html', {
        'form': form, 'page': 'usuarios', 'accion': 'Editar usuario', 'objeto': usuario,
    })


@login_required
def usuario_eliminar(request, pk):
    empresa = _get_empresa(request)
    usuario = get_object_or_404(Usuario, id_usuario=pk, empresa=empresa)
    if request.method == 'POST':
        # Baja lógica: eliminar en duro arrastraría sus facturas y movimientos (CASCADE)
        usuario.activo = False
        usuario.save()
        cache.delete(f'usuario_web:{request.user.pk}')
        messages.success(request, f'Usuario "{usuario.nombre}" desactivado.')
        return redirect('usuarios')
    return render(request, 'pages/shared/confirm_delete.html', {
        'objeto': usuario, 'nombre': usuario.nombre, 'tipo': 'Usuario',
        'cancelar_url': 'usuarios', 'page': 'usuarios', 'desactivar': True,
    })
