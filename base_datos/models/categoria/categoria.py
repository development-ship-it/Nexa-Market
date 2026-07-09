from django.db import models


class Categoria(models.Model):
    """Agrupador de artículos. Usado para filtros en POS y reportes."""
    id_categoria = models.CharField(max_length=36, primary_key=True)
    empresa      = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    categoria    = models.CharField(max_length=255)
    estado       = models.BooleanField(default=True)
    sync_status  = models.CharField(max_length=20, default='pending')

    class Meta:
        db_table = 'categoria'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.categoria
