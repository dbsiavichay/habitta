from realty.models import Service, Specification

services = Service.objects.all()

for s in services:
	kwargs = {
		'name': s.name,
		'icon': s.icon,
		'internal_name': s.name,
		'field_type': 'BooleanField',
	}

	sp = Specification.objects.create(**kwargs)