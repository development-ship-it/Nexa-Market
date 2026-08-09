import uuid

from django.db import models, transaction
from django.utils import timezone

from base_datos.facturacion import sumar_un_mes


def _nuevo_id():
    return str(uuid.uuid4())


class Pago(models.Model):
    """
    Libro de pagos de la suscripción: la verdad histórica del cobro.
    `Empresa.fecha_vencimiento` es solo el estado actual, derivado de aquí.

    TRANSFERENCIA → nace PENDIENTE y lo confirma un super admin revisando el
    comprobante. FLOW → lo confirma el webhook servidor-a-servidor
    (`urlConfirmation`), nunca la vuelta del navegador del cliente.

    Backoffice de NexaMarket: esta tabla no es del tenant y no baja al móvil.
    """

    METODO_CHOICES = [
        ('TRANSFERENCIA', 'Transferencia'),
        ('FLOW', 'Flow'),
    ]
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADO', 'Confirmado'),
        ('RECHAZADO', 'Rechazado'),
        ('REEMBOLSADO', 'Reembolsado'),
    ]

    id_pago = models.CharField(max_length=36, primary_key=True, default=_nuevo_id)
    empresa = models.ForeignKey(
        'Empresa', on_delete=models.CASCADE,
        related_name='pagos', db_column='id_empresa',
    )
    plan = models.ForeignKey(
        'Plan', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='pagos', db_column='id_plan',
    )
    usuarios_cobrados = models.IntegerField(default=1)  # asientos congelados de este ciclo

    # ── Montos (pesos enteros; el precio publicado es IVA incluido) ────────────
    monto_neto  = models.IntegerField(default=0)
    monto_iva   = models.IntegerField(default=0)
    monto_total = models.IntegerField(default=0)
    monto_descuento       = models.IntegerField(default=0)
    descripcion_descuento = models.CharField(max_length=255, null=True, blank=True)

    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES, default='TRANSFERENCIA')
    estado      = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    # Nº de operación bancaria o flowOrder. Único: evita que el mismo comprobante
    # reenviado por WhatsApp se cargue dos veces.
    referencia_externa = models.CharField(max_length=100, null=True, blank=True, unique=True)

    fecha_pago         = models.DateTimeField()  # la que declara el cliente / la que informa Flow
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    periodo_inicio     = models.DateTimeField(null=True, blank=True)
    periodo_fin        = models.DateTimeField(null=True, blank=True)

    comprobante_url = models.URLField(null=True, blank=True)
    confirmado_por  = models.ForeignKey(
        'Usuario', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='pagos_confirmados',
    )

    # ── Costo de la pasarela — nulo en transferencia ───────────────────────────
    # Lo informa Flow, no se calcula: la tasa cambia según débito, crédito o cuotas.
    # El IVA va aparte porque es crédito fiscal recuperable en el F29.
    comision_neto  = models.IntegerField(null=True, blank=True)
    comision_iva   = models.IntegerField(null=True, blank=True)
    comision_total = models.IntegerField(null=True, blank=True)
    monto_abonado  = models.IntegerField(null=True, blank=True)  # lo que llega al banco
    fecha_abono    = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pago'
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago']
        indexes = [models.Index(fields=['empresa', 'estado'])]

    def __str__(self):
        return f"{self.empresa_id} — ${self.monto_total} ({self.get_estado_display()})"

    @property
    def porcentaje_comision(self):
        """Se deriva, no se guarda: Flow cobra distinto según el medio de pago."""
        if not self.comision_total or not self.monto_total:
            return None
        return round(self.comision_total * 100 / self.monto_total, 2)

    @transaction.atomic
    def confirmar(self, usuario=None):
        """
        Confirma el pago, calcula el periodo cubierto y actualiza la vigencia
        de la empresa.

        El periodo arranca en `max(fecha_pago, vencimiento vigente)`: si paga
        atrasado corre desde el pago, y si paga adelantado se encola después del
        vencimiento actual para que no pierda los días que ya tenía pagados.

        Idempotente: el webhook de Flow puede llegar repetido.
        """
        if self.estado == 'CONFIRMADO':
            return self

        empresa = self.empresa
        inicio = self.fecha_pago
        if empresa.fecha_vencimiento and empresa.fecha_vencimiento > inicio:
            inicio = empresa.fecha_vencimiento

        self.estado = 'CONFIRMADO'
        self.fecha_confirmacion = timezone.now()
        self.confirmado_por = usuario
        self.periodo_inicio = inicio
        self.periodo_fin = sumar_un_mes(inicio)
        self.save()

        empresa.fecha_vencimiento = self.periodo_fin
        empresa.estado_suscripcion = 'ACTIVA'
        campos = ['fecha_vencimiento', 'estado_suscripcion']
        if self.plan_id:
            empresa.id_plan_id = self.plan_id
            campos.append('id_plan')
        empresa.save(update_fields=campos)
        return self
