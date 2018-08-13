from django import forms
from .models import Comment

class CommentForm(forms.ModelForm):
	class Meta:
		model = Comment
		exclude = ('date','user')
		widgets = {
			'object_id': forms.HiddenInput,
			'contenttype':forms.HiddenInput,			
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['content'].widget.attrs.update({'placeholder':'Tú comentario'})
	