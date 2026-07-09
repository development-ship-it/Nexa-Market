from django.db import models


class Configuracion(models.Model):
    """Personalización visual y de módulos por empresa/usuario."""
    id_configuracion = models.CharField(max_length=36, primary_key=True)
    empresa          = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    usuario          = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    nombre_app       = models.CharField(max_length=100, null=True, blank=True)
    logo_url         = models.URLField(null=True, blank=True)
    color_primario   = models.CharField(max_length=9, default='#8B0000')
    color_secundario = models.CharField(max_length=9, null=True, blank=True)
    color_acento     = models.CharField(max_length=9, null=True, blank=True)
    color_texto      = models.CharField(max_length=9, null=True, blank=True)
    color_fondo      = models.CharField(max_length=9, null=True, blank=True)
    modo_oscuro      = models.BooleanField(default=False)
    updated_at       = models.DateTimeField(null=True, blank=True)
    sync_status      = models.CharField(max_length=20, default='pending')

    class Meta:
        db_table = 'configuracion'
        verbose_name = 'Configuración'
        verbose_name_plural = 'Configuraciones'

    def __str__(self):
        return f"Config — {self.empresa}"
