"""
Mis Pagos: estado de la suscripción, elección de plan y los dos caminos de pago.

TRANSFERENCIA → el cliente transfiere, sube la foto del comprobante y el pago
queda PENDIENTE hasta que un super admin lo revisa y confirma.

FLOW → el cliente paga en Flow y lo confirma el webhook servidor-a-servidor,
sin intervención manual.

Los dos terminan en la misma tabla `Pago`; lo único que cambia es quién pone el
estado en CONFIRMADO.
"""
import logging
from datetime import datetime, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from base_datos.facturacion import desglosar_iva
from base_datos.models import Pago, Plan, SolicitudPremium

from .. import flow
from .comunes import _get_empresa, _get_usuario
from .supabase_storage import subir_comprobante

log = logging.getLogger(__name__)

# Estados en los que una solicitud sigue abierta: mientras exista una, no se
# crean duplicados aunque el cliente insista con el botón.
SOLICITUD_ABIERTA = ['PENDIENTE', 'CONTACTADO']

# Tope del selector de usuarios. Más que esto ya no es autoservicio: es una
# conversación de venta, y conviene que pase por ti.
MAX_USUARIOS = 100


# ── PÁGINA PRINCIPAL ─────────────────────────────────────────────────────────

@login_required
def mis_pagos(request):
    empresa = _get_empresa(request)

    return render(request, 'pages/pagos/mis_pagos.html', {
        'page': 'mis_pagos',
        'empresa': empresa,
        'cobro': empresa.calcular_cobro(),
        'pagos': empresa.pagos.select_related('plan')[:24],
        # Con suscripción vigente no se cambia de plan a mano: se solicita.
        'planes': Plan.objects.filter(activo=True).order_by('precio_base'),
        'usuarios_minimo': _usuarios_en_uso(empresa),
        'flow_disponible': flow.configurado(),
        'solicitud_abierta': (
            SolicitudPremium.objects
            .filter(empresa=empresa, estado__in=SOLICITUD_ABIERTA)
            .select_related('plan')
            .first()
        ),
    })


def _usuarios_en_uso(empresa):
    """Usuarios activos reales. Es el piso de lo que puede contratar."""
    return max(1, empresa.usuario_set.filter(activo=True).count())


@login_required
def elegir_plan(request):
    """Asignar plan es gratis y no da acceso: lo que activa es el pago."""
    if request.method != 'POST':
        return redirect('mis_pagos')

    empresa = _get_empresa(request)
    if empresa.esta_vigente:
        # Ya está pagando: cambiar de plan a mitad de ciclo se coordina, no se
        # hace solo, porque hay que ver prorrateo y cobros ya emitidos.
        messages.info(request, 'Tu plan está activo. Solicita el cambio y lo coordinamos.')
        return redirect('mis_pagos')

    plan = Plan.objects.filter(pk=request.POST.get('id_plan'), activo=True).first()
    if not plan:
        messages.error(request, 'Ese plan no está disponible.')
        return redirect('mis_pagos')

    empresa.id_plan = plan
    empresa.save(update_fields=['id_plan'])
    if plan.precio_base or plan.precio_por_usuario:
        messages.success(request, f'Plan {plan.nombre} seleccionado. Ahora elige cómo pagar.')
    else:
        messages.success(request, 'Quedaste en el plan Gratuito.')
    return redirect('mis_pagos')


@login_required
def ajustar_usuarios(request):
    """Cuántos usuarios contrata. Nunca por debajo de los que ya tiene creados."""
    if request.method != 'POST':
        return redirect('mis_pagos')

    empresa = _get_empresa(request)
    try:
        cantidad = int(request.POST.get('usuarios') or 0)
    except ValueError:
        cantidad = 0

    minimo = _usuarios_en_uso(empresa)
    if cantidad < minimo:
        messages.error(
            request,
            f'Tienes {minimo} usuario(s) activo(s): no puedes contratar menos. '
            'Desactiva usuarios primero si quieres bajar el plan.',
        )
        return redirect('mis_pagos')
    if cantidad > MAX_USUARIOS:
        messages.error(request, f'Para más de {MAX_USUARIOS} usuarios, hablemos directamente.')
        return redirect('mis_pagos')

    empresa.usuarios_activos = cantidad
    empresa.save(update_fields=['usuarios_activos'])
    messages.success(request, f'Plan ajustado a {cantidad} usuario(s).')
    return redirect('mis_pagos')


