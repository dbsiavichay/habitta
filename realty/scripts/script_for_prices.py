from realty.models import Property

props = Property.objects.all()
for p in props:
	p.details['specifications'].update({
		'49': str(p.price),
		'50':'Si' if p.negotiable else 'No'
	})
	p.save()