from django.urls import path

from .views import ManualChapterView, ManualHubView, ManualIndexView

urlpatterns = [
    path('', ManualHubView.as_view(), name='manual'),
    path('<slug:manual>/', ManualIndexView.as_view(), name='manual_index'),
    path('<slug:manual>/<slug:chapter>/', ManualChapterView.as_view(), name='manual_chapter'),
]
