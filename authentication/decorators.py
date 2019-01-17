from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.http import Http404

def owner_required(function):
	def get_attr(instance, attrs):
		attrs = attrs.split('.')
		attr = attrs.pop(0)

		if len(attrs) == 0:		
			return getattr(instance, attr)						
	 
		return get_attr(getattr(instance, attr), '.'.join(attrs))

	def wrapper(request, *args, **kwargs):	
		if not request.user.is_authenticated:
			url = '%s?next=%s' % (reverse_lazy('login'), request.path)    		
			return redirect(url)        
		
		## Revisar en el POST si se verifica la propiedad del objeto
		response = function(request, *args, **kwargs)
		if response.__class__.__name__ == 'HttpResponseRedirect':
			return response

		###
		
		if not 'object' in response.context_data:
			return response

		obj = response.context_data.get('object')
		models = {
			'Property': 'user',
			'Service': 'user',			
		}
				
		if not obj.__class__.__name__ in models:
			return response

		owner = get_attr(obj, models[obj.__class__.__name__])
		if owner == request.user || request.user.is_superuser:
			return response

		raise Http404

	return wrapper