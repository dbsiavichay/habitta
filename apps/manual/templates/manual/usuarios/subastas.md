{% load manual %}Una subasta pone uno de tus anuncios a recibir ofertas durante un tiempo fijo, a partir de un monto base.

## Crea una subasta

1. En [Subastas]({% url 'auctions' %}), toca **Nueva subasta**. También puedes empezar desde **Subastar**, en tu anuncio o en el menú **⋯** de Mis publicaciones.
2. Elige el **anuncio a subastar**. Sólo aparecen tus anuncios que no estén ya en una subasta abierta.
3. Escribe el **monto base** en dólares: la oferta más baja que aceptas.
4. Escribe la **duración en horas**, de 1 a 2160 (90 días). Por ejemplo, 72 horas son 3 días y 168, una semana.
5. Toca **Abrir subasta**. La subasta empieza en ese momento.

{% figura 'usuarios/nueva-subasta.webp' 'El formulario para abrir una subasta.' %}

## Sigue tus subastas

En [Subastas]({% url 'auctions' %}), cada subasta muestra:

- su estado: **Abierta**, **Finalizada** o **Cancelada**;
- la cuenta regresiva;
- el monto base;
- cuántas ofertas tiene y cuál es la mejor.

La subasta se cierra sola cuando se cumple la duración. Mientras está abierta puedes tocar **Cancelar**: se cierra al instante y no acepta más ofertas.

{% figura 'usuarios/subastas.webp' 'Tus subastas.' %}

## Lo que ven los interesados

El anuncio muestra la etiqueta **En subasta** y un recuadro con:

- la cuenta regresiva;
- el monto base;
- la garantía para ofertar, que es el 10 % del monto base;
- las mejores ofertas.

{% figura 'usuarios/subasta-anuncio.webp' 'El recuadro de la subasta en el anuncio.' 'angosta' %}

!!! demo "Por ahora"
    Las ofertas todavía no se envían desde el sitio. **Quiero participar** abre el chat con el dueño del anuncio para acordar la oferta y la garantía.
