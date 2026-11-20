{% load manual %}Quienes compran los archivos de un anuncio pagan por transferencia, y suben el comprobante, o con PayPal. Las transferencias necesitan que alguien del equipo las revise; PayPal se confirma solo.

## Revisa las transferencias

En **Transferencias** las pendientes salen primero, con la etiqueta **Por confirmar**. Después vienen las confirmadas y las rechazadas, de la más reciente a la más antigua. El número junto a **Transferencias**, en el menú, cuenta las pendientes.

- Busca por el nombre, el usuario o el correo de quien pagó.
- En **Filtros** puedes elegir estado, banco y rango de fechas.
- **Pagado por** abre en otra pestaña el anuncio que se compró.

{% figura 'administracion/transferencias.webp' 'La lista de transferencias: primero las que esperan confirmación.' %}

## Confirma o rechaza una transferencia

Abre la transferencia para ver el comprobante (la imagen, o un enlace si es un PDF). Compara el monto y la cuenta con el pago registrado. Arriba a la derecha tienes dos botones:

- **Confirmar**: pide una confirmación. Al aceptar, el pago queda **Confirmado**, se habilita la descarga y el usuario recibe un correo.
- **Rechazar**: puedes escribir un motivo, que es opcional y va en el correo al usuario. Después, el usuario puede registrar el pago de nuevo.

{% figura 'administracion/transferencia-ficha.webp' 'La ficha de una transferencia pendiente, con el comprobante.' %}

{% figura 'administracion/transferencia-confirmar.webp' 'Confirmación antes de aprobar el pago.' %}

{% figura 'administracion/transferencia-rechazar.webp' 'El motivo del rechazo llega al usuario por correo.' %}

Las mismas acciones están en el menú **⋯** de cada fila de la lista. En la ficha sólo aparecen mientras la transferencia espera confirmación. En la lista aparecen siempre: si la transferencia ya estaba resuelta, la acción avisa y no cambia nada.

### Varias a la vez

Marca las casillas de las transferencias y, en **Elige una acción**, toca **Confirmar las transferencias seleccionadas** o **Rechazar las transferencias seleccionadas**. En lote no se pide confirmación ni motivo, y las que ya estaban resueltas se saltan.

!!! warning "Permisos"
    Para confirmar o rechazar necesitas permiso para modificar pagos bancarios. Con permiso de sólo lectura puedes ver las transferencias, pero no resolverlas.
{% if not EMAIL_ENABLED %}
!!! demo "En este demo"
    El sitio no envía correos reales: el estado del pago cambia igual, pero el aviso no le llega al usuario.
{% endif %}
## Pagos PayPal

Es sólo de consulta: PayPal confirma o rechaza el pago cuando el usuario vuelve al sitio, así que aquí no hay acciones. Puedes buscar por el correo del pagador o el número del pago, y filtrar por estado y fecha.

## Bancos

Son las cuentas que ve el usuario cuando elige pagar por transferencia. Cada una tiene el banco, el tipo de cuenta (corriente o de ahorros), el número, el beneficiario y su identificación. Se agregan, editan o eliminan desde **Bancos**, en la sección Sistema del menú.

Si no hay ninguna cuenta, el usuario ve un aviso que lo invita a escribir desde Ayuda.
