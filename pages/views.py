import uuid
import json
import math
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from base_datos.models import Empresa, Articulo, Categoria, Proveedor, Usuario, Factura, Stock, ConfiguracionWeb
from base_datos.cache import cachear
from .forms import ArticuloForm, CategoriaForm, ProveedorForm, EmpresaForm, ConfiguracionWebForm, UsuarioForm


def _round10(val):
    """Redondea al múltiplo de 10 más cercano (≤4 baja, ≥5 sube)."""
    val = float(val)
    return int(math.floor(val / 10 + 0.5)) * 10


def _get_empresa_demo():
    """Empresa por defecto para el login web local (admin) sin usuario de la app."""
    empresa, _ = Empresa.objects.get_or_create(
        id_empresa='00000000-0000-0000-0000-000000000001',
        defaults={'nombre': 'Mi Negocio', 'rut': '00.000.000-0', 'activo': True}
    )
    return empresa


def _get_usuario(request):
    """
    Usuario de la app (tabla usuario) vinculado al login web por correo.
    Si el correo no existe en la tabla, se usa el usuario web por defecto
    asociado a la empresa demo.
    Cacheado 60 s por usuario web: evita repetir la consulta en cada request.
    """
    cache_key = f'usuario_web:{request.user.pk}'
    usuario = cache.get(cache_key)
    if usuario is not None:
        return usuario

    email = (getattr(request.user, 'email', '') or request.user.get_username() or '').strip()
    usuario = None
    if email:
        usuario = (
            Usuario.objects
            .filter(correo__iexact=email, activo=True)
            .select_related('empresa')
            .first()
        )
    if usuario is None:
        empresa = _get_empresa_demo()
        usuario, _ = Usuario.objects.get_or_create(
            id_usuario='00000000-0000-0000-0000-000000000002',
            defaults={
                'empresa': empresa,
                'nombre': 'Admin Web',
                'correo': 'admin@nexamarket.com',
                'tipo_usuario': 'administrador',
                'activo': True,
            }
        )
    _ = usuario.empresa  # precargar la relación antes de cachear
    cache.set(cache_key, usuario, 60)
    return usuario


def _get_empresa(request):
    """Empresa del usuario logueado — cada usuario solo ve datos de su empresa."""
    usuario = _get_usuario(request)
    return usuario.empresa if usuario.empresa_id else _get_empresa_demo()


# ── AUTH ──────────────────────────────────────────────────────────────────────

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


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

