from .models import Icons

def get_active_icons_url():
    try:
        icons = Icons.objects.get(is_active=True)
        return icons.css.url
    except Icons.DoesNotExist:
        return ''