from django.db import models


class Factura(models.Model):
    """
    Agrupa todos los movimientos de Stock de una transacción.
    Una COMPRA agrupa los artículos ingresados en un mismo carrito de compra.
    Una VENTA agrupa los artículos vendidos antes de confirmar el carrito.
    Una MERMA agrupa salidas por pérdida/deterioro (las crea la app móvil).
    tipo: 'COMPRA' → entradas | 'VENTA' → salidas | 'MERMA' → salidas sin venta
    """
    TIPO_CHOICES = [('COMPRA', 'Compra'), ('VENTA', 'Venta'), ('MERMA', 'Merma')]

    id_nfactura    = models.CharField(max_length=36, primary_key=True)
    empresa        = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    usuario        = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    numero_factura = models.CharField(max_length=50)
    fecha          = models.DateTimeField()
    total          = models.FloatField()
    tipo           = models.CharField(max_length=10, choices=TIPO_CHOICES)
    created_at     = models.DateTimeField(null=True, blank=True)
    sync_status    = models.CharField(max_length=20, default='pending')

    class Meta:
        db_table = 'factura'
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'

    def __str__(self):
        return f"{self.tipo} - {self.numero_factura}"