def _datos_dashboard(empresa):
    from django.db.models import Sum, Count, Q, Value, IntegerField
    from django.db.models.functions import Coalesce, ExtractHour

    hoy = timezone.localdate()

    facturas = Factura.objects.filter(empresa=empresa)
    ventas_hoy = facturas.filter(tipo='VENTA', fecha__date=hoy).aggregate(t=Sum('total'))['t'] or 0
    ventas_ayer = facturas.filter(tipo='VENTA', fecha__date=hoy - timedelta(days=1)).aggregate(t=Sum('total'))['t'] or 0
    variacion = round((ventas_hoy - ventas_ayer) / ventas_ayer * 100) if ventas_ayer else None
    facturas_hoy = facturas.filter(fecha__date=hoy).count()

    total_ventas = facturas.filter(tipo='VENTA').aggregate(t=Sum('total'))['t'] or 0
    total_compras = facturas.filter(tipo='COMPRA').aggregate(t=Sum('total'))['t'] or 0

    # Stock actual por artículo (entradas - salidas del libro de movimientos)
    articulos = (
        Articulo.objects
        .filter(empresa=empresa, activo=True)
        .annotate(
            entradas=Coalesce(
                Sum('movimientos__unidades', filter=Q(movimientos__tipo='ENTRADA')),
                Value(0), output_field=IntegerField()
            ),
            salidas=Coalesce(
                Sum('movimientos__unidades', filter=Q(movimientos__tipo='SALIDA')),
                Value(0), output_field=IntegerField()
            ),
        )
    )
    stock_total = 0
    stock_bajo = []
    for art in articulos:
        art.stock_actual = art.entradas - art.salidas
        stock_total += max(art.stock_actual, 0)
        umbral = art.stock_minimo if art.stock_minimo is not None else 5
        if art.stock_actual < umbral:
            stock_bajo.append(art)
    stock_bajo.sort(key=lambda a: a.stock_actual)
    stock_bajo_count = len(stock_bajo)
    stock_bajo = stock_bajo[:5]

    # Ventas por hora del día (conteo de ventas por hora, todo el historial):
    # muestra las horas más activas del negocio como un gráfico lineal.
    conteo_hora = {
        r['h']: r['c']
        for r in (
            facturas.filter(tipo='VENTA')
            .annotate(h=ExtractHour('fecha'))
            .values('h')
            .annotate(c=Count('id_nfactura'), t=Sum('total'))
        )
    }
    total_hora = {
        r['h']: r['t'] or 0
        for r in (
            facturas.filter(tipo='VENTA')
            .annotate(h=ExtractHour('fecha'))
            .values('h')
            .annotate(t=Sum('total'))
        )
    }
    max_conteo = max(conteo_hora.values(), default=0)
    ventas_por_hora = []
    for i, h in enumerate(range(24)):
        c = conteo_hora.get(h, 0)
        pct = round(c / max_conteo * 100) if max_conteo else 0
        ventas_por_hora.append({
            'hora': h,
            'label': f'{h:02d}h',
            'count': c,
            'total': total_hora.get(h, 0),
            'pct': pct,
            'x': round(i / 23 * 100, 2),          # posición X en el SVG (0–100)
            'y': round(100 - pct, 2),             # posición Y (invertida: más alto = más ventas)
            'mostrar_label': h % 3 == 0,          # etiquetar cada 3 horas
        })
    # Cadenas de puntos para el SVG (línea + área rellena)
    linea_puntos = ' '.join(f"{p['x']},{p['y']}" for p in ventas_por_hora)
    area_puntos = f"0,100 {linea_puntos} 100,100"
    hay_ventas_hora = max_conteo > 0

    # Top 5 productos más vendidos (unidades salidas, sin contar mermas)
    salidas_reales = (
        Stock.objects.filter(empresa=empresa, tipo='SALIDA').exclude(factura__tipo='MERMA')
    )
    productos_top = list(
        salidas_reales
        .values('articulo__nombre_articulo')
        .annotate(unidades=Sum('unidades'), total=Sum('total'))
        .order_by('-unidades')[:5]
    )
    max_prod = productos_top[0]['unidades'] if productos_top else 0
    for p in productos_top:
        p['pct'] = round((p['unidades'] or 0) / max_prod * 100) if max_prod else 0

    # Top 5 categorías más vendidas
    categorias_top = list(
        salidas_reales
        .values('articulo__categoria__categoria')
        .annotate(unidades=Sum('unidades'), total=Sum('total'))
        .order_by('-unidades')[:5]
    )
    max_cat = categorias_top[0]['unidades'] if categorias_top else 0
    for c in categorias_top:
        c['nombre'] = c['articulo__categoria__categoria'] or 'Sin categoría'
        c['pct'] = round((c['unidades'] or 0) / max_cat * 100) if max_cat else 0

    return {
        'ventas_hoy': ventas_hoy,
        'variacion': variacion,
        'stock_total': stock_total,
        'facturas_hoy': facturas_hoy,
        'stock_bajo': stock_bajo,
        'stock_bajo_count': stock_bajo_count,
        'ventas_por_hora': ventas_por_hora,
        'linea_puntos': linea_puntos,
        'area_puntos': area_puntos,
        'hay_ventas_hora': hay_ventas_hora,
        'productos_top': productos_top,
        'categorias_top': categorias_top,
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'balance': total_ventas - total_compras,
        'ultimas_facturas': list(facturas.select_related('usuario').order_by('-fecha')[:4]),
    }


@login_required
def dashboard(request):
    empresa = _get_empresa(request)
    datos = cachear(empresa.pk, 'dashboard', lambda: _datos_dashboard(empresa))
    return render(request, 'pages/dashboard/dashboard.html', {'page': 'dashboard', **datos})


def _aplicar_precios_mayor(articulo):
    """Redondea los precios mayoristas y recalcula su margen (igual que el normal)."""
    pcm = _round10(articulo.precio_compra_mayor) if articulo.precio_compra_mayor else None
    pvm = _round10(articulo.precio_venta_mayor) if articulo.precio_venta_mayor else None
    articulo.precio_compra_mayor = pcm
    articulo.precio_venta_mayor = pvm
    if pcm and pvm:
        articulo.margen_ganancia_mayor = round((pvm - pcm) / pcm * 100, 2)


# ── PRODUCTOS ─────────────────────────────────────────────────────────────────

