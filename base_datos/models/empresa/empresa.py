from datetime import timedelta

from django.db import models
from django.utils import timezone

from base_datos.facturacion import DIAS_GRACIA, USUARIOS_INCLUIDOS, agregar_iva


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

    @property
    def estado_actual(self):
        """
        Estado real de la suscripción, calculado desde `fecha_vencimiento`.

        Es lo que hay que mostrar y lo que decide el acceso. El campo
        `estado_suscripcion` es una etiqueta guardada para poder filtrar en
        consultas (los avisos de n8n), pero se queda atrás sola cuando pasa el
        tiempo: nadie la actualiza al vencer. La fecha nunca miente.

        SIN_ACTIVAR = tiene un plan de pago asignado pero nunca pagó.
        """
        if not self.fecha_vencimiento:
            return 'SIN_ACTIVAR' if self.id_plan_id else 'GRATUITO'
        if self.en_gracia:
            return 'GRACIA'
        if self.esta_vigente:
            return 'ACTIVA'
        return 'VENCIDA'

    # ── Cobro ─────────────────────────────────────────────────────────────────

    def calcular_cobro(self, usuarios=None):
        """
        Desglose del próximo cobro mensual con el descuento negociado aplicado.

        Los precios del plan son **netos**: el base cubre `USUARIOS_INCLUIDOS`
        (el administrador) y recién del siguiente en adelante se cobra por
        usuario. El IVA se suma al final.

        Devuelve None si la empresa no tiene plan de pago asignado.
        """
        if not self.id_plan_id:
            return None

        plan = self.id_plan
        usuarios = max(1, self.usuarios_activos if usuarios is None else usuarios)
        adicionales = max(0, usuarios - USUARIOS_INCLUIDOS)

        bruto = plan.precio_base + plan.precio_por_usuario * adicionales
        descuento = round(bruto * self.descuento_porcentaje / 100)
        neto = bruto - descuento
        iva, total = agregar_iva(neto)
        return {
            'usuarios': usuarios,
            'incluidos': USUARIOS_INCLUIDOS,
            'adicionales': adicionales,
            'monto_base': plan.precio_base,
            'monto_adicionales': plan.precio_por_usuario * adicionales,
            'precio_usuario': plan.precio_por_usuario,
            'bruto': bruto,
            'descuento': descuento,
            'neto': neto,
            'iva': iva,
            'total': total,
        }
