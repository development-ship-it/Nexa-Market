"""
Caché por empresa con invalidación por versión.

Cada empresa tiene un número de versión en el caché. Las claves de datos
incluyen esa versión, así que subirla (invalidar_empresa) hace que todas
las lecturas siguientes vuelvan a consultar la base de datos — sin tener
que borrar clave por clave.

- Cambios desde la WEB → señales (signals.py) suben la versión → instantáneo.
- Cambios desde la APP MÓVIL → no pasan por Django → los cubre el TTL (60 s).
"""

from django.core.cache import cache

TTL = 60  # segundos: desfase máximo para cambios hechos fuera de la web


def _version_key(empresa_id):
    return f'v:{empresa_id}'


def version_empresa(empresa_id):
    version = cache.get(_version_key(empresa_id))
    if version is None:
        version = 1
        cache.set(_version_key(empresa_id), version, None)  # sin expiración
    return version


def invalidar_empresa(empresa_id):
    """Sube la versión de la empresa: su caché queda obsoleto al instante."""
    if not empresa_id:
        return
    try:
        cache.incr(_version_key(empresa_id))
    except ValueError:
        cache.set(_version_key(empresa_id), 1, None)


def cachear(empresa_id, nombre, cargar, ttl=TTL):
    """Devuelve el valor cacheado o ejecuta `cargar()` y lo guarda."""
    key = f'datos:{empresa_id}:{version_empresa(empresa_id)}:{nombre}'
    datos = cache.get(key)
    if datos is None:
        datos = cargar()
        cache.set(key, datos, ttl)
    return datos
