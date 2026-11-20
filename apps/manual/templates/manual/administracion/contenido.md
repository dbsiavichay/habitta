{% load manual %}La sección Contenido del sitio guarda los textos y las imágenes que no dependen de los anuncios.

## Portada y fondos

Son las imágenes de fondo de la portada, de los términos y de la página de ayuda. Puedes tener varias configuraciones guardadas, pero sólo una está activa: al activar una se desactivan las demás. El **nombre** sirve para reconocer cada configuración.

El bloque plegado **Del diseño anterior** guarda campos que el diseño actual ya no usa.

{% figura 'administracion/portada-fondos.webp' 'La configuración activa de fondos.' %}

## Términos y Ayuda

**Términos** son las cláusulas de la página [Términos y condiciones]({% url 'terms' %}). **Ayuda** son las preguntas frecuentes de la página [Ayuda]({% url 'help' %}).

- Cada una tiene un título y una descripción en texto plano; los saltos de línea se respetan.
- Las nuevas se agregan al final, con el botón **+**.
- Para cambiar el orden, arrastra las filas desde el ícono de la izquierda y toca **Guardar**.

{% figura 'administracion/terminos.webp' 'Los términos: se ordenan arrastrando.' %}

!!! demo "Preguntas sin respuesta"
    Si una pregunta frecuente dice «No disponible», escribe su respuesta aquí, en **Ayuda**.

## Redes sociales

Son las redes que los usuarios pueden poner en su perfil, como Facebook o Instagram. Cada una tiene un nombre, un ícono y una dirección base (por ejemplo, `https://facebook.com/`); el usuario sólo escribe su nombre de usuario.

## Íconos

Es la fuente de íconos (IcoMoon) de las especificaciones, con sus archivos CSS, WOFF, TTF, EOT y SVG. Sólo una puede estar activa a la vez, y sus íconos son los que eliges en cada especificación.
