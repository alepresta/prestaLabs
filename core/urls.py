# Core URLs for PrestaLabs
from django.urls import path

from .views_app import (
    analisis_dominio_view,
    dominios_guardados_view,
    exportar_dominio_individual,
    urls_guardadas_view,
    analisis_detalle,
    documentacion_view,
    configuracion_view,
    reportes_view,
    analisis_url_view,
    soporte_view,
    nuevo_reporte_view,
)

# Import user views from separated module
from .views.user_views import (
    listar_usuarios_view,
    nuevo_usuario_view,
    editar_usuarios_view,
    admin_set_password_view,
)

# Import crawling views from separated module
from .views.crawling_views import (
    api_status,
    index,
    detener_crawling_ajax as crawling_detener_ajax,
    iniciar_crawling_multiple_ajax as crawling_multiple_ajax,
    limpiar_procesos_fantasma_ajax as crawling_limpiar_fantasma,
    listar_crawlings_activos_ajax as crawling_listar_activos,
    progreso_crawling_ajax as crawling_progreso_ajax,
    iniciar_crawling_ajax as crawling_iniciar_ajax,
    verificar_crawling_activo as crawling_verificar_activo,
)
from core.views.analisis_estado import analisis_estado
from core.views.test_views import test_session_recovery

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
    path("dominios/guardados/", dominios_guardados_view, name="dominios_guardados"),
    path(
        "dominios/guardados/<int:dominio_id>/exportar/<str:formato>/",
        exportar_dominio_individual,
        name="exportar_dominio_individual",
    ),
    path("urls/guardadas/", urls_guardadas_view, name="urls_guardadas"),
    path("analisis/detalle/", analisis_detalle, name="analisis_detalle"),
    path("analisis/url/", analisis_url_view, name="analisis_url"),
    path("documentacion/", documentacion_view, name="documentacion"),
    path("configuracion/", configuracion_view, name="configuracion"),
    path("reportes/", reportes_view, name="reportes"),
    path("usuarios/", listar_usuarios_view, name="listar_usuarios"),
    path("usuarios/editar/", editar_usuarios_view, name="editar_usuarios"),
    path("soporte/", soporte_view, name="soporte"),
    path("usuarios/nuevo/", nuevo_usuario_view, name="nuevo_usuario"),
    path("reportes/nuevo/", nuevo_reporte_view, name="nuevo_reporte"),
    path(
        "usuarios/<int:user_id>/cambiar_password/",
        admin_set_password_view,
        name="admin_set_password",
    ),
    path("crawling/iniciar/", crawling_iniciar_ajax, name="iniciar_crawling_ajax"),
    path(
        "crawling/multiple/iniciar/",
        crawling_multiple_ajax,
        name="iniciar_crawling_multiple_ajax",
    ),
    path("crawling/progreso/", crawling_progreso_ajax, name="progreso_crawling_ajax"),
    path(
        "crawling/activo/", crawling_verificar_activo, name="verificar_crawling_activo"
    ),
    path(
        "crawling/activos/listar/",
        crawling_listar_activos,
        name="listar_crawlings_activos_ajax",
    ),
    path("crawling/detener/", crawling_detener_ajax, name="detener_crawling_ajax"),
    path(
        "crawling/limpiar/",
        crawling_limpiar_fantasma,
        name="limpiar_procesos_fantasma_ajax",
    ),
    path("analisis/estado/", analisis_estado, name="analisis_estado"),
    path("test/session-recovery/", test_session_recovery, name="test_session_recovery"),
    # path("analisis/historial/", historial_busquedas, name="historial_busquedas"),
]
