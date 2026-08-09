import uuid

from django.db import models


def _nuevo_id():
    return str(uuid.uuid4())


class SolicitudPremium(models.Model):
    """
    Un cliente pide pasarse a un plan de pago. No decide acceso — es la bandeja
    de entrada que gestiona el super admin. Cuando se concreta se enlaza con el
    `Pago` que la cerró.

    Se guarda el historial completo a propósito: un cliente puede pedir en
    marzo, no concretar, y volver a pedir en julio. Eso es información de venta
    que un simple campo de estado en `Empresa` no conserva.
    """

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONTACTADO', 'Contactado'),
        ('CONVERTIDA', 'Convertida'),
        ('DESCARTADA', 'Descartada'),
    ]

    id_solicitud = models.CharField(max_length=36, primary_key=True, default=_nuevo_id)
    empresa = models.ForeignKey(
        'Empresa', on_delete=models.CASCADE,
        related_name='solicitudes_premium', db_column='id_empresa',
    )
    plan = models.ForeignKey(
        'Plan', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='solicitudes', db_column='id_plan',
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    pago = models.ForeignKey(
        'Pago', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='solicitudes', db_column='id_pago',
    )
    nota = models.TextField(null=True, blank=True)  # notas internas de gestión

    class Meta:
        db_table = 'solicitud_premium'
        verbose_name = 'Solicitud de premium'
        verbose_name_plural = 'Solicitudes de premium'
        ordering = ['-fecha_solicitud']
        indexes = [models.Index(fields=['estado', 'fecha_solicitud'])]

    def __str__(self):
        return f"{self.empresa_id} — {self.get_estado_display()}"
