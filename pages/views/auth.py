"""Landing, login/logout web y login con Google (OAuth 2.0)."""
import secrets
from urllib.parse import urlencode

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import redirect, render


def index(request):
    """Landing pública: primera impresión de la app. Si ya hay sesión, va al dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'pages/landing/landing.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'pages/auth/login.html')


# ── AUTH CON GOOGLE (OAuth 2.0 directo) ──────────────────────────────────────

def google_login(request):
    """Paso 1: redirige a Google para autorizar (flujo de código OAuth 2.0)."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        messages.error(request, 'El login con Google no está configurado (faltan GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET en .env).')
        return redirect('login')

    state = secrets.token_urlsafe(32)
    request.session['google_oauth_state'] = state
    params = urlencode({
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': request.build_absolute_uri('/auth/callback/'),
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'prompt': 'select_account',
    })
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')


def google_callback(request):
    """Paso 2: Google devuelve ?code=... — se canjea por el perfil y se abre la sesión."""
    if request.GET.get('error'):
        messages.error(request, f"Google canceló el inicio de sesión ({request.GET['error']}).")
        return redirect('login')

    code = request.GET.get('code', '')
    state = request.GET.get('state', '')
    if not code or not state or state != request.session.pop('google_oauth_state', None):
        messages.error(request, 'Respuesta de Google inválida. Intenta iniciar sesión de nuevo.')
        return redirect('login')

    try:
        token_resp = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': request.build_absolute_uri('/auth/callback/'),
                'grant_type': 'authorization_code',
            },
            timeout=10,
        )
        if token_resp.status_code != 200:
            messages.error(request, 'Google rechazó el código de autorización. Intenta de nuevo.')
            return redirect('login')

        user_resp = requests.get(
            'https://openidconnect.googleapis.com/v1/userinfo',
            headers={'Authorization': f"Bearer {token_resp.json().get('access_token', '')}"},
            timeout=10,
        )
    except requests.RequestException:
        messages.error(request, 'No se pudo contactar a Google. Revisa tu conexión.')
        return redirect('login')

    if user_resp.status_code != 200:
        messages.error(request, 'No se pudo obtener tu perfil de Google.')
        return redirect('login')

    info = user_resp.json()
    email = info.get('email')
    if not email:
        messages.error(request, 'La cuenta de Google no entregó un email.')
        return redirect('login')

    user, created = User.objects.get_or_create(
        username=email,
        defaults={'email': email, 'first_name': (info.get('name') or '')[:150]},
    )
    if created:
        user.set_unusable_password()
        user.save()

    login(request, user)
    return redirect('dashboard')
