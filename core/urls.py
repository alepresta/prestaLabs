from django.urls import path
from .views_app import (
    index,
    api_status,
    analisis_dominio,
    analisis_detalle,
)

urlpatterns = [
    path("", index, name="index"),
    path("status/", api_status, name="api_status"),
    # path(
    #     "usuarios/crear/",
    #     CrearUsuarioLecturaView.as_view(),
    #     name="crear_usuario_lectura",
    # ),
    # path(
    #     "usuarios/editar/",
    #     EditarUsuariosView.as_view(),
    #     name="editar_usuarios",
    # ),
    # path(
    #     "usuarios/",
    #     ListarUsuariosView.as_view(),
    #     name="listar_usuarios",
    # ),
    # path(
    #     "usuarios/exportar/",
    #     ExportarUsuariosView.as_view(),
    #     name="exportar_usuarios",
    # ),
    path("dashboard/", index, name="dashboard"),
    path("analisis/dominio/", analisis_dominio, name="analisis_dominio"),
    path("analisis/detalle/", analisis_detalle, name="analisis_detalle"),
    # path("analisis/historial/", historial_busquedas, name="historial_busquedas"),
]
