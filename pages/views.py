import uuid
import json
import math
from urllib.parse import quote

import requests
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from base_datos.models import Empresa, Articulo, Categoria, Proveedor, Usuario, Factura, Stock
from .forms import ArticuloForm, CategoriaForm, ProveedorForm, EmpresaForm


def _round10(val):
    """Redondea al múltiplo de 10 más cercano (≤4 baja, ≥5 sube)."""
    val = float(val)
    return int(math.floor(val / 10 + 0.5)) * 10


def _get_empresa():
    empresa, _ = Empresa.objects.get_or_create(
        id_empresa='00000000-0000-0000-0000-000000000001',
        defaults={'nombre': 'Mi Negocio', 'rut': '00.000.000-0', 'activo': True}
    )
    return empresa


def _get_usuario():
    empresa = _get_empresa()
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
    return usuario


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


# ── AUTH CON GOOGLE (Supabase Auth) ──────────────────────────────────────────

def google_login(request):
    """Redirige al flujo OAuth de Google gestionado por Supabase Auth."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        messages.error(request, 'El login con Google no está configurado (faltan SUPABASE_URL / SUPABASE_ANON_KEY en .env).')
        return redirect('login')
    callback = request.build_absolute_uri('/auth/callback/')
    return redirect(
        f"{settings.SUPABASE_URL}/auth/v1/authorize"
        f"?provider=google&redirect_to={quote(callback, safe='')}"
    )


def google_callback(request):
    """
    Supabase redirige aquí con los tokens en el fragmento de la URL
    (#access_token=...). El fragmento no llega al servidor, así que esta
    página lo lee con JS y lo envía a supabase_session para abrir la sesión.
    """
    return render(request, 'pages/auth/google_callback.html')


def supabase_session(request):
    """Valida el access_token contra Supabase y abre la sesión Django."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    try:
        token = json.loads(request.body).get('access_token', '')
    except json.JSONDecodeError:
        token = ''
    if not token:
        return JsonResponse({'ok': False, 'error': 'Falta el access_token.'}, status=400)

    try:
        resp = requests.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={
                'apikey': settings.SUPABASE_ANON_KEY,
                'Authorization': f'Bearer {token}',
            },
            timeout=10,
        )
    except requests.RequestException:
        return JsonResponse({'ok': False, 'error': 'No se pudo contactar a Supabase.'}, status=502)

    if resp.status_code != 200:
        return JsonResponse({'ok': False, 'error': 'Token inválido o expirado.'}, status=401)

    info = resp.json()
    email = info.get('email')
    if not email:
        return JsonResponse({'ok': False, 'error': 'La cuenta de Google no entregó un email.'}, status=400)

    meta = info.get('user_metadata') or {}
    user, created = User.objects.get_or_create(
        username=email,
        defaults={'email': email, 'first_name': (meta.get('full_name') or '')[:150]},
    )
    if created:
        user.set_unusable_password()
        user.save()

    login(request, user)
    return JsonResponse({'ok': True, 'next': settings.LOGIN_REDIRECT_URL})


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    return render(request, 'pages/dashboard/dashboard.html', {'page': 'dashboard'})


# ── PRODUCTOS ─────────────────────────────────────────────────────────────────

@login_required
def productos(request):
    empresa = _get_empresa()
    qs = (
        Articulo.objects
        .filter(empresa=empresa, activo=True)
        .select_related('categoria', 'proveedor')
        .order_by('nombre_articulo')
    )
    prov_filter = request.GET.get('proveedor', '')
    prov_nombre = ''
    if prov_filter:
        qs = qs.filter(proveedor__id_proveedor=prov_filter)
        try:
            prov_nombre = Proveedor.objects.get(id_proveedor=prov_filter).nombre
        except Proveedor.DoesNotExist:
            prov_filter = ''
    return render(request, 'pages/productos/productos.html', {
        'page': 'productos',
        'articulos': qs,
        'prov_filter': prov_filter,
        'prov_nombre': prov_nombre,
    })


@login_required
def producto_crear(request):
    empresa = _get_empresa()
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
            articulo.save()
            messages.success(request, f'Producto "{articulo.nombre_articulo}" creado correctamente.')
            return redirect('productos')
    else:
        form = ArticuloForm(empresa=empresa)
    return render(request, 'pages/productos/producto_form.html', {'form': form, 'page': 'productos', 'accion': 'Crear producto'})


@login_required
def producto_editar(request, pk):
    empresa = _get_empresa()
    articulo = get_object_or_404(Articulo, id_articulo=pk)
    if request.method == 'POST':
        form = ArticuloForm(request.POST, request.FILES, instance=articulo, empresa=empresa)
        if form.is_valid():
            obj = form.save(commit=False)
            pc = _round10(obj.precio_compra or 0)
            pv = _round10(obj.precio_venta or 0)
            obj.precio_compra = pc
            obj.precio_venta = pv
            obj.margen_ganancia = round(((pv - pc) / pc * 100) if pc > 0 else 0, 2)
            obj.save()
            messages.success(request, f'Producto "{obj.nombre_articulo}" actualizado.')
            return redirect('productos')
    else:
        form = ArticuloForm(instance=articulo, empresa=empresa)
    return render(request, 'pages/productos/producto_form.html', {'form': form, 'page': 'productos', 'accion': 'Editar producto', 'articulo': articulo})


