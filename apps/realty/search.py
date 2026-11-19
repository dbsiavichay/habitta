"""Datos compartidos por los buscadores del frontend (hero de la home y explorador)."""
from .models import Category, Purpose


def search_data():
    """Categorías habilitadas (con tipo y propósitos) y propósitos, para filtrar los selects en el navegador.

    Se serializa con |json_script; reemplaza la llamada AJAX que antes recargaba el select de
    categorías cada vez que cambiaba el propósito.
    """
    categories = Category.objects.filter(enabled=True).prefetch_related('purposes').order_by('kind', 'name')
    return {
        'categories': [
            {
                'id': category.id,
                'name': category.name,
                'kind': category.kind,
                'purposes': [purpose.id for purpose in category.purposes.all()],
            }
            for category in categories
        ],
        'purposes': [{'id': purpose.id, 'name': purpose.for_user} for purpose in Purpose.objects.all()],
    }
