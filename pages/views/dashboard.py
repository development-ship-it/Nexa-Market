"""Vista del dashboard: elige qué pestaña renderizar."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from base_datos.cache import cachear

from .comunes import _get_empresa
from .dashboard_filtros import resolver_periodo
from .dashboard_principal import _datos_dashboard


DASHBOARD_VISTAS = ('principal', 'productos', 'temporal', 'usuarios')


@login_required
def dashboard(request):
    empresa = _get_empresa(request)
    vista = request.GET.get('vista', 'principal')
    if vista not in DASHBOARD_VISTAS:
        vista = 'principal'

    ctx = {'page': 'dashboard', 'vista': vista}
    if vista == 'principal':
        periodo = resolver_periodo(request, empresa)
        ctx.update(cachear(empresa.pk, f'dashboard:{periodo["clave"]}',
                           lambda: _datos_dashboard(empresa, periodo)))
        ctx['periodo'] = periodo
    # 'productos', 'temporal' y 'usuarios' muestran el placeholder de "próximamente".
    # `dashboard_productos.py` y `_productos.html` quedan tal cual para cuando
    # se reactive esa pestaña: solo se dejó de calcular y de renderizar.
    return render(request, 'pages/dashboard/dashboard.html', ctx)
