from django.db import models


class ConfiguracionWeb(models.Model):
    """
    Personalización visual de la app WEB, por empresa.
    Tabla separada de 'configuracion' (que pertenece a la app móvil y
    se sincroniza desde allá) para poder evolucionar la web sin tocarla.
    """
    empresa        = models.OneToOneField(
        'Empresa', on_delete=models.CASCADE,
        related_name='config_web', primary_key=True,
    )
    color_primario = models.CharField(max_length=9, default='#2563eb')   # botones, item activo, gráficos
    color_acento   = models.CharField(max_length=9, default='#f5c211')   # detalles y resaltados
    color_fondo    = models.CharField(max_length=9, default='#f4f7fb')   # fondo general
    color_sidebar  = models.CharField(max_length=9, default='#ffffff')   # sidebar / topbar / tarjetas
    color_texto    = models.CharField(max_length=9, default='#0f1f33')   # texto principal
    logo_url       = models.URLField(null=True, blank=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_web'
        verbose_name = 'Configuración web'
        verbose_name_plural = 'Configuraciones web'

    def __str__(self):
        return f"Config web — {self.empresa}"
