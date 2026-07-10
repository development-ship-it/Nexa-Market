"""
Context processors de pages: inyectan en todos los templates la empresa
del usuario logueado y su configuración visual web.
"""


def empresa_actual(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    try:
        from .views import _get_empresa
        empresa = _get_empresa(request)
    except Exception:
        # Nunca romper el render por un problema de BD
        return {}

    ctx = {'empresa_actual': empresa}
    try:
        from base_datos.cache import cachear
        from base_datos.models import ConfiguracionWeb

        def _cargar():
            config, _ = ConfiguracionWeb.objects.get_or_create(empresa=empresa)
            return config

        ctx['config_web'] = cachear(empresa.pk, 'config_web', _cargar)
    except Exception:
        # La tabla configuracion_web puede no existir aún (migración pendiente
        # de aplicar en el deploy) — la empresa se muestra igual.
        pass
    return ctx
