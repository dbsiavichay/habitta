{% load manual %}Publicar es gratis y tu anuncio se ve apenas lo publicas. Necesitas tener la sesión iniciada. El asistente tiene seis pasos; la barra de arriba te muestra en cuál estás.

[Publicar un anuncio]({% url 'choose_category' %}){.manual-go}

## 1. Elige la categoría

Toca **Publica gratis**, arriba, o el botón **+** de la barra inferior del celular. Elige la pestaña **Inmuebles**, **Servicios** o **Empleos**, o busca la categoría por su nombre. Debajo de cada categoría ves qué permite: vender, rentar, subastar…

Las que dicen **Sin ubicación fija** son para servicios que atiendes en una zona y no en una dirección.

{% figura 'usuarios/publicar-categoria.webp' 'Las categorías de inmuebles.' %}

La categoría define los datos que te pedirá el asistente y no se puede cambiar después. Si te equivocas, toca **Cambiar**, junto a su nombre, antes de publicar.

## 2. Datos

- **¿Qué quieres hacer?**: vender, rentar, subastar… No aparece si la categoría tiene una sola opción.
- **Título del anuncio**: corto y claro, de hasta 32 caracteres. El contador te dice cuántos llevas.
- **Descripción**: opcional, pero ayuda a que te escriban.
- Debajo hay un bloque por cada grupo de datos de la categoría: precio, área, habitaciones… Los campos con asterisco son obligatorios. Si la categoría pide un archivo, como un plano, acepta PDF o DWG.

Toca **Siguiente**. Antes de avanzar, el asistente revisa los campos y te marca los que faltan.

{% figura 'usuarios/publicar-datos.webp' 'El paso de datos.' %}

## 3. Ubicación

Si la categoría tiene una dirección fija, como una casa o un local:

1. Escribe la dirección y elige una de las sugerencias.
2. Ajusta el pin en el punto exacto: toca el mapa o arrastra el pin.
3. Si estás en el lugar, toca **Usar mi ubicación**.

Así tu anuncio aparece en el mapa del explorador.

Si es un servicio sin ubicación fija, marca tu ciudad o zona y, con la barra **Hasta dónde llegas**, elige un radio de 0,5 a 50 km. Tu anuncio aparece a quienes buscan dentro de ese radio.

{% figura 'usuarios/publicar-ubicacion.webp' 'El paso de ubicación.' %}

!!! tip "Si el mapa no carga"
    Escribe la dirección y usa **Usar mi ubicación**: el punto queda marcado igual.

## 4. Portada

La portada es la foto que se ve en los resultados. Arrastra una foto o haz clic para elegirla (JPG, PNG o WEBP). Se abre un recorte horizontal (16:9): mueve y acerca la foto y toca **Usar esta portada**.

Elige una foto con buena luz, en horizontal y sin textos, logos ni marcas de agua. La portada es opcional: sin ella se muestra una imagen genérica.

{% figura 'usuarios/publicar-portada.webp' 'El paso de portada.' %}

## 5. Revisa y publica

El último paso resume lo que escribiste, por secciones. **Editar** te lleva al paso correspondiente. A la derecha ves cómo quedará la tarjeta del anuncio en los resultados.

Toca **Publicar anuncio**. Tu anuncio queda visible al instante.

{% figura 'usuarios/publicar-revisar.webp' 'El resumen antes de publicar.' %}

!!! tip "Muévete entre pasos"
    **Atrás** y **Siguiente** cambian de paso; la tecla Enter también avanza. Si intentas salir con cambios sin guardar, el sitio te avisa.

## 6. Suma fotos

Al publicar llegas a **Suma más fotos**. Arrastra varias fotos a la vez o haz clic para elegirlas (JPG o PNG): se suben solas. Para quitar una, toca la papelera que aparece sobre ella.

La portada no se borra aquí; se cambia al editar el anuncio.

{% figura 'usuarios/publicar-fotos.webp' 'La galería de fotos de un anuncio.' %}

Puedes volver a esta pantalla cuando quieras, desde **Fotos** en [Mis publicaciones]({% url 'properties' %}).
