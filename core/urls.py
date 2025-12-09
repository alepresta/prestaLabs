from django.urls import path
from .views import index, api_status

urlpatterns = [
    path('', index, name='index'),
    path('status/', api_status, name='api_status'),
]
