"""
Cliente de Flow (flow.cl) para el cobro de la suscripción.

El recorrido completo:

  1. `crear_orden()` registra el cobro en Flow y devuelve la URL a la que hay
     que mandar al cliente.
  2. El cliente paga en el formulario de Flow (por dentro, Webpay).
  3. Flow hace un POST servidor-a-servidor a `urlConfirmation` con un token.
  4. `consultar_estado(token)` le pregunta a Flow qué pasó de verdad.

El paso 4 es el que importa: **solo la respuesta de Flow confirma un pago**.
El POST del paso 3 se toma nada más como aviso de "algo cambió", y la vuelta
del navegador (`urlReturn`) no confirma nada porque la controla el cliente —
cualquiera puede llegar a esa URL sin haber pagado.

La firma `s` es HMAC-SHA256 sobre los parámetros ordenados por nombre y
concatenados como nombre+valor sin separadores, con la secret key del comercio.
"""
import hashlib
import hmac

import requests
from django.conf import settings

TIMEOUT = 20

# Estados que devuelve payment/getStatus
PENDIENTE = 1
PAGADO = 2
RECHAZADO = 3
ANULADO = 4


def configurado():
    """¿Hay credenciales? Sin esto no se le ofrece Flow al cliente."""
    return bool(settings.FLOW_API_KEY and settings.FLOW_SECRET_KEY)


def _base_url():
    return 'https://sandbox.flow.cl/api' if settings.FLOW_SANDBOX else 'https://www.flow.cl/api'


def firmar(params):
    """HMAC-SHA256 de los parámetros ordenados por nombre, concatenados nombre+valor."""
    cadena = ''.join(f'{clave}{params[clave]}' for clave in sorted(params))
    return hmac.new(
        settings.FLOW_SECRET_KEY.encode(),
        cadena.encode(),
        hashlib.sha256,
    ).hexdigest()


def crear_orden(*, orden, monto, asunto, email, url_confirmacion, url_retorno):
    """
    Registra el cobro en Flow. Devuelve (datos, error); `datos` trae la URL de
    redirección, el token y el flowOrder.
    """
    params = {
        'apiKey': settings.FLOW_API_KEY,
        'commerceOrder': str(orden),
        'subject': asunto,
        'currency': 'CLP',
        'amount': int(monto),
        'email': email,
        'urlConfirmation': url_confirmacion,
        'urlReturn': url_retorno,
    }
    params['s'] = firmar(params)

    try:
        resp = requests.post(f'{_base_url()}/payment/create', data=params, timeout=TIMEOUT)
    except requests.RequestException:
        return None, 'No se pudo conectar con Flow. Intenta de nuevo en unos minutos.'

    if resp.status_code != 200:
        return None, f'Flow rechazó la solicitud de pago (HTTP {resp.status_code}).'

    try:
        datos = resp.json()
        return {
            'url': f"{datos['url']}?token={datos['token']}",
            'token': datos['token'],
            'flow_order': datos.get('flowOrder'),
        }, None
    except (ValueError, KeyError):
        return None, 'Flow devolvió una respuesta que no se pudo interpretar.'


def consultar_estado(token):
    """Pregunta a Flow el estado real de un pago. Devuelve (datos, error)."""
    params = {'apiKey': settings.FLOW_API_KEY, 'token': token}
    params['s'] = firmar(params)

    try:
        resp = requests.get(f'{_base_url()}/payment/getStatus', params=params, timeout=TIMEOUT)
    except requests.RequestException:
        return None, 'No se pudo consultar el estado en Flow.'

    if resp.status_code != 200:
        return None, f'Flow respondió HTTP {resp.status_code} al consultar el estado.'

    try:
        return resp.json(), None
    except ValueError:
        return None, 'Flow devolvió una respuesta que no se pudo interpretar.'
