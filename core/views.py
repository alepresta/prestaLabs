"""
Nuevo views.py principal que importa desde la estructura modular.

Este archivo mantiene compatibilidad mientras migramos gradualmente
todas las vistas desde views_app.py a la nueva estructura organizada.
"""

# Dashboard y análisis  
# (Imports disponibles para uso futuro)

# Crawling y análisis de dominios
from .views.crawling_views import (
    analisis_dominio_view,
    iniciar_crawling_ajax,
    progreso_crawling_ajax,
    api_status,
)

# Gestión de usuarios
from .views.user_views import (
    admin_set_password_view,
    listar_usuarios_view,
    perfil_usuario_view,
    cambiar_password_view,
)

# Servicios (disponibles para importación)
from .services.crawling_service import (
    CrawlingService,
    SitemapService,
    AnalysisService,
)

# Utilidades (disponibles para importación)
from .utils.web_utils import (
    get_random_headers,
    detect_blocking,
    normalizar_dominio,
    normalizar_url_individual,
)
