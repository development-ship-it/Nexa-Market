from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pages',
    'base_datos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pages.middleware.SuscripcionRequeridaMiddleware',
]

ROOT_URLCONF = 'NexaMarket.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'pages.context_processors.empresa_actual',
            ],
        },
    },
]

WSGI_APPLICATION = 'NexaMarket.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # conn_max_age: reutiliza la conexión entre requests (persistente 10 min)
    # conn_health_checks: verifica la conexión antes de usarla (evita errores del pooler)
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, conn_health_checks=True)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = []

# Caché en memoria: las lecturas pesadas se guardan 60 s.
# Los cambios hechos desde la web invalidan al instante (base_datos/signals.py);
# los hechos desde la app móvil se reflejan en máximo 1 minuto.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 60,
    }
}

# Sesiones: lee desde el caché y escribe en la BD (menos consultas por request)
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Login con Google (OAuth 2.0 directo) — Google Cloud Console > Credentials
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

# Muro de pago: sin suscripción vigente, la web solo deja ver Mis Pagos.
# Los super admin (Django o `usuario.es_super_admin`) nunca quedan bloqueados.
# Ponlo en False si te dejas afuera durante el desarrollo.
MURO_DE_PAGO = os.getenv('MURO_DE_PAGO', 'True') == 'True'

# Flow (flow.cl) — Mi Comercio > Configuración > API. La secret key firma las
# peticiones: si se filtra, cualquiera puede crear cobros a tu nombre.
FLOW_API_KEY = os.getenv('FLOW_API_KEY', '')
FLOW_SECRET_KEY = os.getenv('FLOW_SECRET_KEY', '')
# Sandbox: https://sandbox.flow.cl/api — Producción: https://www.flow.cl/api
FLOW_API_BASE = os.getenv('FLOW_API_BASE', 'https://sandbox.flow.cl/api').rstrip('/')
FLOW_CURRENCY = os.getenv('FLOW_CURRENCY', 'CLP')
# Medio de pago que se le ofrece al cliente. 9 = todos los que tengas habilitados.
FLOW_PAYMENT_METHOD = os.getenv('FLOW_PAYMENT_METHOD', '9')

# Datos bancarios que se le muestran al cliente para pagar por transferencia.
TRANSFERENCIA = {
    'titular':     os.getenv('TRANSFERENCIA_TITULAR', ''),
    'rut':         os.getenv('TRANSFERENCIA_RUT', ''),
    'banco':       os.getenv('TRANSFERENCIA_BANCO', ''),
    'tipo_cuenta': os.getenv('TRANSFERENCIA_TIPO_CUENTA', 'Cuenta Corriente'),
    'numero':      os.getenv('TRANSFERENCIA_NUMERO', ''),
    'correo':      os.getenv('TRANSFERENCIA_CORREO', ''),
}

# Versión del Service Worker: cambia en cada deploy para invalidar el caché
# del navegador automáticamente (Render expone el commit desplegado).
SW_VERSION = (os.getenv('RENDER_GIT_COMMIT') or 'dev')[:12]

# Supabase API (opcional — Storage u otras integraciones)
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
# Bucket donde la app móvil guarda las fotos de artículos; la web usa el mismo.
SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET', 'Articulos-Imagen')

# Producción detrás del proxy de Render (HTTPS + CSRF)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']
