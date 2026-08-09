"""Mis Pagos: estado de la suscripción del cliente, próximo cobro e historial."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from base_datos.models import Plan, SolicitudPremium

from .comunes import _get_empresa

# Estados en los que una solicitud sigue abierta: mientras exista una, no se
# crean duplicados aunque el cliente insista con el botón.
SOLICITUD_ABIERTA = ['PENDIENTE', 'CONTACTADO']


@login_required
def mis_pagos(request):
    empresa = _get_empresa(request)

    solicitud_abierta = (
        SolicitudPremium.objects
        .filter(empresa=empresa, estado__in=SOLICITUD_ABIERTA)
        .select_related('plan')
        .first()
    )

    if request.method == 'POST':
        if solicitud_abierta:
            messages.info(request, 'Ya tienes una solicitud en curso, te contactaremos pronto.')
        else:
            plan_id = request.POST.get('id_plan') or None
            SolicitudPremium.objects.create(
                empresa=empresa,
                plan=Plan.objects.filter(pk=plan_id).first() if plan_id else None,
            )
            messages.success(request, 'Solicitud enviada. Te contactaremos para activar tu plan.')
        return redirect('mis_pagos')

    planes = Plan.objects.filter(activo=True).order_by('precio_base')
    if empresa.id_plan_id:
        planes = planes.exclude(pk=empresa.id_plan_id)

    return render(request, 'pages/pagos/mis_pagos.html', {
        'page': 'mis_pagos',
        'empresa': empresa,
        'cobro': empresa.calcular_cobro(),
        'pagos': empresa.pagos.select_related('plan')[:24],
        'planes': planes,
        'solicitud_abierta': solicitud_abierta,
    })
