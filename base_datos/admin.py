from django.contrib import admin, messages
from django.utils.html import format_html

from .models import (
    Articulo, Categoria, Configuracion, ConfiguracionWeb, Empresa, Factura,
    Pago, Proveedor, SolicitudPremium, Stock, Usuario,
)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'id_plan', 'estado_calculado',
                    'fecha_vencimiento', 'usuarios_activos', 'descuento_porcentaje')
    list_filter = ('estado_suscripcion', 'id_plan', 'activo')
    search_fields = ('nombre', 'rut', 'id_empresa')

    @admin.display(description='Estado real')
    def estado_calculado(self, obj):
        """El calculado desde la fecha, no la etiqueta guardada."""
        return obj.estado_actual


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """
    Bandeja de revisión de pagos. El trabajo diario es: filtrar por PENDIENTE,
    abrir el comprobante, comparar con la cartola y confirmar.
    """
    list_display = ('fecha_pago', 'empresa', 'plan', 'monto_total', 'metodo_pago',
                    'estado', 'referencia_externa', 'ver_comprobante', 'periodo_fin')
    list_filter = ('estado', 'metodo_pago', 'plan')
    search_fields = ('empresa__nombre', 'referencia_externa', 'id_pago')
    date_hierarchy = 'fecha_pago'
    actions = ('confirmar_pagos',)
    readonly_fields = ('created_at', 'fecha_confirmacion', 'periodo_inicio',
                       'periodo_fin', 'confirmado_por', 'ver_comprobante')

    @admin.display(description='Comprobante')
    def ver_comprobante(self, obj):
        if not obj.comprobante_url:
            return '—'
        return format_html('<a href="{}" target="_blank" rel="noopener">Ver foto</a>',
                           obj.comprobante_url)

    @admin.action(description='Confirmar los pagos seleccionados')
    def confirmar_pagos(self, request, queryset):
        """
        Confirma, calcula el periodo y deja la empresa vigente. Los que ya
        estaban confirmados se saltan: `confirmar()` es idempotente.
        """
        # El Usuario de la app que corresponde al admin logueado, para dejar
        # registrado quién aprobó cada pago.
        quien = Usuario.objects.filter(correo__iexact=request.user.email or '').first()

        confirmados = omitidos = 0
        for pago in queryset:
            if pago.estado == 'CONFIRMADO':
                omitidos += 1
                continue
            pago.confirmar(quien)
            confirmados += 1

        if confirmados:
            self.message_user(request, f'{confirmados} pago(s) confirmado(s).',
                              messages.SUCCESS)
        if omitidos:
            self.message_user(request, f'{omitidos} ya estaban confirmados.',
                              messages.INFO)


@admin.register(SolicitudPremium)
class SolicitudPremiumAdmin(admin.ModelAdmin):
    list_display = ('fecha_solicitud', 'empresa', 'plan', 'estado', 'pago')
    list_filter = ('estado', 'plan')
    search_fields = ('empresa__nombre',)
    date_hierarchy = 'fecha_solicitud'


admin.site.register(Usuario)
admin.site.register(Categoria)
admin.site.register(Proveedor)
admin.site.register(Articulo)
admin.site.register(Factura)
admin.site.register(Stock)
admin.site.register(Configuracion)
admin.site.register(ConfiguracionWeb)
