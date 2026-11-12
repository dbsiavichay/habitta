from django.contrib.auth.mixins import LoginRequiredMixin


class OwnerQuerysetMixin(LoginRequiredMixin):
    """Restringe la vista a objetos del usuario autenticado.

    El filtro se aplica al queryset *antes* de procesar la petición, así que
    un objeto ajeno responde 404 tanto en GET como en POST. Los superusuarios
    pueden acceder a todo.
    """
    owner_field = 'user'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(**{self.owner_field: self.request.user})
