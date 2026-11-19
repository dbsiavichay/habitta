from functools import cached_property, total_ordering

from .models import Message


@total_ordering
class LazyCount:
    """Entero que se calcula la primera vez que se usa (en una plantilla) y luego se reutiliza."""

    def __init__(self, func):
        self._func = func

    @cached_property
    def value(self):
        return int(self._func())

    def __int__(self):
        return self.value

    __index__ = __int__

    def __float__(self):
        return float(self.value)

    def __bool__(self):
        return self.value > 0

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return self.value == int(other)

    def __lt__(self, other):
        return self.value < int(other)

    __hash__ = None


def unread_messages(request):
    """Mensajes sin leer del usuario, para las insignias de navbar, barra inferior y panel.

    Es perezoso: la consulta sólo corre si alguna plantilla lo usa, y una vez por petición.
    """
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {'unread_messages': 0}
    return {'unread_messages': LazyCount(lambda: Message.objects.unread_for(user).count())}
