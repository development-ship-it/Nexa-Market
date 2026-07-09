from django.db import models


class Plan(models.Model):
    """Planes de suscripción SaaS. Gratuito = local, Pro = sincronización en la nube."""
    id_plan            = models.AutoField(primary_key=True)
    nombre             = models.CharField(max_length=100)
    descripcion        = models.TextField(null=True, blank=True)
    precio_base        = models.IntegerField(default=0)
    precio_por_usuario = models.IntegerField(default=0)
    activo             = models.BooleanField(default=True)
    created_at         = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        db_table = 'plan'
        verbose_name = 'Plan'
        verbose_name_plural = 'Planes'

    def __str__(self):
        return self.nombre
