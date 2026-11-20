{% load manual %}El catálogo define qué se puede publicar y qué datos pide el asistente de publicación. Cámbialo con cuidado: afecta a los anuncios que ya existen.

Se arma así: cada **categoría** usa uno o varios **formularios**, y cada formulario agrupa varias **especificaciones**, que son los campos que llena quien publica. Los **propósitos** dicen qué se puede hacer con un anuncio: vender, rentar, subastar…

## Categorías

Cada fila muestra la categoría con su ícono, el tipo, si está habilitada, si requiere ubicación, el orden y cuántas publicaciones tiene. En **Filtros** puedes elegir tipo, habilitada y requiere ubicación.

{% figura 'administracion/categorias.webp' 'La lista de categorías.' %}

La ficha tiene dos pestañas. En **General**:

- **Datos**: el tipo (Inmuebles, Servicios o Empleos), el nombre, el nombre en singular, el ícono, si está habilitada y su orden.
- **Publicación**:
    - **Requiere ubicación**: encendido pide una dirección exacta; apagado pide una zona con radio, y la categoría se muestra como «Sin ubicación fija».
    - **Puede venderse**: muestra el botón **Comprar** para los archivos de sus anuncios, por el precio del anuncio.
    - **Propósitos**: qué se puede hacer con sus anuncios.
    - **Área del precio**: el nombre interno de la especificación que guarda el precio. Si no coincide con ninguna, ese texto se muestra tal cual en lugar del precio (por ejemplo, «Postular»).
    - **Especificaciones aplicables en tarjeta**: las que se muestran en las tarjetas de los resultados, separadas por coma.

En **Formularios** eliges qué formularios usa la categoría y en qué orden aparecen: arrastra las filas para ordenarlas.

{% figura 'administracion/categoria-publicacion.webp' 'Las opciones de publicación de una categoría.' %}

!!! tip "Para vender archivos"
    Una categoría vende archivos cuando tiene **Puede venderse** encendido, un formulario con una especificación de tipo **Archivo** y un precio en número. La categoría **Planos** está pensada para eso.

## Formularios

Un formulario agrupa especificaciones bajo un título, por ejemplo «Características». Tiene un nombre, un nombre interno, el número de columnas en que se muestran sus campos y sus especificaciones, que se eligen con un selector de dos listas.

!!! warning "No lo toques"
    No cambies el formulario «Especificaciones monetarias (no editar)». Guarda el precio que usan las tarjetas, el explorador y los pagos.

## Especificaciones

Cada especificación es un campo del formulario de publicación:

- **Nombre**: lo que ve quien publica.
- **Nombre interno**: el identificador con el que se guardan los datos.
- **Ícono**: se muestra junto al valor en el anuncio.
- **Tipo de campo**: texto, número entero, número decimal, booleano, selector, opción múltiple o archivo.
- **Elecciones**: las opciones de un selector, separadas por coma. Son obligatorias para los selectores.
- **Atributos**: restricciones del campo, por ejemplo `min=0, max=2030`.
- **Requerido**: si es obligatorio.

{% figura 'administracion/especificacion.webp' 'Una especificación de tipo selector.' %}

!!! warning "El nombre interno"
    No cambies el nombre interno de una especificación que ya se usa en anuncios: sus datos quedarían sin mostrarse.

## Propósitos

Lo que se puede hacer con un anuncio. Cada propósito tiene cuatro textos: para el dueño (Vender), para quien busca (Comprar), la actividad (En venta) y el participio (Vendido). Se ordenan arrastrando las filas.
