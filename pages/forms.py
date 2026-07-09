from django import forms
from base_datos.models import Articulo, Proveedor, Categoria, Empresa


class ArticuloForm(forms.ModelForm):
    class Meta:
        model = Articulo
        fields = [
            'nombre_articulo', 'descripcion',
            'categoria', 'proveedor',
            'codigo_qr', 'codigo_barra',
            'precio_compra', 'precio_venta', 'margen_ganancia',
            'unidad_medida', 'foto', 'activo',
        ]
        widgets = {
            'nombre_articulo': forms.TextInput(attrs={'placeholder': 'Nombre del producto'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripción opcional'}),
            'codigo_qr': forms.TextInput(attrs={'placeholder': 'Código QR'}),
            'codigo_barra': forms.TextInput(attrs={'placeholder': 'Código de barras'}),
            'precio_compra': forms.NumberInput(attrs={'placeholder': '0', 'step': '1', 'min': '0'}),
            'precio_venta': forms.NumberInput(attrs={'placeholder': '0', 'step': '1', 'min': '0'}),
            'margen_ganancia': forms.NumberInput(attrs={'placeholder': '0.0', 'step': '0.1', 'min': '-100'}),
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
