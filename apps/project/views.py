from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import DatabaseError, connection
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.generic import ListView, TemplateView

from apps.auctions.models import Auction
from apps.realty.models import Category, Property, Purpose
from apps.realty.search import search_data

from .mixins import ProjectMixin
from .models import Help, Term


class HomeView(ProjectMixin, TemplateView):
	template_name = 'index.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		properties = Property.objects.select_related('category', 'user__profile')
		context.update({
			'properties': properties[:12],
			'list_purposes': self.get_list_by_purposes(),
			'auctions': self.get_auctions_properties(),
			'stats': self.get_stats(),
			'kinds': self.get_kinds(),
			'popular_categories': self.get_popular_categories(),
			'hero_properties': self.get_hero_properties(properties),
			'search_data': search_data(),
		})
		return context

	def get_list_by_purposes(self):
		result = []
		for purpose in Purpose.objects.all():
			properties = Property.objects.filter(details__purpose=purpose.id).select_related('category', 'user__profile')[:10]
			if len(properties): result.append((purpose, properties))
		return result

	def get_auctions_properties(self):
		Auction.objects.filter(ending_date__lte=timezone.now()+timedelta(minutes=1), stage=Auction.OPEN).update(stage=Auction.CLOSED)
		queryset = Property.objects.filter(auction__stage=Auction.OPEN).select_related('category', 'user__profile')
		return queryset

	def get_stats(self):
		"""Cifras reales del sitio (antes eran números fijos en la plantilla)."""
		return {
			'properties': Property.objects.count(),
			'advertisers': User.objects.filter(property__isnull=False).distinct().count(),
			'categories': Category.objects.filter(enabled=True).count(),
			'users': User.objects.filter(is_active=True).count(),
		}

	def get_kinds(self):
		"""Tarjetas de los tres tipos de anuncio con su número de publicaciones."""
		totals = dict(
			Property.objects.order_by().values('category__kind').annotate(total=Count('id')).values_list('category__kind', 'total')
		)
		meta = {
			Category.REAL_STATE: ('Inmuebles', 'house', 'Casas, departamentos, terrenos, locales y alojamiento.'),
			Category.SERVICE: ('Servicios', 'wrench', 'Profesionales y técnicos de confianza cerca de ti.'),
			Category.JOB: ('Empleos', 'briefcase-business', 'Ofertas de trabajo y talento disponible en tu ciudad.'),
		}
		return [
			{'kind': kind, 'label': label, 'icon': icon, 'description': description, 'total': totals.get(kind, 0)}
			for kind, (label, icon, description) in meta.items()
		]

	def get_popular_categories(self):
		return (
			Category.objects.filter(enabled=True)
			.annotate(total=Count('property'))
			.filter(total__gt=0)
			.order_by('-total', 'name')[:10]
		)

	def get_hero_properties(self, properties):
		"""Hasta 3 anuncios recientes con portada para el collage del hero."""
		result = []
		for prop in properties[:30]:
			cover = prop.get_cover_instance()
			# Sólo portadas que existan de verdad (algunas imágenes antiguas faltan en media/)
			if cover and cover.img and cover.img.storage.exists(cover.img.name):
				result.append(prop)
			if len(result) == 3:
				break
		return result


class TermListView(ProjectMixin, ListView):
	model = Term
	template_name = 'project/terms.html'


class HelpListView(ProjectMixin, ListView):
	model = Help


@never_cache
@require_GET
def healthz(request):
	"""Lo consultan el HEALTHCHECK de la imagen y el deploy: 200 si hay base de datos, con el commit."""
	try:
		connection.ensure_connection()
	except DatabaseError:
		return JsonResponse({'status': 'error', 'sha': settings.APP_VERSION}, status=503)
	return JsonResponse({'status': 'ok', 'sha': settings.APP_VERSION})
