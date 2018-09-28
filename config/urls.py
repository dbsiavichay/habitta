"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static
from django.views.generic import TemplateView
from realty.views import HomeView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('api/', include('api.urls')),
    path('authentication/', include('authentication.urls')),
    path('comments/', include('comments.urls')),
    path('realty/', include('realty.urls')),
    path('logs/', include('logs.urls')),
    path('legal/terms/', TemplateView.as_view(template_name='terms_and_conditions.html'), name='terms'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
