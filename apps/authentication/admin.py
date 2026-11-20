from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from apps.project.admin_utils import short_date, user_header
from apps.project.templatetags.habitta import SOCIAL_ICONS

from .models import Profile, SocialNetwork, SocialProfile

# El título y la marca del admin los da UNFOLD (config/unfold.py).

# User y Group vienen registrados por django.contrib.auth con el admin de serie: se vuelven a
# registrar con los formularios de Unfold. El perfil (teléfono y foto) y los inicios de sesión con
# redes sociales se ven dentro del usuario; las redes de su perfil público las edita cada usuario.
admin.site.unregister(User)
admin.site.unregister(Group)

ROLE_LABEL = {'Superusuario': 'danger', 'Staff': 'primary'}


class ProfileInline(StackedInline):
	model = Profile
	fields = ('phone', 'image')
	can_delete = False
	verbose_name = 'perfil'
	verbose_name_plural = 'Perfil'


class SocialProfileInline(TabularInline):
	model = SocialProfile
	fields = ('provider', 'identifier')
	readonly_fields = fields
	extra = 0
	can_delete = False
	tab = True
	show_title = False  # sin la fila "SocialProfile object (n)"
	verbose_name = 'inicio de sesión social'
	verbose_name_plural = 'Redes con las que inicia sesión'

	def has_add_permission(self, request, obj=None):
		return False


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
	form = UserChangeForm
	add_form = UserCreationForm
	change_password_form = AdminPasswordChangeForm
	list_display = ('person', 'role', 'is_active', 'joined', 'last_seen', 'listings')
	list_select_related = ('profile',)
	list_filter = ('is_staff', 'is_superuser', 'is_active', ('date_joined', RangeDateFilter), 'groups')
	list_filter_submit = True
	ordering = ('-date_joined',)

	def get_inlines(self, request, obj):
		# Al crear, el perfil lo hace la señal de post_save: el inline sólo se muestra al editar.
		return [ProfileInline, SocialProfileInline] if obj else []

	def get_queryset(self, request):
		return super().get_queryset(request).annotate(listings_count=Count('property', distinct=True))

	@display(description='Usuario', header=True, ordering='first_name')
	def person(self, obj):
		return user_header(obj)

	@display(description='Rol', label=ROLE_LABEL)
	def role(self, obj):
		if obj.is_superuser:
			return 'Superusuario'
		return 'Staff' if obj.is_staff else 'Usuario'

	@display(description='Alta', ordering='date_joined')
	def joined(self, obj):
		return short_date(obj.date_joined)

	@display(description='Último acceso', ordering='last_login', empty_value='Nunca')
	def last_seen(self, obj):
		return short_date(obj.last_login) if obj.last_login else None

	@display(description='Publicaciones', ordering='listings_count')
	def listings(self, obj):
		return obj.listings_count


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
	pass


@admin.register(SocialNetwork)
class SocialNetworkAdmin(ModelAdmin):
	list_display = ('name', 'icon', 'url')
	search_fields = ('name',)
	fields = ('name', 'icon', 'url')

	def get_form(self, request, obj=None, **kwargs):
		kwargs['help_texts'] = {
			'icon': 'Uno de: %s. Con otro nombre se muestra un globo.' % ', '.join(sorted(SOCIAL_ICONS)),
			'url': 'Dirección base del perfil; se le agrega el usuario. Ejemplo: https://www.instagram.com/',
		}
		return super().get_form(request, obj, **kwargs)
