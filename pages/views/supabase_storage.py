"""Subida de fotos de artículos a Supabase Storage.

La app móvil guarda las fotos en el bucket `Articulos-Imagen`, con la ruta
`{empresa_id}/{uuid}.{ext}` y expone la URL pública. La web hace exactamente lo
mismo: así las fotos son durables y consistentes con el móvil (el disco de
Render es efímero y el ImageField local no sirve en producción).
"""
import uuid

import requests
from django.conf import settings

MAX_BYTES = 5 * 1024 * 1024          # 5 MB, igual que dice la interfaz
EXT_POR_TIPO = {
    'image/jpeg': 'jpg', 'image/jpg': 'jpg',
    'image/png': 'png', 'image/webp': 'webp',
}


def subir_comprobante(empresa_id, archivo):
    """Comprobante de transferencia: misma subida, en su propia carpeta."""
    return subir_imagen_articulo(empresa_id, archivo, carpeta='comprobantes')


def subir_imagen_articulo(empresa_id, archivo, carpeta=None):
    """Sube `archivo` (UploadedFile) al bucket y devuelve (url, error).

    - (url, None)   → subida correcta, `url` es la pública.
    - (None, texto) → algo que el usuario debe ver (muy grande, formato, fallo).
    - (None, None)  → no había archivo (nada que hacer).
    """
    if not archivo:
        return None, None

    base = (settings.SUPABASE_URL or '').rstrip('/')
    key = settings.SUPABASE_ANON_KEY
    if not base or not key:
        return None, 'El almacenamiento de imágenes no está configurado.'

    if archivo.size > MAX_BYTES:
        return None, 'La imagen supera los 5 MB.'

    tipo = (archivo.content_type or '').lower()
    ext = EXT_POR_TIPO.get(tipo)
    if not ext:
        return None, 'Formato no soportado. Usa JPG, PNG o WEBP.'

    prefijo = f'{carpeta}/' if carpeta else ''
    ruta = f'{prefijo}{empresa_id}/{uuid.uuid4()}.{ext}'
    endpoint = f'{base}/storage/v1/object/{settings.SUPABASE_BUCKET}/{ruta}'
    try:
        resp = requests.post(
            endpoint,
            data=archivo.read(),
            headers={
                'Authorization': f'Bearer {key}',
                'apikey': key,
                'Content-Type': tipo,
                'x-upsert': 'true',
            },
            timeout=20,
        )
    except requests.RequestException:
        return None, 'No se pudo conectar con el almacenamiento. Intenta de nuevo.'

    if resp.status_code not in (200, 201):
        # 400/403 suele ser permiso del bucket (RLS) para la anon key.
        return None, 'No se pudo subir la imagen (permiso del bucket o error del servidor).'

    return f'{base}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{ruta}', None
