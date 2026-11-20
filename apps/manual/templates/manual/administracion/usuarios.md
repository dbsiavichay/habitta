{% load manual %}En **Usuarios** atiendes las cuentas: corriges datos, desactivas cuentas y decides quién entra a la administración y qué puede hacer ahí.

## La lista

Cada fila muestra la foto o las iniciales, el nombre y el correo, el rol (**Superusuario**, **Staff** o **Usuario**), si la cuenta está activa, la fecha de alta, el último acceso y cuántas publicaciones tiene.

- Busca por usuario, nombres, apellidos o correo.
- En **Filtros** puedes elegir staff, superusuario, activo, fecha de alta y grupo.

{% figura 'administracion/usuarios.webp' 'La lista de usuarios.' %}

## La ficha de un usuario

Tiene sus datos personales, el **perfil** (celular y foto, que se pueden corregir), los permisos y las fechas de alta y de último acceso. Una pestaña aparte muestra las redes con las que inicia sesión (Facebook o X), sólo de lectura.

La contraseña no se ve. Para cambiarla usa el enlace al formulario de contraseña, junto al campo.

### Desactiva una cuenta

Apaga **Activo** en vez de eliminar al usuario: la persona ya no puede iniciar sesión y se conserva su historial. Sus anuncios siguen publicados; si hace falta, elimínalos desde **Publicaciones**.

## Da acceso a la administración

Conviene dar los permisos por grupos: así es fácil dar el mismo acceso a varias personas y quitarlo después.

1. En **Grupos y permisos**, toca **+** y crea un grupo, por ejemplo «Revisores».
2. Elige sus permisos en la lista de la izquierda y pásalos a la derecha con la flecha. Usa **Filtro** para encontrarlos por nombre.
3. En la ficha de la persona, enciende **Es staff** y agrégala al grupo, en **Grupos**.
4. Toca **Guardar**. La próxima vez que entre, verá **Administración** en el menú de su cuenta.

{% figura 'administracion/grupo.webp' 'Un grupo nuevo: nombre y permisos.' %}

{% figura 'administracion/usuario-permisos.webp' 'Staff, superusuario y grupos en la ficha de un usuario.' %}

Los permisos aparecen como «Sección | modelo | Can view …». La acción está al final: **view** es ver, **add** es crear, **change** es modificar y **delete** es eliminar.

| Para que la persona pueda… | Dale estos permisos |
|---|---|
| Revisar y confirmar transferencias | Ver y modificar *pago bancario* |
| Revisar y corregir publicaciones | Ver y modificar *propiedad*; para eliminarlas, también eliminar |
| Seguir y cancelar subastas | Ver y modificar *subasta* |
| Mantener el catálogo | Ver, crear y modificar *categoría*, *formulario*, *especificación* y *propósito* |
| Editar los textos del sitio | Ver, crear y modificar *Configuración*, *Término* y *Ayuda* |

Una persona con permiso de sólo lectura ve los módulos, pero no las acciones que cambian datos. Los módulos sin permiso no aparecen en su menú.

!!! warning "Superusuario"
    **Estado de superusuario** da todos los permisos sin asignarlos uno por uno, incluidas las conversaciones privadas entre usuarios. Resérvalo para quien administra el sitio.
