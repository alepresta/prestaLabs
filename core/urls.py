from django.urls import path
from .views import (
    index,
    api_status,
    dashboard_redirect,
    CrearUsuarioLecturaView,
    EditarUsuariosView,
    ListarUsuariosView,
    ExportarUsuariosView,
    AnalisisDominioView,
    AnalisisUrlView,
)

urlpatterns = [
    path("", index, name="index"),
    path("status/", api_status, name="api_status"),
    path(
        "usuarios/crear/",
        CrearUsuarioLecturaView.as_view(),
        name="crear_usuario_lectura",
    ),
    path(
        "usuarios/editar/",
        EditarUsuariosView.as_view(),
        name="editar_usuarios",
    ),
    path(
        "usuarios/",
        ListarUsuariosView.as_view(),
        name="listar_usuarios",
    ),
    path(
        "usuarios/exportar/",
        ExportarUsuariosView.as_view(),
        name="exportar_usuarios",
    ),
    path("dashboard/", dashboard_redirect, name="dashboard"),
    path("analisis/dominio/", AnalisisDominioView.as_view(), name="analisis_dominio"),
    path("analisis/url/", AnalisisUrlView.as_view(), name="analisis_url"),
]
