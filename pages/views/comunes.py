"""Helpers compartidos por todas las vistas: empresa/usuario del request."""
import math

from django.core.cache import cache

from base_datos.models import Empresa, Usuario


def _round10(val):
    """Redondea al múltiplo de 10 más cercano (≤4 baja, ≥5 sube)."""
    val = float(val)
    return int(math.floor(val / 10 + 0.5)) * 10


def _get_empresa_demo():
    """Empresa por defecto para el login web local (admin) sin usuario de la app."""
    empresa, _ = Empresa.objects.get_or_create(
        id_empresa='00000000-0000-0000-0000-000000000001',
        defaults={'nombre': 'Mi Negocio', 'rut': '00.000.000-0', 'activo': True}
    )
    return empresa


def _get_usuario(request):
    """
    Usuario de la app (tabla usuario) vinculado al login web por correo.
    Si el correo no existe en la tabla, se usa el usuario web por defecto
    asociado a la empresa demo.
    Cacheado 60 s por usuario web: evita repetir la consulta en cada request.
    """
    cache_key = f'usuario_web:{request.user.pk}'
    usuario = cache.get(cache_key)
    if usuario is not None:
        return usuario

    email = (getattr(request.user, 'email', '') or request.user.get_username() or '').strip()
    usuario = None
    if email:
        usuario = (
            Usuario.objects
            .filter(correo__iexact=email, activo=True)
            .select_related('empresa')
            .first()
        )
    if usuario is None:
        empresa = _get_empresa_demo()
        usuario, _ = Usuario.objects.get_or_create(
            id_usuario='00000000-0000-0000-0000-000000000002',
            defaults={
                'empresa': empresa,
                'nombre': 'Admin Web',
                'correo': 'admin@nexamarket.com',
                'tipo_usuario': 'administrador',
                'activo': True,
            }
        )
    _ = usuario.empresa  # precargar la relación antes de cachear
    cache.set(cache_key, usuario, 60)
    return usuario


def _get_empresa(request):
    """Empresa del usuario logueado — cada usuario solo ve datos de su empresa."""
    usuario = _get_usuario(request)
    return usuario.empresa if usuario.empresa_id else _get_empresa_demo()
