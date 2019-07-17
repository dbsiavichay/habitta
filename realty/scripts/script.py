from services.models import Activity
from realty.models import Category

Category.objects.filter(kind=2).delete()

acts = Activity.objects.all()

for a in acts:
	kwargs = {
		'kind': 2,
		'name': a.name,
		'singular_name': a.name,
		'order':1,
	}
	c = Category.objects.create(**kwargs)
	c.purposes.add(8)
