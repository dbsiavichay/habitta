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
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', include('apps.project.urls')),
    path('authentication/', include('apps.authentication.urls')),
    path('messenger/', include('apps.messenger.urls')),
    path('realty/', include('apps.realty.urls')),
    path('auctions/', include('apps.auctions.urls')),
    path('multimedia/', include('apps.multimedia.urls')),
    path('logs/', include('apps.logs.urls')),
    path('payments/', include('apps.payments.urls')),
    path('manual/', include('apps.manual.urls')),
]

# En producción los archivos de media deben servirse desde nginx o un storage externo.
if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