@login_required
def productos(request):
    empresa = _get_empresa(request)
    filtro = request.GET.get('proveedor', '')

    def _cargar():
        qs = (
            Articulo.objects
            .filter(empresa=empresa, activo=True)
            .select_related('categoria', 'proveedor')
            .order_by('nombre_articulo')
        )
        prov_filter, prov_nombre = filtro, ''
        if prov_filter:
            qs = qs.filter(proveedor__id_proveedor=prov_filter)
            try:
                prov_nombre = Proveedor.objects.get(id_proveedor=prov_filter).nombre
            except Proveedor.DoesNotExist:
                prov_filter = ''
        return list(qs), prov_filter, prov_nombre

    articulos, prov_filter, prov_nombre = cachear(empresa.pk, f'productos:{filtro}', _cargar)
    return render(request, 'pages/productos/productos.html', {
        'page': 'productos',
        'articulos': articulos,
        'prov_filter': prov_filter,
        'prov_nombre': prov_nombre,
    })


@login_required
def producto_crear(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = ArticuloForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            articulo = form.save(commit=False)
            articulo.id_articulo = str(uuid.uuid4())
            articulo.empresa = empresa
            pc = _round10(articulo.precio_compra or 0)
            pv = _round10(articulo.precio_venta or 0)
            articulo.precio_compra = pc
            articulo.precio_venta = pv
            articulo.margen_ganancia = round(((pv - pc) / pc * 100) if pc > 0 else 0, 2)
            _aplicar_precios_mayor(articulo)
            articulo.save()
            messages.success(request, f'Producto "{articulo.nombre_articulo}" creado correctamente.')
            return redirect('productos')
    else:
        form = ArticuloForm(empresa=empresa)
    return render(request, 'pages/productos/producto_form.html', {'form': form, 'page': 'productos', 'accion': 'Crear producto'})


@login_required
def producto_editar(request, pk):
    empresa = _get_empresa(request)
    articulo = get_object_or_404(Articulo, id_articulo=pk, empresa=empresa)
    if request.method == 'POST':
        form = ArticuloForm(request.POST, request.FILES, instance=articulo, empresa=empresa)
        if form.is_valid():
            obj = form.save(commit=False)
            pc = _round10(obj.precio_compra or 0)
            pv = _round10(obj.precio_venta or 0)
            obj.precio_compra = pc
            obj.precio_venta = pv
            obj.margen_ganancia = round(((pv - pc) / pc * 100) if pc > 0 else 0, 2)
            _aplicar_precios_mayor(obj)
            obj.save()
            messages.success(request, f'Producto "{obj.nombre_articulo}" actualizado.')
            return redirect('productos')
    else:
        form = ArticuloForm(instance=articulo, empresa=empresa)
    return render(request, 'pages/productos/producto_form.html', {'form': form, 'page': 'productos', 'accion': 'Editar producto', 'articulo': articulo})


@login_required
def producto_eliminar(request, pk):
    empresa = _get_empresa(request)
    articulo = get_object_or_404(Articulo, id_articulo=pk, empresa=empresa)
    if request.method == 'POST':
        articulo.activo = False
        articulo.save()
        messages.success(request, f'Producto "{articulo.nombre_articulo}" desactivado.')
        return redirect('productos')
    return render(request, 'pages/productos/producto_confirm_delete.html', {'articulo': articulo, 'page': 'productos'})


# ── CATEGORÍAS ────────────────────────────────────────────────────────────────

@login_required
def categorias(request):
    empresa = _get_empresa(request)
    cats = Categoria.objects.filter(empresa=empresa).order_by('categoria')
    return render(request, 'pages/categorias/categorias.html', {'page': 'categorias', 'categorias': cats})


@login_required
def categoria_crear(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.id_categoria = str(uuid.uuid4())
            cat.empresa = empresa
            cat.save()
            messages.success(request, f'Categoría "{cat.categoria}" creada.')
            return redirect('categorias')
    else:
        form = CategoriaForm()
    return render(request, 'pages/categorias/categoria_form.html', {'form': form, 'page': 'categorias', 'accion': 'Nueva categoría'})


@login_required
def categoria_editar(request, pk):
    empresa = _get_empresa(request)
    cat = get_object_or_404(Categoria, id_categoria=pk, empresa=empresa)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, f'Categoría "{cat.categoria}" actualizada.')
            return redirect('categorias')
    else:
        form = CategoriaForm(instance=cat)
    return render(request, 'pages/categorias/categoria_form.html', {'form': form, 'page': 'categorias', 'accion': 'Editar categoría', 'objeto': cat})


@login_required
def categoria_eliminar(request, pk):
    empresa = _get_empresa(request)
    cat = get_object_or_404(Categoria, id_categoria=pk, empresa=empresa)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'Categoría eliminada.')
        return redirect('categorias')
    return render(request, 'pages/shared/confirm_delete.html', {
        'objeto': cat, 'nombre': cat.categoria, 'tipo': 'Categoría',
        'cancelar_url': 'categorias', 'page': 'categorias',
    })


