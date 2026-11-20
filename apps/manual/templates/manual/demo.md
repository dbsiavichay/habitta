{% load manual %}Este sitio es una demostración de {{ SITE_NAME }}. Puedes recorrerlo como cualquier persona que busca o publica anuncios.

### Como usuario

1. [Crea tu cuenta]({% url 'register' %}). Es gratis y sólo pide correo, usuario y contraseña. El [capítulo 1 del manual del usuario]({% url 'manual_chapter' 'usuarios' 'primeros-pasos' %}) explica cada paso.
2. Busca en el [explorador]({% url 'finder' %}), abre un anuncio y guárdalo en tus favoritos.
3. [Publica un anuncio de prueba]({% url 'choose_category' %}). Puedes editarlo, sumarle fotos, ponerlo en subasta y borrarlo cuando termines.
4. Para ver el chat en tiempo real, abre una segunda cuenta en otra ventana privada y escríbele a tu anuncio.
{% if purchasable_categories %}5. Para probar la compra de archivos, abre un anuncio de {{ purchasable_categories|join:", " }} y toca **Comprar**. El pago queda en revisión hasta que alguien del equipo lo confirme.
{% endif %}
!!! warning "Usa el chat del sitio para probar el contacto"
    Los anuncios de ejemplo pueden tener teléfonos o correos de personas reales. No les escribas por WhatsApp, teléfono ni correo: prueba el contacto con tus propias cuentas.

### Como administrador

La administración no tiene registro abierto. Si quieres recorrerla, pídele acceso a quien te compartió el demo. Mientras tanto, el [manual de administración]({% url 'manual_index' 'administracion' %}) muestra cada pantalla.

### Límites conocidos del demo

- Los planes de la portada son ilustrativos: publicar es gratis y no tiene límite de anuncios.
- Las ofertas de las subastas todavía no se envían desde el sitio. El botón «Quiero participar» abre el chat con el dueño.
- Los mapas y las sugerencias de lugares usan datos de OpenStreetMap: algunas direcciones con número de casa no aparecen. En ese caso, marca el punto en el mapa.
{% if not purchasable_categories %}- La compra de archivos (planos, catálogos) no está activa: ninguna categoría tiene anuncios con archivos a la venta.
{% endif %}{% if not EMAIL_ENABLED %}- Este demo no envía correos: no llegarán el enlace para recuperar la contraseña ni los avisos de pago.
{% endif %}{% if not PAYPAL_ENABLED %}- El pago con PayPal está desactivado. Para pagar sólo está la transferencia bancaria.
{% endif %}{% if not FACEBOOK_LOGIN_ENABLED and not TWITTER_LOGIN_ENABLED %}- El ingreso con Facebook o X está desactivado: crea tu cuenta con tu correo.
{% endif %}
