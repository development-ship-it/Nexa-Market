"""Datos de la empresa y personalización visual de la web."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect, render

from base_datos.models import ConfiguracionWeb

from ..forms import ConfiguracionWebForm, EmpresaForm

from .comunes import _get_empresa


@login_required
def empresa(request):
    emp = _get_empresa(request)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            cache.delete(f'usuario_web:{request.user.pk}')  # refrescar nombre en el sidebar
            messages.success(request, 'Datos de la empresa actualizados.')
            return redirect('empresa')
    else:
        form = EmpresaForm(instance=emp)
    return render(request, 'pages/empresa/empresa.html', {'form': form, 'page': 'empresa', 'empresa': emp})


# ── PERSONALIZACIÓN ───────────────────────────────────────────────────────────

@login_required
def personalizacion(request):
    empresa = _get_empresa(request)
    config, _ = ConfiguracionWeb.objects.get_or_create(empresa=empresa)
    if request.method == 'POST':
        if 'restaurar' in request.POST:
            config.delete()
            ConfiguracionWeb.objects.create(empresa=empresa)
            messages.success(request, 'Colores restaurados a los valores por defecto.')
            return redirect('personalizacion')
        form = ConfiguracionWebForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Personalización guardada.')
            return redirect('personalizacion')
    else:
        form = ConfiguracionWebForm(instance=config)
    return render(request, 'pages/personalizacion/personalizacion.html', {
        'form': form, 'page': 'personalizacion',
    })
