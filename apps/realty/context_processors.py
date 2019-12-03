from .forms import FinderForm
from apps.project.utils import get_active_icons_url

def search_bar(request):
	form = FinderForm()
	return {
		'search_form': form,
		'icons_url': get_active_icons_url(),
	}