from django.db import models


class Articulo(models.Model):
    """
    Catálogo de artículos de la empresa.
    El stock real NO se guarda aquí; se calcula desde la tabla Stock:
        stock_actual = SUM(ENTRADA) - SUM(SALIDA)
    """
    UNIDAD_CHOICES = [('unidad', 'Unidad'), ('kg', 'Kilogramo'), ('lb', 'Libra')]

    id_articulo     = models.CharField(max_length=36, primary_key=True)
    empresa         = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    proveedor       = models.ForeignKey('Proveedor', null=True, blank=True, on_delete=models.SET_NULL)
    nombre_articulo = models.CharField(max_length=255)
    descripcion     = models.TextField(null=True, blank=True)
    categoria       = models.ForeignKey(
        'Categoria', null=True, blank=True,
        on_delete=models.SET_NULL,
        db_column='categoria',
        related_name='articulos',
    )
    codigo_qr       = models.CharField(max_length=100, null=True, blank=True)
    codigo_barra    = models.CharField(max_length=100, null=True, blank=True)
    precio_compra   = models.FloatField()
    precio_venta    = models.FloatField()
    foto            = models.ImageField(upload_to='productos/', null=True, blank=True)
    foto_url        = models.URLField(null=True, blank=True)
    unidad_medida   = models.CharField(max_length=10, choices=UNIDAD_CHOICES, default='unidad')
    margen_ganancia = models.FloatField(default=0.0)
    activo          = models.BooleanField(default=True)
    created_at      = models.DateTimeField(null=True, blank=True)
    updated_at      = models.DateTimeField(null=True, blank=True)
    sync_status     = models.CharField(max_length=20, default='pending')

    class Meta:
        db_table = 'articulo'
        verbose_name = 'Artículo'
        verbose_name_plural = 'Artículos'

    def __str__(self):
        return self.nombre_articulo
