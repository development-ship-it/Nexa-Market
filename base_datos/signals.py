"""
Invalidación automática del caché: cualquier guardado o borrado hecho
desde la web (ORM de Django) sube la versión de caché de su empresa,
así los cambios se ven al instante sin esperar el TTL.
"""

from django.db.models.signals import post_save, post_delete

from .cache import invalidar_empresa
from .models import (
    Empresa, Usuario, Categoria, Proveedor, Articulo,
    Factura, Stock, Configuracion, ConfiguracionWeb,
)

_MODELOS = (
    Empresa, Usuario, Categoria, Proveedor, Articulo,
    Factura, Stock, Configuracion, ConfiguracionWeb,
)


def _invalidar(sender, instance, **kwargs):
    if isinstance(instance, Empresa):
        invalidar_empresa(instance.pk)
    else:
        invalidar_empresa(getattr(instance, 'empresa_id', None))


for modelo in _MODELOS:
    post_save.connect(_invalidar, sender=modelo, dispatch_uid=f'inv_save_{modelo.__name__}')
    post_delete.connect(_invalidar, sender=modelo, dispatch_uid=f'inv_del_{modelo.__name__}')
