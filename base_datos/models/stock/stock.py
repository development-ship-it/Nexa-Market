from django.db import models


class Stock(models.Model):
    """
    Libro de movimientos de inventario — append-only.
    ENTRADA: artículo ingresó al inventario (origen: Compra)
    SALIDA:  artículo salió del inventario  (origen: Venta)

    Stock actual de un artículo = SUM(unidades WHERE tipo=ENTRADA)
                                 - SUM(unidades WHERE tipo=SALIDA)
    """
    TIPO_CHOICES = [('ENTRADA', 'Entrada'), ('SALIDA', 'Salida')]

    id_stock               = models.CharField(max_length=36, primary_key=True)
    articulo               = models.ForeignKey('Articulo', on_delete=models.CASCADE, related_name='movimientos')
    empresa                = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    usuario                = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    tipo                   = models.CharField(max_length=10, choices=TIPO_CHOICES)
    unidades               = models.IntegerField()
    precio_unitario_compra = models.FloatField()
    precio_unitario_venta  = models.FloatField()
    total                  = models.FloatField()
    factura                = models.ForeignKey('Factura', null=True, blank=True, on_delete=models.SET_NULL, related_name='lineas')
    id_lote                = models.CharField(max_length=36, null=True, blank=True)
    fecha_vencimiento      = models.DateTimeField(null=True, blank=True)
    fecha_hora             = models.DateTimeField()
    sync_status            = models.CharField(max_length=20, default='pending')

    class Meta:
        db_table = 'stock'
        verbose_name = 'Movimiento de stock'
        verbose_name_plural = 'Movimientos de stock'
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"{self.tipo} — {self.articulo} ({self.unidades}u)"

    @property
    def es_entrada(self):
        return self.tipo == 'ENTRADA'

    @property
    def label_tipo(self):
        if self.tipo == 'ENTRADA':
            return 'Compra'
        if self.factura and self.factura.tipo == 'MERMA':
            return 'Merma'
        return 'Venta'