# ── PROVEEDORES ───────────────────────────────────────────────────────────────

@login_required
def proveedores(request):
    empresa = _get_empresa(request)
    provs = Proveedor.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    return render(request, 'pages/proveedores/proveedores.html', {'page': 'proveedores', 'proveedores': provs})


@login_required
def proveedor_crear(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            prov = form.save(commit=False)
            prov.id_proveedor = str(uuid.uuid4())
            prov.empresa = empresa
            prov.save()
            messages.success(request, f'Proveedor "{prov.nombre}" creado.')
            return redirect('proveedores')
    else:
        form = ProveedorForm()
    return render(request, 'pages/proveedores/proveedor_form.html', {'form': form, 'page': 'proveedores', 'accion': 'Nuevo proveedor'})


@login_required
def proveedor_editar(request, pk):
    empresa = _get_empresa(request)
    prov = get_object_or_404(Proveedor, id_proveedor=pk, empresa=empresa)
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=prov)
        if form.is_valid():
            form.save()
            messages.success(request, f'Proveedor "{prov.nombre}" actualizado.')
            return redirect('proveedores')
    else:
        form = ProveedorForm(instance=prov)
    return render(request, 'pages/proveedores/proveedor_form.html', {'form': form, 'page': 'proveedores', 'accion': 'Editar proveedor', 'objeto': prov})


@login_required
def proveedor_eliminar(request, pk):
    empresa = _get_empresa(request)
    prov = get_object_or_404(Proveedor, id_proveedor=pk, empresa=empresa)
    if request.method == 'POST':
        prov.activo = False
        prov.save()
        messages.success(request, f'Proveedor "{prov.nombre}" desactivado.')
        return redirect('proveedores')
    return render(request, 'pages/shared/confirm_delete.html', {
        'objeto': prov, 'nombre': prov.nombre, 'tipo': 'Proveedor',
        'cancelar_url': 'proveedores', 'page': 'proveedores',
    })


# ── USUARIOS ──────────────────────────────────────────────────────────────────

@login_required
def usuarios(request):
    empresa = _get_empresa(request)
    lista = list(Usuario.objects.filter(empresa=empresa).order_by('-activo', 'nombre'))
    # Nombres de las categorías asignadas a cada usuario (id_categorias es JSON de PKs)
    cat_map = {c.id_categoria: c.categoria for c in Categoria.objects.filter(empresa=empresa)}
    for u in lista:
        ids = u.id_categorias or []
        u.categorias_nombres = [cat_map[i] for i in ids if i in cat_map]
    return render(request, 'pages/usuarios/usuarios.html', {
        'page': 'usuarios',
        'usuarios': lista,
    })


def _guardar_usuario(usuario, empresa, form):
    """Completa empresa + id_categorias (desde el multiselect) y guarda."""
    usuario.empresa = empresa
    usuario.id_categorias = [str(c.id_categoria) for c in form.cleaned_data['categorias']]
    usuario.save()


@login_required
def usuario_crear(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, empresa=empresa)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.id_usuario = str(uuid.uuid4())
            _guardar_usuario(usuario, empresa, form)
            messages.success(request, f'Usuario "{usuario.nombre}" creado.')
            return redirect('usuarios')
    else:
        form = UsuarioForm(empresa=empresa)
    return render(request, 'pages/usuarios/usuario_form.html', {
        'form': form, 'page': 'usuarios', 'accion': 'Nuevo usuario',
    })


@login_required
def usuario_editar(request, pk):
    empresa = _get_empresa(request)
    usuario = get_object_or_404(Usuario, id_usuario=pk, empresa=empresa)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario, empresa=empresa)
        if form.is_valid():
            obj = form.save(commit=False)
            _guardar_usuario(obj, empresa, form)
            cache.delete(f'usuario_web:{request.user.pk}')  # por si editó su propio acceso
            messages.success(request, f'Usuario "{obj.nombre}" actualizado.')
            return redirect('usuarios')
    else:
        form = UsuarioForm(instance=usuario, empresa=empresa)
    return render(request, 'pages/usuarios/usuario_form.html', {
        'form': form, 'page': 'usuarios', 'accion': 'Editar usuario', 'objeto': usuario,
    })


@login_required
def usuario_eliminar(request, pk):
    empresa = _get_empresa(request)
    usuario = get_object_or_404(Usuario, id_usuario=pk, empresa=empresa)
    if request.method == 'POST':
        # Baja lógica: eliminar en duro arrastraría sus facturas y movimientos (CASCADE)
        usuario.activo = False
        usuario.save()
        cache.delete(f'usuario_web:{request.user.pk}')
        messages.success(request, f'Usuario "{usuario.nombre}" desactivado.')
        return redirect('usuarios')
    return render(request, 'pages/shared/confirm_delete.html', {
        'objeto': usuario, 'nombre': usuario.nombre, 'tipo': 'Usuario',
        'cancelar_url': 'usuarios', 'page': 'usuarios', 'desactivar': True,
    })