@login_required
def producto_eliminar(request, pk):
    articulo = get_object_or_404(Articulo, id_articulo=pk)
    if request.method == 'POST':
        articulo.activo = False
        articulo.save()
        messages.success(request, f'Producto "{articulo.nombre_articulo}" desactivado.')
        return redirect('productos')
    return render(request, 'pages/productos/producto_confirm_delete.html', {'articulo': articulo, 'page': 'productos'})


# ── CATEGORÍAS ────────────────────────────────────────────────────────────────

@login_required
def categorias(request):
    empresa = _get_empresa()
    cats = Categoria.objects.filter(empresa=empresa).order_by('categoria')
    return render(request, 'pages/categorias/categorias.html', {'page': 'categorias', 'categorias': cats})


@login_required
def categoria_crear(request):
    empresa = _get_empresa()
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
    cat = get_object_or_404(Categoria, id_categoria=pk)
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
    cat = get_object_or_404(Categoria, id_categoria=pk)
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
    empresa = _get_empresa()
    provs = Proveedor.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    return render(request, 'pages/proveedores/proveedores.html', {'page': 'proveedores', 'proveedores': provs})


@login_required
def proveedor_crear(request):
    empresa = _get_empresa()
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
    prov = get_object_or_404(Proveedor, id_proveedor=pk)
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
    prov = get_object_or_404(Proveedor, id_proveedor=pk)
    if request.method == 'POST':
        prov.activo = False
        prov.save()
        messages.success(request, f'Proveedor "{prov.nombre}" desactivado.')
        return redirect('proveedores')
    return render(request, 'pages/shared/confirm_delete.html', {
        'objeto': prov, 'nombre': prov.nombre, 'tipo': 'Proveedor',
        'cancelar_url': 'proveedores', 'page': 'proveedores',
    })


# ── EMPRESA ───────────────────────────────────────────────────────────────────

@login_required
def empresa(request):
    emp = _get_empresa()
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos de la empresa actualizados.')
            return redirect('empresa')
    else:
        form = EmpresaForm(instance=emp)
    return render(request, 'pages/empresa/empresa.html', {'form': form, 'page': 'empresa', 'empresa': emp})


# ── PUNTO DE COMPRA ───────────────────────────────────────────────────────────

@login_required
def punto_compra(request):
    empresa = _get_empresa()

    if request.method == 'POST':
        cart_json = request.POST.get('cart_data', '[]')
        try:
            cart = json.loads(cart_json)
        except json.JSONDecodeError:
            cart = []

        if not cart:
            messages.error(request, 'El carrito está vacío.')
            return redirect('punto_compra')

        usuario = _get_usuario()
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
            articulo = get_object_or_404(Articulo, id_articulo=item['id'])
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

    articulos = (
        Articulo.objects
        .filter(empresa=empresa, activo=True)
        .select_related('categoria', 'proveedor')
        .order_by('nombre_articulo')
    )
    # Solo proveedores que tengan artículos activos en esta empresa
    proveedores_activos = (
        Proveedor.objects
        .filter(empresa=empresa, activo=True, articulo__empresa=empresa, articulo__activo=True)
        .distinct()
        .order_by('nombre')
    )

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
        articulo = get_object_or_404(Articulo, id_articulo=pk)
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

    empresa = _get_empresa()
    articulos = (
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

    return render(request, 'pages/inventario/inventario.html', {
        'page': 'inventario',
        'articulos': articulos,
    })


@login_required
def punto_venta(request):
    return render(request, 'pages/punto_venta/punto_venta.html', {'page': 'punto_venta'})


@login_required
def compras_ventas(request):
    from django.db.models import Sum, Q
    empresa = _get_empresa()
    facturas = (
        Factura.objects
        .filter(empresa=empresa)
        .select_related('usuario')
        .prefetch_related('lineas__articulo')
        .order_by('-fecha')
    )
    total_ventas  = facturas.filter(tipo='VENTA').aggregate(t=Sum('total'))['t'] or 0
    total_compras = facturas.filter(tipo='COMPRA').aggregate(t=Sum('total'))['t'] or 0
    return render(request, 'pages/compras_ventas/compras_ventas.html', {
        'page': 'compras_ventas',
        'facturas': facturas,
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'balance': total_ventas - total_compras,
    })


@login_required
def movimientos(request):
    empresa = _get_empresa()
    tipo_filtro = request.GET.get('tipo', '')
    qs = (
        Stock.objects
        .filter(empresa=empresa)
        .select_related('articulo', 'factura', 'usuario')
        .order_by('-fecha_hora')
    )
    if tipo_filtro in ('ENTRADA', 'SALIDA'):
        qs = qs.filter(tipo=tipo_filtro)

    return render(request, 'pages/movimientos/movimientos.html', {
        'page': 'movimientos',
        'movimientos': qs[:500],
        'tipo_filtro': tipo_filtro,
    })
