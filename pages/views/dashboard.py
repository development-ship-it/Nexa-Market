"""Vista del dashboard: elige qué pestaña renderizar."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from base_datos.cache import cachear

from .comunes import _get_empresa
from .dashboard_filtros import resolver_periodo
from .dashboard_principal import _datos_dashboard
from .dashboard_productos import _datos_productos


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
    elif vista == 'productos':
        ctx.update(cachear(empresa.pk, 'dash_productos', lambda: _datos_productos(empresa)))
    # 'temporal' y 'usuarios': sin datos por ahora (placeholders)
    return render(request, 'pages/dashboard/dashboard.html', ctx)