# ── EMPRESA ───────────────────────────────────────────────────────────────────

@login_required
def empresa(request):
    emp = _get_empresa(request)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            cache.delete(f'usuario_web:{request.user.pk}')  # refrescar nombre en el sidebar
            messages.success(request, 'Datos de la empresa actualizados.')
            return redirect('empresa')
    else:
        form = EmpresaForm(instance=emp)
    return render(request, 'pages/empresa/empresa.html', {'form': form, 'page': 'empresa', 'empresa': emp})


# ── PERSONALIZACIÓN ───────────────────────────────────────────────────────────

@login_required
def personalizacion(request):
    empresa = _get_empresa(request)
    config, _ = ConfiguracionWeb.objects.get_or_create(empresa=empresa)
    if request.method == 'POST':
        if 'restaurar' in request.POST:
            config.delete()
            ConfiguracionWeb.objects.create(empresa=empresa)
            messages.success(request, 'Colores restaurados a los valores por defecto.')
            return redirect('personalizacion')
        form = ConfiguracionWebForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Personalización guardada.')
            return redirect('personalizacion')
    else:
        form = ConfiguracionWebForm(instance=config)
    return render(request, 'pages/personalizacion/personalizacion.html', {
        'form': form, 'page': 'personalizacion',
    })


# ── PUNTO DE COMPRA ───────────────────────────────────────────────────────────

@login_required
def punto_compra(request):
    empresa = _get_empresa(request)

    if request.method == 'POST':
        cart_json = request.POST.get('cart_data', '[]')
        try:
            cart = json.loads(cart_json)
        except json.JSONDecodeError:
            cart = []

        if not cart:
            messages.error(request, 'El carrito está vacío.')
            return redirect('punto_compra')

        usuario = _get_usuario(request)
        total_compra = sum(float(i['precio']) * int(i['cantidad']) for i in cart)

        conteo = Factura.objects.filter(empresa=empresa, tipo='COMPRA').count()
        numero = f'CMP-{conteo + 1:04d}'

        factura = Factura.objects.create(
            id_nfactura=str(uuid.uuid4()),
            empresa=empresa,
            usuario=usuario,
            numero_factura=numero,
            fecha=timezone.now(),
            total=total_compra,
            tipo='COMPRA',
        )

        for item in cart:
            articulo = get_object_or_404(Articulo, id_articulo=item['id'], empresa=empresa)
            cantidad = int(item['cantidad'])
            precio_u = float(item['precio'])
            precio_venta = float(item.get('precio_venta') or articulo.precio_venta)

            # Fecha de vencimiento opcional
            fecha_venc = None
            fv_str = item.get('fecha_vencimiento')
            if fv_str:
                d = parse_date(fv_str)
                if d:
                    fecha_venc = timezone.make_aware(
                        timezone.datetime.combine(d, timezone.datetime.min.time())
                    )

            Stock.objects.create(
                id_stock=str(uuid.uuid4()),
                articulo=articulo,
                empresa=empresa,
                usuario=usuario,
                tipo='ENTRADA',
                unidades=cantidad,
                precio_unitario_compra=precio_u,
                precio_unitario_venta=precio_venta,
                total=precio_u * cantidad,
                factura=factura,
                fecha_hora=timezone.now(),
                fecha_vencimiento=fecha_venc,
            )

        messages.success(request, f'Compra {numero} registrada — Total: ${total_compra:,.0f}')
        return redirect('compras_ventas')

    def _cargar():
        articulos = list(
            Articulo.objects
            .filter(empresa=empresa, activo=True)
            .select_related('categoria', 'proveedor')
            .order_by('nombre_articulo')
        )
        # Solo proveedores que tengan artículos activos en esta empresa
        proveedores_activos = list(
            Proveedor.objects
            .filter(empresa=empresa, activo=True, articulo__empresa=empresa, articulo__activo=True)
            .distinct()
            .order_by('nombre')
        )
        return articulos, proveedores_activos

    articulos, proveedores_activos = cachear(empresa.pk, 'pos_compra', _cargar)
    return render(request, 'pages/punto_compra/punto_compra.html', {
        'page': 'punto_compra',
        'articulos': articulos,
        'proveedores_activos': proveedores_activos,
    })


# ── API INTERNA ───────────────────────────────────────────────────────────────

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


