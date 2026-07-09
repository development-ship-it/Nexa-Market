from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Login con Google (OAuth 2.0)
    path('auth/google/', views.google_login, name='google_login'),
    path('auth/callback/', views.google_callback, name='google_callback'),

    path('dashboard/', views.dashboard, name='dashboard'),

    # Productos
    path('productos/', views.productos, name='productos'),
    path('productos/nuevo/', views.producto_crear, name='producto_crear'),
    path('productos/<str:pk>/editar/', views.producto_editar, name='producto_editar'),
    path('productos/<str:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),

    # Categorías
    path('categorias/', views.categorias, name='categorias'),
    path('categorias/nueva/', views.categoria_crear, name='categoria_crear'),
    path('categorias/<str:pk>/editar/', views.categoria_editar, name='categoria_editar'),
    path('categorias/<str:pk>/eliminar/', views.categoria_eliminar, name='categoria_eliminar'),

    # Proveedores
    path('proveedores/', views.proveedores, name='proveedores'),
    path('proveedores/nuevo/', views.proveedor_crear, name='proveedor_crear'),
    path('proveedores/<str:pk>/editar/', views.proveedor_editar, name='proveedor_editar'),
    path('proveedores/<str:pk>/eliminar/', views.proveedor_eliminar, name='proveedor_eliminar'),

    # Empresa
    path('empresa/', views.empresa, name='empresa'),

    # API interna
    path('api/articulo/<str:pk>/precios/', views.api_precios_update, name='api_precios_update'),

    # Otras
    path('punto-compra/', views.punto_compra, name='punto_compra'),
    path('inventario/', views.inventario, name='inventario'),
    path('punto-venta/', views.punto_venta, name='punto_venta'),
    path('compras-ventas/', views.compras_ventas, name='compras_ventas'),
    path('movimientos/', views.movimientos, name='movimientos'),
]
