{% load manual %}La administración es la parte interna de {{ SITE_NAME }}: desde ahí el equipo confirma pagos, revisa publicaciones, atiende a los usuarios y mantiene el catálogo y los textos del sitio.

## Quién puede entrar

Cada cuenta tiene uno de estos tres niveles:

| Cuenta | Qué puede hacer en la administración |
|---|---|
| Usuario | No entra. Si abre la administración, se le pide iniciar sesión con una cuenta del equipo. |
| Equipo (staff) | Entra y ve sólo los módulos que sus permisos le permiten leer. Para confirmar transferencias o cancelar subastas necesita, además, permiso para modificarlas. |
| Superusuario | Ve y modifica todo. Es el único que ve las conversaciones privadas. |

El acceso lo da un superusuario desde **Usuarios** y **Grupos y permisos**. El capítulo [Usuarios y permisos]({% url 'manual_chapter' 'administracion' 'usuarios' %}) explica cómo.

## Cómo entrar

1. Inicia sesión en el sitio con tu cuenta.
2. Abre el menú de tu cuenta, arriba a la derecha, y elige **Administración**. Esa opción sólo aparece en las cuentas del equipo.

También puedes ir directo a la dirección `/admin/`. Si no tienes la sesión iniciada, verás la pantalla de ingreso de la administración. Ahí se entra con el **nombre de usuario**, no con el correo.

{% figura 'administracion/ingreso.webp' 'Pantalla de ingreso de la administración.' %}

[Abrir la administración]({% url 'admin:index' %}){.manual-go}

## El menú lateral

A la izquierda está el menú, ordenado por tareas:

| Sección | Módulos |
|---|---|
| Operación | Transferencias, Pagos PayPal, Publicaciones y Subastas |
| Comunidad | Usuarios, Vistas y me gusta, Comentarios y Conversaciones |
| Catálogo | Categorías, Formularios, Especificaciones y Propósitos |
| Contenido del sitio | Portada y fondos, Términos, Ayuda, Redes sociales e Íconos |
| Sistema | Bancos, Grupos y permisos e Imágenes |
| Manuales | Este manual |

El número junto a **Transferencias** cuenta las que esperan confirmación. Si a tu cuenta le falta permiso para ver un módulo, ese módulo no aparece en el menú.

El campo **Buscar en el menú…**, arriba de todo, filtra los módulos mientras escribes. El ícono de panel, junto al título de la página, esconde o muestra el menú.

{% figura 'administracion/inicio.webp' 'Menú lateral y página de inicio de la administración.' %}

## Buscar cualquier cosa

Pulsa <kbd>⌘</kbd> <kbd>K</kbd> en Mac o <kbd>Ctrl</kbd> <kbd>K</kbd> en Windows y Linux para abrir el buscador. Además de los módulos del menú, encuentra registros de:

- usuarios;
- publicaciones;
- transferencias;
- categorías;
- especificaciones.

Muévete entre los resultados con las flechas y abre uno con <kbd>Enter</kbd>. El buscador recuerda tus búsquedas recientes y sólo muestra lo que tu cuenta puede ver.

{% figura 'administracion/buscador.webp' 'El buscador encuentra módulos y registros.' %}

## Volver al sitio y cerrar sesión

Arriba del menú, al tocar el nombre del sitio, se abre un menú con tres atajos:

- **Ver el sitio**;
- **Mi panel**, que abre tus publicaciones;
- **Manual de administración**.

{% figura 'administracion/menu-sitio.webp' 'Atajos al sitio, a tu panel y a este manual.' 'angosta' %}

Abajo del menú están tu nombre y tu correo. Al tocarlos puedes:

- elegir el tema **Claro**, **Oscuro** o del **Sistema**;
- volver al sitio;
- **cerrar sesión**.

{% figura 'administracion/menu-usuario.webp' 'Tema y cierre de sesión.' 'angosta' %}

## Cómo se usan las listas y las fichas

Todos los módulos funcionan igual:

- **Lista.** Muestra los registros con una caja de búsqueda y el botón **Filtros**. Elige los filtros y toca **Aplicar filtros**. Mientras haya filtros activos, **Quitar filtros** te devuelve a la lista completa. Para ordenar, toca el título de una columna.
- **Acciones.** Algunos módulos tienen acciones en cada fila, como confirmar una transferencia. Otras se aplican a varios registros a la vez: marca las casillas de la izquierda y elige la acción en **Elige una acción**.
- **Ficha.** Al abrir un registro ves su ficha, a veces dividida en pestañas. Arriba, **Histórico** muestra los cambios hechos desde la administración y **Ver en el sitio** abre el registro en el sitio. Abajo están los botones para guardar y para eliminar. Si cambias algo y quieres irte sin guardar, la administración te avisa.

Los capítulos siguientes explican cada módulo.
