from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from .models import Property
from .forms import PropertyForm

class PropertyCreateView(CreateView):
	model = Property
	form_class = PropertyForm
	success_url = reverse_lazy('home')	
