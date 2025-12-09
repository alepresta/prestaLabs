from django.urls import path
from .views import index, api_status, crear_usuario_lectura, editar_usuarios

urlpatterns = [
    path('', index, name='index'),
    path('status/', api_status, name='api_status'),
    path('usuarios/crear/', crear_usuario_lectura, name='crear_usuario_lectura'),
    path('usuarios/editar/', editar_usuarios, name='editar_usuarios'),
]
