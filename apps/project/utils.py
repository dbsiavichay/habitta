from .models import Icons


def get_active_icons():
    """Fuente de íconos de especificaciones activa (la sube el admin), o None."""
    return Icons.objects.filter(is_active=True).order_by('-pk').first()


def get_active_icons_url():
    icons = get_active_icons()
    return icons.css.url if icons and icons.css else ''
