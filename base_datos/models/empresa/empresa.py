from datetime import timedelta

from django.db import models
from django.utils import timezone

from base_datos.facturacion import DIAS_GRACIA, desglosar_iva


class Empresa(models.Model):
    """Tenant raíz del SaaS. Todo registro lleva empresa como discriminador."""

    ESTADO_SUSCRIPCION_CHOICES = [
        ('GRATUITO', 'Plan gratuito'),
        ('ACTIVA', 'Activa'),
        ('GRACIA', 'En periodo de gracia'),
        ('VENCIDA', 'Vencida'),
    ]

    id_empresa       = models.CharField(max_length=36, primary_key=True)
    nombre           = models.CharField(max_length=255)
    rut              = models.CharField(max_length=20)
    activo           = models.BooleanField(default=True)
    created_at       = models.DateTimeField(null=True, blank=True)
    sync_status      = models.CharField(max_length=20, default='synced')
    foto_url         = models.URLField(null=True, blank=True)  # logo del negocio (Supabase Storage)
    id_plan          = models.ForeignKey(
        'Plan', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='empresas',
        db_column='id_plan',
    )
    usuarios_activos = models.IntegerField(default=1)

    # ── Suscripción: estado actual. El histórico vive en `Pago` ────────────────
    # Se leen en cada request (login y app móvil), por eso están denormalizados
    # aquí en vez de recalcularse recorriendo los pagos.
    fecha_vencimiento    = models.DateTimeField(null=True, blank=True)
    estado_suscripcion   = models.CharField(
        max_length=20, choices=ESTADO_SUSCRIPCION_CHOICES, default='GRATUITO',
    )
    # Descuento negociado uno a uno, se aplica solo en cada cobro. Los cupones,
    # si algún día hacen falta, rellenan `Pago.monto_descuento` sin tocar esto.
    descuento_porcentaje = models.IntegerField(default=0)

    # ── Datos tributarios (para emitir boleta/factura de la suscripción) ───────
    razon_social = models.CharField(max_length=255, null=True, blank=True)
    giro         = models.CharField(max_length=255, null=True, blank=True)
    direccion    = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'empresa'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nombre

    # ── Vigencia ──────────────────────────────────────────────────────────────

    @property
    def dias_restantes(self):
        """Días hasta el vencimiento. Negativo si ya venció, None si no aplica."""
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - timezone.now()).days

    @property
    def esta_vigente(self):
        """¿Puede usar las funciones de pago hoy? Incluye el periodo de gracia."""
        if not self.fecha_vencimiento:
            return False
        return timezone.now() <= self.fecha_vencimiento + timedelta(days=DIAS_GRACIA)

    @property
    def en_gracia(self):
        """Venció pero sigue operando: toca avisar por correo, no cortar."""
        if not self.fecha_vencimiento:
            return False
        return self.fecha_vencimiento < timezone.now() <= self.fecha_vencimiento + timedelta(days=DIAS_GRACIA)

    # ── Cobro ─────────────────────────────────────────────────────────────────

    def calcular_cobro(self, usuarios=None):
        """
        Desglose del próximo cobro mensual con el descuento negociado aplicado.
        Los precios del plan son IVA incluido, así que el neto se despeja hacia
        atrás. Devuelve None si la empresa no tiene plan de pago asignado.
        """
        if not self.id_plan_id:
            return None

        plan = self.id_plan
        usuarios = self.usuarios_activos if usuarios is None else usuarios
        bruto = plan.precio_base + plan.precio_por_usuario * usuarios
        descuento = round(bruto * self.descuento_porcentaje / 100)
        total = bruto - descuento
        neto, iva = desglosar_iva(total)
        return {
            'usuarios': usuarios,
            'bruto': bruto,
            'descuento': descuento,
            'total': total,
            'neto': neto,
            'iva': iva,
        }