@login_required
def solicitar_contacto(request):
    """Para quien prefiere coordinar el pago por WhatsApp en vez de pagar solo."""
    if request.method != 'POST':
        return redirect('mis_pagos')

    empresa = _get_empresa(request)
    if SolicitudPremium.objects.filter(empresa=empresa, estado__in=SOLICITUD_ABIERTA).exists():
        messages.info(request, 'Ya tienes una solicitud en curso, te contactaremos pronto.')
    else:
        SolicitudPremium.objects.create(empresa=empresa, plan=empresa.id_plan)
        messages.success(request, 'Solicitud enviada. Te vamos a contactar para coordinar el pago.')
    return redirect('mis_pagos')


# ── TRANSFERENCIA ────────────────────────────────────────────────────────────

@login_required
def pagar_transferencia(request):
    """Datos bancarios y subida del comprobante. El pago nace PENDIENTE."""
    empresa = _get_empresa(request)
    cobro = empresa.calcular_cobro()
    if not cobro:
        messages.error(request, 'Primero elige un plan.')
        return redirect('mis_pagos')

    if request.method == 'POST':
        error = _crear_pago_transferencia(request, empresa, cobro)
        if error:
            messages.error(request, error)
        else:
            messages.success(
                request,
                'Comprobante recibido. Vamos a revisarlo y activar tu plan apenas lo validemos.',
            )
            return redirect('mis_pagos')

    return render(request, 'pages/pagos/transferencia.html', {
        'page': 'mis_pagos',
        'empresa': empresa,
        'cobro': cobro,
        'datos': _datos_transferencia(),
        'hoy': timezone.localdate().isoformat(),
    })


def _datos_transferencia():
    from django.conf import settings
    return settings.TRANSFERENCIA


def _crear_pago_transferencia(request, empresa, cobro):
    """Valida el formulario y crea el Pago. Devuelve un texto de error o None."""
    texto_fecha = request.POST.get('fecha_pago') or ''
    referencia = (request.POST.get('referencia_externa') or '').strip()

    try:
        fecha = datetime.strptime(texto_fecha, '%Y-%m-%d').date()
    except ValueError:
        return 'Indica la fecha en que hiciste la transferencia.'

    # Se compara por día, no por instante: alguien que transfiere a las 9 y sube
    # el comprobante a las 10 está declarando hoy, y eso es válido.
    if fecha > timezone.localdate():
        return 'La fecha de la transferencia no puede ser futura.'

    # Para un día pasado se ancla a mediodía (evita que el huso mueva el día);
    # si es hoy se usa la hora actual, para no dejar el pago con fecha futura.
    fecha_pago = (
        timezone.now() if fecha == timezone.localdate()
        else timezone.make_aware(datetime.combine(fecha, time(12, 0)))
    )

    if not referencia:
        return 'Indica el número de operación de la transferencia.'

    url, error = subir_comprobante(empresa.pk, request.FILES.get('comprobante'))
    if error:
        return error
    if not url:
        return 'Adjunta la foto del comprobante.'

    try:
        Pago.objects.create(
            empresa=empresa,
            plan=empresa.id_plan,
            usuarios_cobrados=cobro['usuarios'],
            monto_neto=cobro['neto'],
            monto_iva=cobro['iva'],
            monto_total=cobro['total'],
            monto_descuento=cobro['descuento'],
            metodo_pago='TRANSFERENCIA',
            estado='PENDIENTE',
            referencia_externa=referencia,
            fecha_pago=fecha_pago,
            comprobante_url=url,
        )
    except IntegrityError:
        return 'Ese número de operación ya fue registrado. Revisa el comprobante.'
    return None


# ── FLOW ─────────────────────────────────────────────────────────────────────

