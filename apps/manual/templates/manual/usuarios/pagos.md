{% load manual %}Algunos anuncios venden archivos, como planos o catálogos. Cuando los compras y tu pago se confirma, puedes descargarlos.

## Compra

En el anuncio, toca **Comprar por $…**. Ese botón aparece en las categorías que venden archivos y sólo en anuncios que no son tuyos. Después eliges cómo pagar.

{% figura 'usuarios/comprar.webp' 'El botón para comprar los archivos de un anuncio.' 'angosta' %}

## Paga por transferencia o depósito

1. Paga el monto exacto en una de las cuentas que aparecen. El botón junto a cada número de cuenta lo copia.
2. Guarda una foto o un PDF del comprobante.
3. Toca **Ya pagué: registrar comprobante**.
4. Elige la cuenta a la que pagaste, revisa el monto y sube el comprobante: PDF, JPG o PNG de hasta 5 MB.
5. Toca **Registrar pago**.

El pago queda **En revisión** hasta que alguien del equipo lo confirme.

{% figura 'usuarios/elegir-pago.webp' 'Las cuentas para pagar.' %}

{% figura 'usuarios/registrar-pago.webp' 'El formulario para registrar el pago.' %}

## Paga con PayPal

Si está disponible, toca **Continuar con PayPal** y paga con tu cuenta o con tu tarjeta. Al volver al sitio, el pago se confirma al instante y puedes descargar los archivos.
{% if not PAYPAL_ENABLED %}
!!! demo "En este demo"
    El pago con PayPal está desactivado: sólo está la transferencia.
{% endif %}
## Mis pagos

En [Mis pagos]({% url 'list_bank_payment' %}) ves cada pago con su método, su fecha, el anuncio, el comprobante y su estado:

| Estado | Qué significa |
|---|---|
| En revisión | El equipo todavía no revisa tu transferencia. |
| Confirmado | Ya puedes descargar los archivos. |
| Rechazado | Algo no coincidió, por ejemplo el monto. Puedes volver a comprar y registrar el pago de nuevo. |

Cuando el equipo confirma o rechaza tu transferencia, te llega un correo. Si la rechaza, el correo explica el motivo.

{% figura 'usuarios/mis-pagos.webp' 'Tus pagos y su estado.' %}

## Descargas

En [Descargas]({% url 'downloads' %}) están los archivos que compraste. Con el pago confirmado aparece **Descargar**, que baja un archivo ZIP con los archivos del anuncio. Mientras tanto, la tarjeta dice **Pago en revisión**.

{% figura 'usuarios/descargas.webp' 'Tus descargas.' %}
