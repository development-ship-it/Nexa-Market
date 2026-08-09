"""
Muro de pago: sin suscripción vigente, la web solo deja ver Mis Pagos.

La web ES el producto de pago (el plan Gratuito es la app local en el celular),
así que una empresa sin pago asociado no debería ver el dashboard, el inventario
ni el punto de venta — solo la página para activar su plan.

Va como middleware y no como decorador a propósito: así una vista nueva queda
protegida por defecto en vez de depender de que alguien se acuerde de decorarla.
"""
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

# Vistas siempre accesibles: autenticación, la propia página de pago, y lo que
# necesita el service worker de la PWA para no romperse.
VISTAS_LIBRES = {
    'index', 'login', 'logout',
    'google_login', 'google_callback',
    # Todo el circuito de pago
    'mis_pagos', 'elegir_plan', 'solicitar_contacto',
    'pagar_transferencia', 'pagar_flow', 'flow_retorno', 'flow_confirmacion',
    # Sin pagar igual debe poder ver su empresa y sus usuarios: son los datos
    # que necesita completar (razón social, giro) para que le emitan la boleta.
    'empresa',
    'usuarios', 'usuario_crear', 'usuario_editar', 'usuario_eliminar',
    # Lo que necesita el service worker de la PWA para no romperse
    'service_worker', 'api_estado',
}


class SuscripcionRequeridaMiddleware:
    """Redirige a Mis Pagos cuando la empresa no tiene suscripción vigente."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(settings, 'MURO_DE_PAGO', True):
            return None
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return None

        match = request.resolver_match
        if match is None or match.url_name in VISTAS_LIBRES:
            return None
        if request.path.startswith('/admin/'):
            return None

        try:
            from .views import _get_empresa, _get_usuario

            # El super admin de NexaMarket entra siempre: es quien gestiona los
            # pagos y no puede quedar encerrado fuera de su propia herramienta.
            if request.user.is_superuser or _get_usuario(request).es_super_admin:
                return None

            empresa = _get_empresa(request)
            if empresa.esta_vigente:  # incluye el periodo de gracia
                return None
        except Exception:
            # Ante un problema de BD se deja pasar. Un cliente que entra gratis
            # un rato cuesta mucho menos que dejar afuera a los que sí pagaron.
            return None

        messages.warning(
            request,
            'Tu suscripción no está activa. Actívala para volver a usar NexaMarket.',
        )
        return redirect('mis_pagos')
