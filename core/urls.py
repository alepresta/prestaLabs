# Eliminado bloque incorrecto y duplicado
from django.urls import path
from .views_app import (
    index,
    api_status,
    analisis_dominio_view,
    analisis_detalle,
    documentacion_view,
    configuracion_view,
    reportes_view,
    analisis_url_view,
    editar_usuarios_view,
    soporte_view,
    nuevo_usuario_view,
    nuevo_reporte_view,
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
    path("analisis/dominio/", analisis_dominio_view, name="analisis_dominio"),
    path("analisis/detalle/", analisis_detalle, name="analisis_detalle"),
    path("analisis/url/", analisis_url_view, name="analisis_url"),
    path("documentacion/", documentacion_view, name="documentacion"),
    path("configuracion/", configuracion_view, name="configuracion"),
    path("reportes/", reportes_view, name="reportes"),
    path("usuarios/editar/", editar_usuarios_view, name="editar_usuarios"),
    path("soporte/", soporte_view, name="soporte"),
    path("usuarios/nuevo/", nuevo_usuario_view, name="nuevo_usuario"),
    path("reportes/nuevo/", nuevo_reporte_view, name="nuevo_reporte"),
    # path("analisis/historial/", historial_busquedas, name="historial_busquedas"),
]
