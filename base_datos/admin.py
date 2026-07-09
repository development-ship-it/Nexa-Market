from django.contrib import admin
from .models import Empresa, Usuario, Categoria, Proveedor, Articulo, Factura, Stock, Configuracion

admin.site.register(Empresa)
admin.site.register(Usuario)
admin.site.register(Categoria)
admin.site.register(Proveedor)
admin.site.register(Articulo)
admin.site.register(Factura)
admin.site.register(Stock)
admin.site.register(Configuracion)
