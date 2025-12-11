#!/usr/bin/env python
"""
Script para probar mensajes de análisis de dominio
"""

import os
import sys
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prestaLabs.settings")
django.setup()


def test_message_generation():
    """Prueba la generación de mensajes"""
    from core.views_app import crawl_urls
    from core.recommendations import get_domain_recommendations
    from django.utils.safestring import mark_safe

    print("🧪 Probando generación de mensajes para dominios bloqueados")
    print("=" * 60)

    # Simular resultado de udemy.com
    result = {
        "urls": [],
        "status": "blocked_no_sitemap",
        "message": "Crawling bloqueado y no hay sitemap disponible. Motivo: HTTP 403: Acceso bloqueado por el servidor",
        "blocked_count": 1,
        "sitemap_urls": 0,
    }

    dominio = "udemy.com"
    urls_encontradas = []
    crawl_status = "blocked_no_sitemap"
    blocked_count = 1

    # Generar mensaje según nuestro código
    from core.recommendations import get_domain_recommendations
    from django.utils.safestring import mark_safe

    base_msg = (
        f"Dominio '{dominio}' analizado: {len(urls_encontradas)} URLs encontradas."
    )
    recommendations = get_domain_recommendations(dominio, result)

    # Determinar clase CSS según el resultado
    message_class = "blocked"
    if "no_sitemap" in crawl_status:
        # Mensaje más específico para dominios totalmente bloqueados
        if len(urls_encontradas) == 0 and blocked_count > 0:
            mensaje = (
                f"{base_msg} 🛡️ Dominio completamente protegido - "
                f"bloquea tanto crawling como sitemap. Esto es normal para sitios como Udemy, Netflix, etc."
            )
            message_class = "blocked"
        else:
            mensaje = f"{base_msg} ❌ Crawling falló y no hay sitemap disponible."
            message_class = "warning"

    # Generar HTML para recomendaciones si existen
    if recommendations:
        recommendations_html = f"""
        <div class="domain-recommendations domain-{message_class}">
            <div class="recommendation-title">
                <i class="bi bi-lightbulb-fill recommendation-icon"></i>
                Recomendaciones para {dominio}
            </div>
        """

        for rec in recommendations:
            recommendations_html += f"""
            <div class="recommendation-item">
                <span class="recommendation-icon">{rec[:2]}</span>
                <span>{rec[2:]}</span>
            </div>
            """

        recommendations_html += "</div>"
        mensaje_final = mark_safe(
            f'<div class="crawl-message {message_class}">{mensaje}</div>{recommendations_html}'
        )
    else:
        mensaje_final = mark_safe(
            f'<div class="crawl-message {message_class}">{mensaje}</div>'
        )

    print("📝 Mensaje generado:")
    print(mensaje_final)
    print("\n📊 Recomendaciones encontradas:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")

    print(
        f"\n✅ Mensaje HTML generado correctamente con {len(recommendations)} recomendaciones"
    )
    print("🔍 Este mensaje debería aparecer cuando se haga POST al formulario")


if __name__ == "__main__":
    test_message_generation()