# ── OTRAS VISTAS ──────────────────────────────────────────────────────────────

@login_required
def inventario(request):
    from django.db.models import Sum, Q, Value, IntegerField
    from django.db.models.functions import Coalesce

    empresa = _get_empresa(request)

    def _cargar():
        articulos = list(
            Articulo.objects
            .filter(empresa=empresa, activo=True)
            .select_related('categoria', 'proveedor')
            .annotate(
                entradas=Coalesce(
                    Sum('movimientos__unidades', filter=Q(movimientos__tipo='ENTRADA')),
                    Value(0), output_field=IntegerField()
                ),
                salidas=Coalesce(
                    Sum('movimientos__unidades', filter=Q(movimientos__tipo='SALIDA')),
                    Value(0), output_field=IntegerField()
                ),
            )
            .order_by('nombre_articulo')
        )
        for art in articulos:
            art.stock_actual = art.entradas - art.salidas
        return articulos

    return render(request, 'pages/inventario/inventario.html', {
        'page': 'inventario',
        'articulos': cachear(empresa.pk, 'inventario', _cargar),
    })


@login_required
def punto_venta(request):
    from django.db.models import Sum, Q, Value, IntegerField
    from django.db.models.functions import Coalesce

    empresa = _get_empresa(request)

    if request.method == 'POST':
        try:
            cart = json.loads(request.POST.get('cart_data', '[]'))
        except json.JSONDecodeError:
            cart = []

        # Precio autoritativo desde la BD: aplica el mayorista si corresponde
        lineas = []
        for item in cart:
            articulo = get_object_or_404(Articulo, id_articulo=item['id'], empresa=empresa)
            cantidad = int(item['cantidad'])
            if cantidad <= 0:
                continue
            precio_u = float(articulo.precio_venta or 0)
            if (articulo.es_mayorista and articulo.precio_venta_mayor
                    and articulo.cantidad_minima_mayor
                    and cantidad >= articulo.cantidad_minima_mayor):
                precio_u = float(articulo.precio_venta_mayor)
            lineas.append((articulo, cantidad, precio_u))

        if not lineas:
            messages.error(request, 'El carrito está vacío.')
            return redirect('punto_venta')

        usuario = _get_usuario(request)
        total_venta = sum(cantidad * precio for _, cantidad, precio in lineas)
        conteo = Factura.objects.filter(empresa=empresa, tipo='VENTA').count()
        numero = f'VTA-{conteo + 1:04d}'

        factura = Factura.objects.create(
            id_nfactura=str(uuid.uuid4()),
            empresa=empresa,
            usuario=usuario,
            numero_factura=numero,
            fecha=timezone.now(),
            total=total_venta,
            tipo='VENTA',
        )
        for articulo, cantidad, precio_u in lineas:
            Stock.objects.create(
                id_stock=str(uuid.uuid4()),
                articulo=articulo,
                empresa=empresa,
                usuario=usuario,
                tipo='SALIDA',
                unidades=cantidad,
                precio_unitario_compra=float(articulo.precio_compra or 0),
                precio_unitario_venta=precio_u,
                total=precio_u * cantidad,
                factura=factura,
                fecha_hora=timezone.now(),
            )

        messages.success(request, f'Venta {numero} registrada — Total: ${total_venta:,.0f}')
        return redirect('compras_ventas')

    def _cargar():
        articulos = list(
            Articulo.objects
            .filter(empresa=empresa, activo=True)
            .select_related('categoria')
            .annotate(
                entradas=Coalesce(
                    Sum('movimientos__unidades', filter=Q(movimientos__tipo='ENTRADA')),
                    Value(0), output_field=IntegerField()
                ),
                salidas=Coalesce(
                    Sum('movimientos__unidades', filter=Q(movimientos__tipo='SALIDA')),
                    Value(0), output_field=IntegerField()
                ),
            )
            .order_by('nombre_articulo')
        )
        for art in articulos:
            art.stock_actual = art.entradas - art.salidas
        categorias = list(
            Categoria.objects
            .filter(empresa=empresa, estado=True, articulos__empresa=empresa, articulos__activo=True)
            .distinct()
            .order_by('categoria')
        )
        return articulos, categorias

    articulos, categorias = cachear(empresa.pk, 'pos_venta', _cargar)
    return render(request, 'pages/punto_venta/punto_venta.html', {
        'page': 'punto_venta',
        'articulos': articulos,
        'categorias': categorias,
    })


# ── MERMA ─────────────────────────────────────────────────────────────────────

