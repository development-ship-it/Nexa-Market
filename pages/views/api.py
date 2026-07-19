"""API interna (precios) y sincronización con la caché del navegador."""
import hashlib
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from base_datos.cache import cachear
from base_datos.models import Articulo, Factura, Stock

from .comunes import _get_empresa, _round10


@login_required
def api_precios_update(request, pk):
    """Actualiza precio_compra y precio_venta de un artículo vía AJAX (desde el carrito)."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    try:
        data = json.loads(request.body)
        articulo = get_object_or_404(Articulo, id_articulo=pk, empresa=_get_empresa(request))
        pc = _round10(float(data.get('precio_compra', articulo.precio_compra)))
        pv = _round10(float(data.get('precio_venta', articulo.precio_venta)))
        articulo.precio_compra = pc
        articulo.precio_venta = pv
        articulo.margen_ganancia = round(((pv - pc) / pc * 100) if pc > 0 else 0, 2)
        articulo.save(update_fields=['precio_compra', 'precio_venta', 'margen_ganancia'])
        return JsonResponse({'ok': True, 'precio_compra': pc, 'precio_venta': pv})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


# ── SINCRONIZACIÓN (caché en el navegador, estilo AppSheet) ──────────────────

def service_worker(request):
    """
    Sirve el Service Worker desde la raíz (/sw.js) para que su alcance sea
    todo el sitio. Si se sirviera desde /static/ solo controlaría esa carpeta.
    """
    return render(request, 'pages/sw.js', {'version': settings.SW_VERSION},
                  content_type='application/javascript')


@login_required
def api_estado(request):
    """
    Firma del estado de los datos de la empresa. El navegador la compara con
    la que tenía al sincronizar: si cambió, enciende el botón Sync.
    Es una respuesta minúscula y se cachea 30 s en el servidor, así el sondeo
    no golpea la base de datos.
    """
    from django.db.models import Max, Count

    empresa = _get_empresa(request)

    def _firma():
        art = Articulo.objects.filter(empresa=empresa).aggregate(n=Count('pk'), t=Max('updated_at'))
        fac = Factura.objects.filter(empresa=empresa).aggregate(t=Max('fecha'))
        stk = Stock.objects.filter(empresa=empresa).aggregate(t=Max('fecha_hora'))
        crudo = '|'.join(str(x) for x in (art['n'], art['t'], fac['t'], stk['t']))
        return hashlib.md5(crudo.encode()).hexdigest()[:16]

    # La clave de `cachear` incluye la versión de la empresa: un cambio hecho
    # desde la web la sube y recalcula al instante; los de la app móvil los
    # detecta el propio contenido de la firma (máximos de fecha).
    return JsonResponse({
        'firma': cachear(empresa.pk, 'firma', _firma, ttl=30),
        'usuario': request.user.pk,
    })
