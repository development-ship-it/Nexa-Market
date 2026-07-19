"""Vistas de la app `pages`, separadas por dominio.

Este archivo solo reexporta: `urls.py` sigue haciendo `from . import views` y
llamando `views.productos`, `views.dashboard`, etc. sin enterarse del cambio.
Para tocar una vista, ve directo a su módulo:

    comunes.py              empresa/usuario del request (lo usan todas)
    auth.py                 landing, login web y login con Google
    dashboard.py            elige la pestaña del dashboard
      dashboard_principal.py   datos de la pestaña principal
      dashboard_productos.py   datos de la pestaña productos
    productos.py            CRUD de artículos
    categorias.py           CRUD de categorías
    proveedores.py          CRUD de proveedores
    usuarios.py             CRUD de usuarios
    empresa.py              datos de empresa y personalización
    punto_compra.py         punto de compra
    punto_venta.py          punto de venta
    merma.py                bajas de stock por merma
    inventario.py           stock actual
    compras_ventas.py       listado de facturas
    movimientos.py          listado de movimientos de stock
    agrupamiento.py         helpers de agrupación por fecha (listados)
    api.py                  API interna y sincronización del navegador
"""
from .comunes import _round10, _get_empresa_demo, _get_usuario, _get_empresa

from .auth import index, login_view, google_login, google_callback
from .dashboard import DASHBOARD_VISTAS, dashboard
from .productos import productos, producto_crear, producto_editar, producto_eliminar
from .categorias import categorias, categoria_crear, categoria_editar, categoria_eliminar
from .proveedores import proveedores, proveedor_crear, proveedor_editar, proveedor_eliminar
from .usuarios import usuarios, usuario_crear, usuario_editar, usuario_eliminar
from .empresa import empresa, personalizacion
from .punto_compra import punto_compra
from .punto_venta import punto_venta
from .merma import merma
from .inventario import inventario
from .compras_ventas import compras_ventas
from .movimientos import movimientos
from .api import api_precios_update, service_worker, api_estado

__all__ = [
    '_round10', '_get_empresa_demo', '_get_usuario', '_get_empresa',
    'index', 'login_view', 'google_login', 'google_callback',
    'DASHBOARD_VISTAS', 'dashboard',
    'productos', 'producto_crear', 'producto_editar', 'producto_eliminar',
    'categorias', 'categoria_crear', 'categoria_editar', 'categoria_eliminar',
    'proveedores', 'proveedor_crear', 'proveedor_editar', 'proveedor_eliminar',
    'usuarios', 'usuario_crear', 'usuario_editar', 'usuario_eliminar',
    'empresa', 'personalizacion',
    'punto_compra', 'punto_venta', 'merma', 'inventario',
    'compras_ventas', 'movimientos',
    'api_precios_update', 'service_worker', 'api_estado',
]
