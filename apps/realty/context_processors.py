from .forms import FinderForm

def search_bar(request):
	form = FinderForm()
	return {
		'search_form': form,		
	}