{% load manual %}Para buscar anuncios no necesitas cuenta. Sí la necesitas para publicar, guardar favoritos, conversar con quienes publican y crear subastas.

## Crea tu cuenta

1. Toca **Crear cuenta**, arriba a la derecha. En el celular, entra por **Ingresar** y luego **Crea una gratis**.
2. Escribe tu **correo electrónico**. Cada correo sirve para una sola cuenta, y es el que usarás si olvidas tu contraseña.
3. Elige un **nombre de usuario**. Forma parte de la dirección de tu perfil público, así que no lleva espacios: usa letras, números y `@ . + - _`.
4. Crea una **contraseña** de al menos 8 caracteres. No puede ser una contraseña común, tener sólo números ni parecerse a tu usuario. El ícono del ojo la muestra mientras la escribes.
5. Toca **Crear cuenta**. Al hacerlo aceptas los [términos de uso]({% url 'terms' %}).

{% figura 'usuarios/registro.webp' 'Formulario para crear la cuenta.' %}
{% if FACEBOOK_LOGIN_ENABLED or TWITTER_LOGIN_ENABLED %}
!!! tip "También con tus redes"
    Arriba del formulario aparecen los botones para crear tu cuenta con {% if FACEBOOK_LOGIN_ENABLED %}Facebook{% if TWITTER_LOGIN_ENABLED %} o X{% endif %}{% else %}X{% endif %}. Con ellos no necesitas inventar una contraseña.
{% endif %}
[Crear mi cuenta]({% url 'register' %}){.manual-go}

## Completa tu perfil

Al crear la cuenta ya quedas con la sesión iniciada, y el sitio te pide tres datos más:

- **Nombres** y **apellidos**: así te verán quienes abran tus anuncios.
- **Número de celular**: activa el botón de WhatsApp en tus anuncios.

Toca **Guardar y continuar**. Si prefieres hacerlo luego, toca **Completar después**: puedes cambiar estos datos cuando quieras desde **Mi perfil**.

{% figura 'usuarios/completar-perfil.webp' 'Después de crear la cuenta, el sitio te pide tu nombre y tu celular.' %}

## Inicia sesión

Toca **Ingresar** y escribe tu **correo o tu nombre de usuario** junto con tu contraseña. Las dos formas sirven.

Si intentas algo que pide sesión, como publicar o guardar un favorito, el sitio te lleva a iniciar sesión y luego te devuelve a donde estabas.

{% figura 'usuarios/ingresar.webp' 'Inicio de sesión en el celular.' 'angosta' %}

## Recupera tu contraseña

1. En **Ingresar**, toca **¿Olvidaste tu contraseña?**
2. Escribe el correo de tu cuenta y toca **Enviar enlace**.
3. Abre el correo que te llega y sigue el enlace para crear una contraseña nueva. El enlace sirve una sola vez.

Si no lo ves en unos minutos, busca en las carpetas de spam o promociones.
{% if not EMAIL_ENABLED %}
!!! demo "En este demo"
    El demo no envía correos, así que el enlace no llegará. Si olvidas tu contraseña, crea otra cuenta.
{% endif %}
## Tu menú y tu panel

Con la sesión iniciada, arriba a la derecha aparecen tu foto o tus iniciales. Al tocarlas se abre tu menú:

| Opción | Para qué sirve |
|---|---|
| Mis publicaciones | Ver, editar y administrar tus anuncios |
| Favoritos | Los anuncios que guardaste |
| Mensajes | Tus conversaciones, con un contador de mensajes sin leer |
| Subastas | Las subastas de tus anuncios |
| Mis pagos y Descargas | Lo que compraste y los archivos que puedes bajar |
| Mi perfil | Tus datos, tu foto y tus redes |
| Manuales de uso | Este manual y el de administración |
| Tema | Cambiar entre claro y oscuro |
| Cerrar sesión | Salir de tu cuenta |

{% figura 'usuarios/menu-cuenta.webp' 'El menú de tu cuenta.' %}

Cada opción abre tu **panel**: a la izquierda tienes las mismas secciones, y en el celular aparecen como botones arriba del contenido. Bajo el título de cada pantalla verás **¿Cómo funciona?**, que te trae al capítulo de este manual que la explica.

En el celular también tienes una barra fija abajo con **Inicio**, **Explorar**, **Publicar** (el botón grande del centro), **Favoritos** y **Mensajes**.

## Tema claro u oscuro

Desde **Tema**, en tu menú, o desde el ícono de sol y luna en las páginas para ingresar, puedes elegir:

- **Tema del sistema**: sigue la configuración de tu teléfono o computador. Es la opción inicial.
- **Tema claro** o **tema oscuro**: queda fijo en ese navegador.

Cada toque pasa a la opción siguiente.
