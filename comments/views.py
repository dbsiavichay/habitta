from django.shortcuts import render, redirect
from django.http import Http404
from django.views.generic import CreateView, DeleteView
from .models import Comment
from .forms import CommentForm

class CommentCreateView(CreateView):	
	model = Comment
	form_class = CommentForm

	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.user = self.request.user
		self.object.save()
		
		return redirect(self.object.get_object_url())

	def get(self, request, *args, **kwargs):
		raise Http404

class CommentDeleteView(DeleteView):	
	model = Comment	

	def delete(self, request, *args, **kwargs):	    
	    self.object = self.get_object()
	    self.object.delete()

	    return redirect(self.object.get_object_url())
