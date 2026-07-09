from django.db import models


class Proveedor(models.Model):
    """Proveedor de artículos. Asociado a una empresa."""
    id_proveedor    = models.CharField(max_length=36, primary_key=True)
    empresa         = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    rut             = models.CharField(max_length=20, null=True, blank=True)
    nombre          = models.CharField(max_length=255)
    correo          = models.EmailField(null=True, blank=True)
    numero_contacto = models.CharField(max_length=30, null=True, blank=True)
    forma_pago      = models.CharField(max_length=50, null=True, blank=True)
    foto_url        = models.URLField(null=True, blank=True)
    activo          = models.BooleanField(default=True)
    created_at      = models.DateTimeField(null=True, blank=True)
    sync_status     = models.CharField(max_length=20, default='pending')

    class Meta:
        db_table = 'proveedor'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.nombre
