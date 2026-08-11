from django.db import models


class Usuario(models.Model):
    """Usuario de la app móvil. tipo_usuario: 'administrador' | 'trabajador'."""

    # Secciones de la web que se pueden habilitar por usuario. La clave es el
    # `url_name` de la vista, así el menú y el middleware hablan el mismo idioma.
    #
    # Quedan fuera a propósito "Mi Empresa" y "Mis Pagos": son los datos de la
    # cuenta y la facturación, y bloquearlos dejaría a alguien sin poder pagar
    # ni completar sus datos tributarios.
    VISTAS_WEB = [
        ('dashboard',      'Dashboard'),
        ('productos',      'Productos'),
        ('inventario',     'Inventario'),
        ('punto_venta',    'Punto de Venta'),
        ('punto_compra',   'Punto de Compra'),
        ('merma',          'Merma'),
        ('compras_ventas', 'Compras / Ventas'),
        ('movimientos',    'Movimientos'),
        ('categorias',     'Categorías'),
        ('proveedores',    'Proveedores'),
        ('usuarios',       'Usuarios'),
        ('personalizacion', 'Personalización'),
    ]

    id_usuario    = models.CharField(max_length=36, primary_key=True)
    empresa       = models.ForeignKey('Empresa', null=True, blank=True, on_delete=models.CASCADE)
    nombre        = models.CharField(max_length=255)
    correo        = models.EmailField()
    tipo_usuario  = models.CharField(max_length=20)
    id_categorias = models.JSONField(default=list, null=True, blank=True)   # categorías que puede ver el trabajador
    vistas        = models.JSONField(default=list, null=True, blank=True)   # pantallas del móvil
    vistas_web    = models.JSONField(default=list, null=True, blank=True)   # secciones de la web
    seccion       = models.CharField(max_length=100, null=True, blank=True)
    foto_url      = models.URLField(null=True, blank=True)
    activo        = models.BooleanField(default=True)
    created_at    = models.DateTimeField(null=True, blank=True)
    sync_status   = models.CharField(max_length=20, default='synced')
    device_id     = models.CharField(max_length=255, null=True, blank=True)
    es_super_admin = models.BooleanField(default=False)
    auth_id       = models.UUIDField(null=True, blank=True)  # id del usuario en Supabase Auth (auth.users)

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.nombre

    def puede_ver(self, vista):
        """
        ¿Este usuario tiene habilitada esa sección de la web?

        Dos reglas de seguridad, ambas a propósito:

        - Sin lista configurada ve todo. Los usuarios que ya existen tienen
          `vistas_web` en nulo, y no pueden quedarse sin acceso al desplegar.
        - El administrador ve todo siempre. Si pudiera restringirse, alcanzaría
          con desmarcarse "Usuarios" para quedar sin forma de volver atrás.
        """
        if self.tipo_usuario == 'administrador' or self.es_super_admin:
            return True
        if not self.vistas_web:
            return True
        return vista in self.vistas_web

    @property
    def vistas_web_permitidas(self):
        """Las secciones que ve, ya resueltas — para pintar el menú."""
        return [clave for clave, _ in self.VISTAS_WEB if self.puede_ver(clave)]
