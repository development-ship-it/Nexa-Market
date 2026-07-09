"""
Context processors de pages: inyectan en todos los templates la empresa
del usuario logueado y su configuración visual web.
"""


def empresa_actual(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    try:
        from base_datos.models import ConfiguracionWeb
        from .views import _get_empresa

        empresa = _get_empresa(request)
        config, _ = ConfiguracionWeb.objects.get_or_create(empresa=empresa)
        return {'empresa_actual': empresa, 'config_web': config}
    except Exception:
        # Nunca romper el render por un problema de BD (p. ej. tabla aún no migrada)
        return {}
