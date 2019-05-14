from .models import Settings

class ProjectMixin(object):	
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		try:
			project = Settings.objects.get(is_active=True)
			context.update({'project': project})
		except Settings.DoesNotExist:
			pass
		return context
