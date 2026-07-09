from django.db import models


class Empresa(models.Model):
    """Tenant raíz del SaaS. Todo registro lleva empresa como discriminador."""
    id_empresa       = models.CharField(max_length=36, primary_key=True)
    nombre           = models.CharField(max_length=255)
    rut              = models.CharField(max_length=20)
    activo           = models.BooleanField(default=True)
    fecha_pago       = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(null=True, blank=True)
    sync_status      = models.CharField(max_length=20, default='synced')
    id_plan          = models.ForeignKey(
        'Plan', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='empresas',
        db_column='id_plan',
    )
    usuarios_activos = models.IntegerField(default=1)

    class Meta:
        db_table = 'empresa'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nombre
