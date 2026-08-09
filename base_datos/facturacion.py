"""
Reglas de cobro de la suscripción SaaS.

Los precios de `Plan` se guardan **con IVA incluido** — es el valor que se le
publica al cliente. El desglose neto/IVA se calcula al cobrar y queda congelado
en cada `Pago`, porque los precios del plan cambian con el tiempo y el histórico
tiene que seguir cuadrando contra la cartola del banco.
"""
import calendar

IVA_PORCENTAJE = 19

# Días que la empresa sigue operando después del vencimiento antes de degradar
# al plan local. En un punto de venta cortar la caja de golpe pierde al cliente.
DIAS_GRACIA = 7


def sumar_un_mes(fecha):
    """
    Suma un mes calendario ajustando al último día válido del mes destino:
    31-ene → 28-feb (29 en bisiesto). Sin este ajuste, un pago hecho un día 31
    reventaría al calcular el vencimiento.
    """
    mes = fecha.month + 1
    anio = fecha.year + (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return fecha.replace(year=anio, month=mes, day=dia)


def desglosar_iva(total):
    """`total` viene con IVA incluido → devuelve (neto, iva) en pesos enteros."""
    neto = round(total / (1 + IVA_PORCENTAJE / 100))
    return neto, total - neto
