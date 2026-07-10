from django import forms
from base_datos.models import Articulo, Proveedor, Categoria, Empresa, ConfiguracionWeb, Usuario


class ConfiguracionWebForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionWeb
        fields = ['color_primario', 'color_acento', 'color_fondo', 'color_sidebar', 'color_texto', 'logo_url']
        widgets = {
            'color_primario': forms.TextInput(attrs={'type': 'color'}),
            'color_acento':   forms.TextInput(attrs={'type': 'color'}),
            'color_fondo':    forms.TextInput(attrs={'type': 'color'}),
            'color_sidebar':  forms.TextInput(attrs={'type': 'color'}),
            'color_texto':    forms.TextInput(attrs={'type': 'color'}),
            'logo_url':       forms.URLInput(attrs={'placeholder': 'https://... (opcional)'}),
        }
        labels = {
            'color_primario': 'Color primario',
            'color_acento':   'Color de acento',
            'color_fondo':    'Color de fondo',
            'color_sidebar':  'Color del menú y tarjetas',
            'color_texto':    'Color del texto',
            'logo_url':       'URL del logo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['logo_url'].required = False


class ArticuloForm(forms.ModelForm):
    # Declarado aparte: BooleanField null=True generaría un select Sí/No/Desconocido
    es_mayorista = forms.BooleanField(required=False, label='Vende al por mayor')

    class Meta:
        model = Articulo
        fields = [
            'nombre_articulo', 'descripcion',
            'categoria', 'proveedor',
            'codigo_qr', 'codigo_barra',
            'precio_compra', 'precio_venta', 'margen_ganancia',
            'unidad_medida', 'foto', 'activo', 'stock_minimo',
            'es_mayorista', 'cantidad_minima_mayor',
            'precio_compra_mayor', 'precio_venta_mayor', 'margen_ganancia_mayor',
        ]
        widgets = {
            'nombre_articulo': forms.TextInput(attrs={'placeholder': 'Nombre del producto'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripción opcional'}),
            'codigo_qr': forms.TextInput(attrs={'placeholder': 'Código QR'}),
            'codigo_barra': forms.TextInput(attrs={'placeholder': 'Código de barras'}),
            'precio_compra': forms.NumberInput(attrs={'placeholder': '0', 'step': '1', 'min': '0'}),
            'precio_venta': forms.NumberInput(attrs={'placeholder': '0', 'step': '1', 'min': '0'}),
            'margen_ganancia': forms.NumberInput(attrs={'placeholder': '0.0', 'step': '0.1', 'min': '-100'}),
            'stock_minimo': forms.NumberInput(attrs={'placeholder': '5', 'step': '1', 'min': '0'}),
            'cantidad_minima_mayor': forms.NumberInput(attrs={'placeholder': 'Ej: 10', 'step': '1', 'min': '0'}),
            'precio_compra_mayor': forms.NumberInput(attrs={'placeholder': '0', 'step': '1', 'min': '0'}),
            'precio_venta_mayor': forms.NumberInput(attrs={'placeholder': '0', 'step': '1', 'min': '0'}),
            'margen_ganancia_mayor': forms.NumberInput(attrs={'placeholder': '0.0', 'step': '0.1', 'min': '-100'}),
        }
        labels = {
            'nombre_articulo': 'Nombre',
            'descripcion': 'Descripción',
            'categoria': 'Categoría',
            'proveedor': 'Proveedor',
            'codigo_qr': 'Código QR',
            'codigo_barra': 'Código de barras',
            'precio_compra': 'Precio de compra ($)',
            'precio_venta': 'Precio de venta ($)',
            'margen_ganancia': 'Margen de ganancia (%)',
            'unidad_medida': 'Unidad de medida',
            'foto': 'Foto del producto',
            'activo': 'Producto activo',
            'stock_minimo': 'Stock mínimo',
            'cantidad_minima_mayor': 'Cantidad mínima mayorista',
            'precio_compra_mayor': 'Precio de compra mayorista ($)',
            'precio_venta_mayor': 'Precio de venta mayorista ($)',
            'margen_ganancia_mayor': 'Margen mayorista (%)',
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        qs_cat = Categoria.objects.filter(estado=True)
        qs_prov = Proveedor.objects.filter(activo=True)
        if empresa:
            qs_cat = qs_cat.filter(empresa=empresa)
            qs_prov = qs_prov.filter(empresa=empresa)
        self.fields['categoria'].queryset = qs_cat
        self.fields['categoria'].required = False
        self.fields['categoria'].empty_label = '— Sin categoría —'
        self.fields['proveedor'].queryset = qs_prov
        self.fields['proveedor'].required = False
        self.fields['proveedor'].empty_label = '— Sin proveedor —'
        self.fields['foto'].required = False
        self.fields['descripcion'].required = False
        self.fields['codigo_qr'].required = False
        self.fields['codigo_barra'].required = False
        self.fields['margen_ganancia'].required = False


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['categoria', 'estado']
        widgets = {
            'categoria': forms.TextInput(attrs={'placeholder': 'Nombre de la categoría'}),
        }
        labels = {
            'categoria': 'Nombre',
            'estado': 'Activa',
        }


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'rut', 'correo', 'numero_contacto', 'forma_pago', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre o razón social'}),
            'rut': forms.TextInput(attrs={'placeholder': 'Ej: 12.345.678-9'}),
            'correo': forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
            'numero_contacto': forms.TextInput(attrs={'placeholder': '+56 9 1234 5678'}),
            'forma_pago': forms.TextInput(attrs={'placeholder': 'Ej: Transferencia, Efectivo...'}),
        }
        labels = {
            'nombre': 'Nombre / Razón social',
            'rut': 'RUT',
            'correo': 'Correo electrónico',
            'numero_contacto': 'Teléfono de contacto',
            'forma_pago': 'Forma de pago',
            'activo': 'Proveedor activo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['rut', 'correo', 'numero_contacto', 'forma_pago']:
            self.fields[f].required = False


class UsuarioForm(forms.ModelForm):
    """
    Gestión de usuarios de la empresa (misma tabla que usa la app móvil).
    `categorias` no es un campo de la tabla: se mapea a/desde el JSON
    `id_categorias` en la vista. Un trabajador solo verá artículos de esas
    categorías; un administrador las ve todas.
    """
    TIPO_CHOICES = [('administrador', 'Administrador'), ('trabajador', 'Trabajador')]

    tipo_usuario = forms.ChoiceField(choices=TIPO_CHOICES, label='Tipo de usuario')
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Categorías asignadas',
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'correo', 'tipo_usuario', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre completo'}),
            'correo': forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
        }
        labels = {
            'nombre': 'Nombre completo',
            'correo': 'Correo electrónico',
            'activo': 'Usuario activo',
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        qs_cat = Categoria.objects.filter(estado=True)
        if empresa:
            qs_cat = qs_cat.filter(empresa=empresa)
        self.fields['categorias'].queryset = qs_cat.order_by('categoria')
        # Precargar las categorías guardadas en id_categorias (JSON con los PK)
        if self.instance and self.instance.pk and self.instance.id_categorias:
            self.fields['categorias'].initial = list(self.instance.id_categorias)


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nombre', 'rut', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre de tu negocio'}),
            'rut': forms.TextInput(attrs={'placeholder': 'Ej: 76.123.456-7'}),
        }
        labels = {
            'nombre': 'Nombre del negocio',
            'rut': 'RUT',
            'activo': 'Activa',
        }
