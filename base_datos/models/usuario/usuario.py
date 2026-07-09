from django.db import models


class Usuario(models.Model):
    """Usuario de la app móvil. tipo_usuario: 'administrador' | 'trabajador'."""
    id_usuario    = models.CharField(max_length=36, primary_key=True)
    empresa       = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    nombre        = models.CharField(max_length=255)
    correo        = models.EmailField()
    tipo_usuario  = models.CharField(max_length=20)
    id_categorias = models.JSONField(default=list)   # categorías que puede ver el trabajador
    vistas        = models.JSONField(default=list)    # pantallas habilitadas
    seccion       = models.CharField(max_length=100, null=True, blank=True)
    foto_url      = models.URLField(null=True, blank=True)
    activo        = models.BooleanField(default=True)
    created_at    = models.DateTimeField(null=True, blank=True)
    sync_status   = models.CharField(max_length=20, default='synced')
    device_id     = models.CharField(max_length=255, null=True, blank=True)
    es_super_admin = models.BooleanField(default=False)

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.nombre