@login_required
def merma(request):
    """
    Registro de merma (pérdida/deterioro) desde la web.
    Genera una Factura tipo MERMA (MRM-XXXX) con precio de venta 0 y el
    precio de compra que corresponda; cada línea es una SALIDA de stock.
    El total de la factura es el costo perdido (para cuantificar la pérdida).
    """
    from django.db.models import Sum, Q, Value, IntegerField
    from django.db.models.functions import Coalesce

    empresa = _get_empresa(request)

    if request.method == 'POST':
        try:
            cart = json.loads(request.POST.get('cart_data', '[]'))
        except json.JSONDecodeError:
            cart = []

        lineas = []
        for item in cart:
            articulo = get_object_or_404(Articulo, id_articulo=item['id'], empresa=empresa)
            cantidad = int(item['cantidad'])
            if cantidad <= 0:
                continue
            costo_u = float(articulo.precio_compra or 0)
            lineas.append((articulo, cantidad, costo_u))

        if not lineas:
            messages.error(request, 'No seleccionaste productos para la merma.')
            return redirect('merma')

        usuario = _get_usuario(request)
        total_merma = sum(cantidad * costo for _, cantidad, costo in lineas)
        conteo = Factura.objects.filter(empresa=empresa, tipo='MERMA').count()
        numero = f'MRM-{conteo + 1:04d}'

        factura = Factura.objects.create(
            id_nfactura=str(uuid.uuid4()),
            empresa=empresa,
            usuario=usuario,
            numero_factura=numero,
            fecha=timezone.now(),
            total=total_merma,
            tipo='MERMA',
        )
        for articulo, cantidad, costo_u in lineas:
            Stock.objects.create(
                id_stock=str(uuid.uuid4()),
                articulo=articulo,
                empresa=empresa,
                usuario=usuario,
                tipo='SALIDA',
                unidades=cantidad,
                precio_unitario_compra=costo_u,
                precio_unitario_venta=0,   # merma: no hay venta
                total=costo_u * cantidad,  # costo perdido
                factura=factura,
                fecha_hora=timezone.now(),
            )

        messages.success(request, f'Merma {numero} registrada — Costo perdido: ${total_merma:,.0f}')
        return redirect('compras_ventas')

    def _cargar():
        articulos = list(
            Articulo.objects
            .filter(empresa=empresa, activo=True)
            .select_related('categoria')
            .annotate(
                entradas=Coalesce(
                    Sum('movimientos__unidades', filter=Q(movimientos__tipo='ENTRADA')),
                    Value(0), output_field=IntegerField()
                ),
                salidas=Coalesce(
                    Sum('movimientos__unidades', filter=Q(movimientos__tipo='SALIDA')),
                    Value(0), output_field=IntegerField()
                ),
            )
            .order_by('nombre_articulo')
        )
        for art in articulos:
            art.stock_actual = art.entradas - art.salidas
        categorias = list(
            Categoria.objects
            .filter(empresa=empresa, estado=True, articulos__empresa=empresa, articulos__activo=True)
            .distinct()
            .order_by('categoria')
        )
        return articulos, categorias

    articulos, categorias = cachear(empresa.pk, 'merma_pos', _cargar)
    return render(request, 'pages/merma/merma.html', {
        'page': 'merma',
        'articulos': articulos,
        'categorias': categorias,
    })


