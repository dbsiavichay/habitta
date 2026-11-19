from django.shortcuts import redirect
from django.http import Http404
from django.views.generic import ListView, CreateView, DeleteView
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
	http_method_names = ['post']

	def get_queryset(self):
		return super().get_queryset().filter(user=self.request.user)

	def form_valid(self, form):
		success_url = self.object.get_object_url()
		self.object.delete()
		return redirect(success_url)
