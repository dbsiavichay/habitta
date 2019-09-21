from .forms import GroupDetailsForm

RENDERES = {
	'property-details': 'get_property_details'
}


def render_component(component):
	callback = eval(RENDERES[component])
	return callback()

def get_property_details(**kwargs):
	forms = []
	pk_category = kwargs.get('category')
	groups = _get_groups(_get_category(pk_category))	
	for group in groups:
		forms.append(self.get_form(group))
	r = render_to_string('components/realty/publication_details.html', context={'forms':forms})
	

_get_category = lambda pk: get_object_or_404(Category, pk=pk)
_get_groups = lambda category: category.groups.all().order_by('groupcategory__sequence')