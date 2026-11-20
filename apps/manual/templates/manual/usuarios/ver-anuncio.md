{% load manual %}Al abrir un anuncio ves todo lo que publicó su dueño y las formas de contactarlo.

## Lo que muestra un anuncio

- **Encabezado**: el tipo (Casa, Oficina…), el propósito (En venta, En renta…), la etiqueta **En subasta** si la tiene, el título, la dirección y hace cuánto se publicó. Los servicios sin dirección fija dicen **Atiende en tu zona**.
- **Galería**: toca una foto para verla en grande y desliza entre todas. **Ver las N fotos** abre la galería completa.
- **Descripción**: si es larga, **Leer más** la muestra completa.
- **Especificaciones**: los datos de la categoría, agrupados (Detalles, Características…). Si el anuncio vende archivos, como un plano, verás un enlace **Descargar**.
- **Ubicación** o **Zona de cobertura** en un mapa, con **Cómo llegar**, que abre Google Maps.
- Al final, **Más de [nombre]**: otros anuncios de la misma persona.

{% figura 'usuarios/anuncio.webp' 'El encabezado y la galería de un anuncio.' %}

## Contacta a quien publica

La tarjeta de la derecha muestra el precio y las formas de contacto. En el celular, el precio y los botones principales quedan fijos en la barra de abajo.

- **Chatear con [nombre]**: abre el chat del sitio sin salir del anuncio. Lo explica el capítulo [Mensajes]({% url 'manual_chapter' 'usuarios' 'mensajes' %}).
- **WhatsApp**: abre una conversación con un mensaje que ya incluye el enlace del anuncio. Aparece si la persona registró su celular.
- **Llamar**: marca su número.
- **Correo** y sus redes sociales, debajo de su nombre. Al tocar el nombre vas a su perfil público.

Si el anuncio vende archivos, como planos o catálogos, también verás **Comprar**. Lo explica el capítulo [Pagos y descargas]({% url 'manual_chapter' 'usuarios' 'pagos' %}).

{% figura 'usuarios/anuncio-contacto.webp' 'Precio, contacto y datos de quien publica.' 'angosta' %}

!!! warning "Cuida tu dinero"
    Visita el lugar o conoce a la persona antes de pagar, y nunca envíes dinero por adelantado.

## Guárdalo en favoritos

Toca **Guardar**, junto al título. El botón cambia a **Guardado**; tócalo otra vez para quitarlo. El número a su lado cuenta cuántas personas lo guardaron. Si no tienes la sesión iniciada, el sitio te pide ingresar.

Tus anuncios guardados están en [Favoritos]({% url 'favorite_properties' %}). Ahí, el corazón tachado de cada tarjeta lo quita de la lista.

{% figura 'usuarios/favoritos.webp' 'Tus favoritos.' %}

## Compártelo o imprímelo

- **Compartir**: si tu dispositivo lo permite, abre su menú para compartir. Si no, ofrece **WhatsApp** y **Copiar enlace**.
- **Afiche en PDF**: el ícono de la impresora descarga un afiche A4 con los datos del anuncio y un código QR que lleva a él. No necesitas cuenta para descargarlo.

## El perfil de quien publica

Muestra el nombre de la persona, desde cuándo está en {{ SITE_NAME }}, sus redes y todos sus anuncios. Tiene botones para chatear, escribir por WhatsApp, llamar o enviar un correo.

{% figura 'usuarios/perfil-publico.webp' 'El perfil público de un anunciante.' %}
