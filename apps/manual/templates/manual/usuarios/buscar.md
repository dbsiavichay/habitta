{% load manual %}No necesitas cuenta para buscar. Tienes dos caminos: el buscador de la portada, para empezar rápido, y el explorador, con todos los filtros, la lista y el mapa.

## Desde la portada

Arriba de la [portada]({% url 'home' %}) está el buscador:

1. Elige el tipo de anuncio: **Todo**, **Inmuebles**, **Servicios** o **Empleos**.
2. En **Quiero**, elige qué buscas: comprar, rentar, contratar… Las opciones cambian según el tipo.
3. En **Categoría**, elige una o deja **Todas**.
4. En **Ubicación**, escribe una ciudad o un sector. Mientras escribes aparecen sugerencias de lugares.
5. Toca **Buscar**: se abre el explorador con esos filtros.

Debajo del buscador, las categorías **populares** llevan directo a sus anuncios.

{% figura 'usuarios/portada.webp' 'El buscador de la portada.' %}

## El explorador

El [explorador]({% url 'finder' %}) también se abre desde **Inmuebles**, **Servicios** y **Empleos** en el menú de arriba, o desde **Explorar** en la barra inferior del celular. Estos son sus filtros:

- **Ciudad, sector o dirección**: escribe un lugar y elige una sugerencia. El ícono de la mira, al final del campo, busca cerca de donde estás; el navegador te pide permiso para usar tu ubicación.
- **Tipo**: Todo, Inmuebles, Servicios o Empleos.
- **Propósito** (qué quieres hacer) y **categoría**.
- **Precio**: escribe un mínimo, un máximo o ambos y toca **Aplicar**.
- **Distancia**: aparece cuando eliges un lugar. Va de 2 a 200 km; empieza en 15 km.

Encima de los resultados, cada filtro activo aparece como una etiqueta: tócala para quitarlo. **Limpiar todo** quita todos los filtros a la vez.

{% figura 'usuarios/explorador.webp' 'El explorador en vista de lista.' %}

Los servicios que atienden en una zona, y no en una dirección fija, aparecen aunque filtres por distancia.

!!! tip "Comparte tu búsqueda"
    La dirección de la página guarda los filtros. Cópiala y envíala: quien la abra verá los mismos resultados.

## Mapa o lista

En la computadora, los botones **Mapa** y **Lista** cambian la vista. En el mapa:

- cada pin muestra el precio, y al tocarlo aparece una vista previa del anuncio;
- los anuncios cercanos se agrupan en un círculo con un número: acércate para separarlos;
- si mueves el mapa, toca **Buscar en esta zona** para ver lo que hay ahí.

En el celular, los filtros están en el botón con el ícono de ajustes, junto al buscador; el número sobre él cuenta los filtros activos. El botón flotante **Mapa** abre el mapa y **Lista** te devuelve a los resultados.

{% figura 'usuarios/explorador-filtros.webp' 'Los filtros en el celular.' 'angosta' %}

!!! demo "En este demo"
    El mapa puede aparecer oscurecido o con un aviso de Google: es una limitación de la clave de Google Maps del demo. La vista de lista funciona igual.

## Escanea el código QR de un afiche

Cada anuncio tiene un afiche en PDF con un código QR (lo explica el capítulo [Ver un anuncio]({% url 'manual_chapter' 'usuarios' 'ver-anuncio' %})). En la computadora o la tableta, toca el ícono de QR en la barra de arriba, permite el uso de la cámara y apunta al código. El escáner sólo abre enlaces de {{ SITE_NAME }}.

En el celular ese botón no aparece: usa la cámara del teléfono, que también lee códigos QR.
