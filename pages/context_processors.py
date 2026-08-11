"""
Context processors de pages: inyectan en todos los templates la empresa
del usuario logueado y su configuración visual web.
"""


def empresa_actual(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    try:
        from .views import _get_empresa, _get_usuario
        empresa = _get_empresa(request)
        usuario = _get_usuario(request)   # ya viene del caché, no cuesta otra consulta
    except Exception:
        # Nunca romper el render por un problema de BD
        return {}

    # Misma función que usa el middleware: el menú nunca ofrece algo que después
    # rebote por falta de pago.
    from .middleware import acceso_bloqueado

    ctx = {
        'empresa_actual': empresa,
        'suscripcion_bloqueada': acceso_bloqueado(request),
        # Secciones habilitadas para este usuario: el menú se dibuja con esto y
        # el middleware corta con lo mismo, así no pueden discrepar.
        'vistas_permitidas': usuario.vistas_web_permitidas,
    }
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
