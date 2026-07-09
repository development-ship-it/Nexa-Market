"""
Archivo principal de modelos — agrega los sub-modelos de cada carpeta.

Cada modelo vive en su propia carpeta (paquete) para poder añadir
sub-productos o sub-modelos sin tocar este archivo más que para
registrar la nueva entidad:

    base_datos/models/
        plan/           → Plan (suscripciones SaaS)
        empresa/        → Empresa (tenant raíz, discriminador SaaS)
        usuario/        → Usuario (app móvil: admin / trabajador)
        categoria/      → Categoria (agrupador de artículos)
        proveedor/      → Proveedor (proveedor de artículos)
        articulo/       → Articulo (catálogo; el stock se calcula desde Stock)
        factura/        → Factura (agrupa movimientos de un carrito confirmado)
        stock/          → Stock (libro append-only: ENTRADA=compra, SALIDA=venta)
        configuracion/  → Configuracion (personalización visual por empresa/usuario)

Para añadir un sub-modelo: crear el archivo dentro de la carpeta de la
entidad, exportarlo en el __init__.py de esa carpeta y añadirlo aquí.
"""

from .plan          import Plan
from .empresa       import Empresa
from .usuario       import Usuario
from .categoria     import Categoria
from .proveedor     import Proveedor
from .articulo      import Articulo
from .factura       import Factura
from .stock         import Stock
from .configuracion import Configuracion

__all__ = [
    'Plan',
    'Empresa',
    'Usuario',
    'Categoria',
    'Proveedor',
    'Articulo',
    'Factura',
    'Stock',
    'Configuracion',
]
