"""Datos de prueba compartidos por las pruebas de las distintas apps.

    from apps.project.testing import create_listing, session_cookie
"""
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point

from apps.realty.models import Category, Group, GroupCategory, Property, Purpose, Specification

IN_MEMORY_LAYER = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


def create_category(kind=Category.REAL_STATE, name='Casas', require_location=True, purposes=None):
    """Categoría con un grupo de especificaciones que contiene el precio (como en la BD real)."""
    spec, _ = Specification.objects.get_or_create(
        internal_name='precio', defaults={'name': 'Precio', 'field_type': 'IntegerField', 'attributes': 'min=1', 'is_required': True}
    )
    category = Category.objects.create(
        kind=kind, name=name, singular_name=name[:-1], price_area='precio', order=1, for_card='precio',
        require_location=require_location,
    )
    group, _ = Group.objects.get_or_create(internal_name='Especificaciones monetarias (no editar)', defaults={'name': 'Detalles'})
    group.specifications.add(spec)
    GroupCategory.objects.create(group=group, category=category, sequence=1)
    if purposes is None:
        purposes = [Purpose.objects.create(for_owner='Vender', for_user='Comprar', activity='En Venta', participle='Vendido')]
    category.purposes.add(*purposes)
    return category


def create_listing(owner, kind=Category.REAL_STATE, name='Casas', price='120000', category=None, title='Casa con jardín'):
    category = category or create_category(kind=kind, name=name)
    spec = Specification.objects.get(internal_name='precio')
    purpose = category.purposes.first()
    return Property.objects.create(
        title=title,
        description='Amplia y luminosa.',
        address='Av. Amazonas, Quito',
        geopoint=Point(-78.4867, -0.1807),
        status=Property.PUBLISHED,
        details={'purpose': purpose.id, 'specifications': {str(spec.id): price}},
        category=category,
        user=owner,
    )


def create_user(username, **kwargs):
    kwargs.setdefault('first_name', username.capitalize())
    return User.objects.create_user(username, f'{username}@example.com', 'x', **kwargs)


def session_cookie(user):
    """Cookie de sesión real para WebsocketCommunicator (AuthMiddlewareStack lee la sesión)."""
    from django.test import Client

    client = Client()
    client.force_login(user)
    return f"sessionid={client.cookies['sessionid'].value}".encode()