MESES = [
    (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
    (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
    (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
]
MESES_DICT = dict(MESES)


def _agrupar_facturas(facturas):
    """
    Agrupa facturas (ya ordenadas por -fecha) en años → meses con conteos y
    totales, para la vista de desglose tipo AppSheet. Reciente primero.
    """
    from collections import OrderedDict
    anios = OrderedDict()
    for f in facturas:
        y, m = f.fecha.year, f.fecha.month
        a = anios.get(y)
        if a is None:
            a = {'anio': y, 'count': 0, 'ventas': 0, 'compras': 0, 'mermas': 0, 'meses': OrderedDict()}
            anios[y] = a
        mm = a['meses'].get(m)
        if mm is None:
            mm = {'num': m, 'nombre': MESES_DICT[m], 'label': f'{m}.-{MESES_DICT[m]}',
                  'count': 0, 'ventas': 0, 'compras': 0, 'mermas': 0, 'facturas': []}
            a['meses'][m] = mm
        a['count'] += 1
        mm['count'] += 1
        mm['facturas'].append(f)
        if f.tipo == 'VENTA':
            a['ventas'] += f.total; mm['ventas'] += f.total
        elif f.tipo == 'COMPRA':
            a['compras'] += f.total; mm['compras'] += f.total
        else:
            a['mermas'] += f.total; mm['mermas'] += f.total
    result = []
    for a in anios.values():
        a['meses'] = list(a['meses'].values())
        result.append(a)
    return result


def _agrupar_movimientos(movs):
    """Agrupa movimientos de stock en años → meses con conteos y total de ventas."""
    from collections import OrderedDict
    anios = OrderedDict()
    for mv in movs:
        y, m = mv.fecha_hora.year, mv.fecha_hora.month
        es_merma = bool(mv.factura_id and mv.factura and mv.factura.tipo == 'MERMA')
        clase = 'entradas' if mv.tipo == 'ENTRADA' else ('mermas' if es_merma else 'salidas')
        a = anios.get(y)
        if a is None:
            a = {'anio': y, 'count': 0, 'entradas': 0, 'salidas': 0, 'mermas': 0,
                 'total_ventas': 0, 'meses': OrderedDict()}
            anios[y] = a
        mm = a['meses'].get(m)
        if mm is None:
            mm = {'num': m, 'nombre': MESES_DICT[m], 'label': f'{m}.-{MESES_DICT[m]}',
                  'count': 0, 'entradas': 0, 'salidas': 0, 'mermas': 0,
                  'total_ventas': 0, 'movimientos': []}
            a['meses'][m] = mm
        a['count'] += 1; a[clase] += 1
        mm['count'] += 1; mm[clase] += 1
        mm['movimientos'].append(mv)
        if clase == 'salidas':
            a['total_ventas'] += mv.total; mm['total_ventas'] += mv.total
    result = []
    for a in anios.values():
        a['meses'] = list(a['meses'].values())
        result.append(a)
    return result


@login_required
def compras_ventas(request):
    empresa = _get_empresa(request)
    base = Factura.objects.filter(empresa=empresa)

    # Años con facturas (para el selector, antes de filtrar)
    anios = [d.year for d in base.dates('fecha', 'year')]

    # Filtros: tipo + mes + año + rango desde/hasta (combinables, todos server-side)
    tipo  = request.GET.get('tipo', '')
    mes   = request.GET.get('mes', '')
    anio  = request.GET.get('anio', '')
    desde = parse_date(request.GET.get('desde') or '')
    hasta = parse_date(request.GET.get('hasta') or '')

    facturas = base.select_related('usuario').prefetch_related('lineas__articulo').order_by('-fecha')
    if tipo in ('VENTA', 'COMPRA', 'MERMA'):
        facturas = facturas.filter(tipo=tipo)
    if anio.isdigit():
        facturas = facturas.filter(fecha__year=int(anio))
    if mes.isdigit() and 1 <= int(mes) <= 12:
        facturas = facturas.filter(fecha__month=int(mes))
    if desde:
        facturas = facturas.filter(fecha__date__gte=desde)
    if hasta:
        facturas = facturas.filter(fecha__date__lte=hasta)

    facturas = list(facturas)
    total_ventas  = sum(f.total for f in facturas if f.tipo == 'VENTA')
    total_compras = sum(f.total for f in facturas if f.tipo == 'COMPRA')
    total_mermas  = sum(f.total for f in facturas if f.tipo == 'MERMA')

    return render(request, 'pages/compras_ventas/compras_ventas.html', {
        'page': 'compras_ventas',
        'grupos': _agrupar_facturas(facturas),
        'total_facturas': len(facturas),
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'total_mermas': total_mermas,
        'balance': total_ventas - total_compras,
        'anios': anios,
        'meses': MESES,
        'filtro_tipo': tipo,
        'filtro_mes': mes,
        'filtro_anio': anio,
        'filtro_desde': request.GET.get('desde', ''),
        'filtro_hasta': request.GET.get('hasta', ''),
        'filtrando': bool(tipo or mes or anio or desde or hasta),
    })


@login_required
def movimientos(request):
    empresa = _get_empresa(request)
    tipo_filtro = request.GET.get('tipo', '')
    qs = (
        Stock.objects
        .filter(empresa=empresa)
        .select_related('articulo', 'articulo__categoria', 'factura', 'usuario')
        .order_by('-fecha_hora')
    )
    if tipo_filtro == 'ENTRADA':
        qs = qs.filter(tipo='ENTRADA')
    elif tipo_filtro == 'SALIDA':
        # Ventas reales: salidas que no provienen de una merma
        qs = qs.filter(tipo='SALIDA').exclude(factura__tipo='MERMA')
    elif tipo_filtro == 'MERMA':
        qs = qs.filter(factura__tipo='MERMA')

    movs = list(qs)
    return render(request, 'pages/movimientos/movimientos.html', {
        'page': 'movimientos',
        'grupos': _agrupar_movimientos(movs),
        'total_movimientos': len(movs),
        'tipo_filtro': tipo_filtro,
    })
