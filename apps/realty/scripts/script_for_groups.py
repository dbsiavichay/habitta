from realty.models import Category, Group, GroupCategory

g = Group.objects.get(pk=1)

cats = Category.objects.filter(kind=1)

for cat in cats:
	kwargs = {
		'group': g,
		'category': cat,
		'sequence': 1
	}
	GroupCategory.objects.create(**kwargs)