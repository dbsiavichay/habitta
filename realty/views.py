from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from .models import Property

class PropertyCreateView(CreateView):
	model = Property
	fields = '__all__'
	success_url = reverse_lazy('home')	