@login_required
def pagar_flow(request):
    """Crea la orden en Flow y manda al cliente a pagar."""
    if request.method != 'POST':
        return redirect('mis_pagos')

    empresa = _get_empresa(request)
    cobro = empresa.calcular_cobro()
    if not cobro:
        messages.error(request, 'Primero elige un plan.')
        return redirect('mis_pagos')
    if not flow.configurado():
        messages.error(request, 'El pago con tarjeta no está disponible por ahora.')
        return redirect('mis_pagos')

    # El pago se crea antes de ir a Flow: su id es el `commerceOrder` con el que
    # después el webhook lo vuelve a encontrar.
    pago = Pago.objects.create(
        empresa=empresa,
        plan=empresa.id_plan,
        usuarios_cobrados=cobro['usuarios'],
        monto_neto=cobro['neto'],
        monto_iva=cobro['iva'],
        monto_total=cobro['total'],
        monto_descuento=cobro['descuento'],
        metodo_pago='FLOW',
        estado='PENDIENTE',
        fecha_pago=timezone.now(),
    )

    datos, error = flow.crear_orden(
        orden=pago.pk,
        monto=cobro['total'],
        asunto=f'NexaMarket — plan {empresa.id_plan.nombre}',
        email=_get_usuario(request).correo,
        url_confirmacion=request.build_absolute_uri(reverse('flow_confirmacion')),
        url_retorno=request.build_absolute_uri(reverse('flow_retorno')),
    )
    if error:
        pago.delete()  # no dejar pagos fantasma si Flow no aceptó la orden
        messages.error(request, error)
        return redirect('mis_pagos')

    return redirect(datos['url'])


@login_required
def flow_retorno(request):
    """
    urlReturn: solo la vuelta del navegador. No confirma nada — la controla el
    cliente. La confirmación real llega por `flow_confirmacion`.
    """
    messages.info(
        request,
        'Estamos confirmando tu pago con Flow. En unos segundos verás tu plan activo.',
    )
    return redirect('mis_pagos')


@csrf_exempt
def flow_confirmacion(request):
    """
    urlConfirmation: POST servidor-a-servidor de Flow.

    El contenido del POST no se cree: solo se toma el token y se le pregunta a
    Flow por el estado real. Es lo que evita que alguien active un plan gratis
    mandando un POST falso a esta URL.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    token = request.POST.get('token')
    if not token:
        return HttpResponse('sin token', status=400)

    datos, error = flow.consultar_estado(token)
    if error:
        log.error('Flow: no se pudo consultar el token %s — %s', token, error)
        return HttpResponse(status=502)  # que Flow reintente

    pago = Pago.objects.filter(pk=datos.get('commerceOrder')).first()
    if not pago:
        log.error('Flow: commerceOrder desconocido %s', datos.get('commerceOrder'))
        return HttpResponse('orden desconocida', status=404)

    estado = datos.get('status')
    if estado != flow.PAGADO:
        if pago.estado == 'PENDIENTE':
            pago.estado = 'RECHAZADO' if estado in (flow.RECHAZADO, flow.ANULADO) else pago.estado
            pago.save(update_fields=['estado'])
        return HttpResponse('OK')

    # Cobrado de más o de menos: no se activa nada y queda registrado para revisar.
    if int(datos.get('amount') or 0) != pago.monto_total:
        log.error('Flow: monto distinto en %s — Flow dice %s, el pago dice %s',
                  pago.pk, datos.get('amount'), pago.monto_total)
        return HttpResponse('OK')

    _guardar_datos_flow(pago, datos)
    pago.confirmar()  # idempotente: si Flow reintenta, no extiende dos veces
    return HttpResponse('OK')


def _guardar_datos_flow(pago, datos):
    """Guarda flowOrder y el costo real que informa Flow (no se calcula)."""
    pago.referencia_externa = str(datos.get('flowOrder') or pago.pk)

    detalle = datos.get('paymentData') or {}
    comision = detalle.get('fee')
    if comision is not None:
        # Flow informa la comisión con IVA incluido; se separa porque ese IVA es
        # crédito fiscal. Si al ver el primer abono real no cuadra, se ajusta aquí.
        total = int(float(comision))
        neto, iva = desglosar_iva(total)
        pago.comision_total, pago.comision_neto, pago.comision_iva = total, neto, iva

    abonado = detalle.get('balance')
    if abonado is not None:
        pago.monto_abonado = int(float(abonado))

    pago.save(update_fields=[
        'referencia_externa', 'comision_total', 'comision_neto',
        'comision_iva', 'monto_abonado',
    ])
