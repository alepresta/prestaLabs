"""
Funciones de utilidad para analizar patrones de bloqueo y dar recomendaciones
"""


def get_domain_recommendations(dominio, crawl_result):
    """
    Genera recomendaciones específicas basadas en el resultado del crawling
    """
    recommendations = []

    if isinstance(crawl_result, dict):
        status = crawl_result.get("status", "")
        blocked_count = crawl_result.get("blocked_count", 0)
        urls_found = len(crawl_result.get("urls", []))

        # Dominios completamente bloqueados
        if status == "blocked_no_sitemap" and urls_found == 0:
            recommendations.extend(
                [
                    f"🛡️ {dominio} tiene protección anti-bot muy agresiva",
                    "💡 Esto es normal para sitios comerciales grandes (Udemy, Netflix, Amazon, etc.)",
                    "🔍 Alternativas: API oficial del sitio o web scraping con Selenium + proxies",
                    "📊 Para análisis SEO básico: usar herramientas como Screaming Frog o Sitebulb",
                ]
            )

        # Timeouts pero posible sitemap
        elif "timeout" in status:
            recommendations.extend(
                [
                    f"⏰ {dominio} tiene problemas de conectividad",
                    "🌍 Podría ser restricción geográfica o servidor lento",
                    "💡 Intentar en diferentes horarios o usar VPN",
                    "🔧 Aumentar timeout en configuración avanzada",
                ]
            )

        # Bloqueos parciales
        elif blocked_count > 0 and urls_found > 0:
            recommendations.extend(
                [
                    f"⚠️ {dominio} tiene protección moderada",
                    "🕐 Usar delays más largos entre requests (5-10 segundos)",
                    "🔄 Limitar URLs simultáneas a 10-20 por sesión",
                    "🤖 Evitar patrones de crawling muy regulares",
                ]
            )

        # Éxito con advertencias
        elif blocked_count > 0:
            recommendations.extend(
                [
                    f"✅ {dominio} crawleado exitosamente con {blocked_count} advertencias",
                    "🔧 Considerar usar delays más largos para evitar futuras restricciones",
                    "📊 El sitio puede implementar rate limiting en el futuro",
                ]
            )

    return recommendations


def get_blocked_domains_stats():
    """
    Analiza estadísticas de dominios bloqueados para mostrar en dashboard
    """
    from .models import BusquedaDominio
    from django.utils import timezone
    from datetime import timedelta

    # Búsquedas de las últimas 24 horas
    last_24h = timezone.now() - timedelta(hours=24)
    recent_searches = BusquedaDominio.objects.filter(fecha__gte=last_24h)

    stats = {
        "total_searches": recent_searches.count(),
        "blocked_domains": 0,
        "successful_domains": 0,
        "timeout_domains": 0,
        "common_blocked": [],
    }

    # Análisis por dominio
    domain_results = {}

    for search in recent_searches:
        domain = search.dominio
        url_count = len(search.get_urls())

        if domain not in domain_results:
            domain_results[domain] = {"searches": 0, "total_urls": 0}

        domain_results[domain]["searches"] += 1
        domain_results[domain]["total_urls"] += url_count

        # Clasificar resultado
        if url_count == 0:
            if "udemy" in domain.lower() or "netflix" in domain.lower():
                stats["blocked_domains"] += 1
            else:
                stats["timeout_domains"] += 1
        else:
            stats["successful_domains"] += 1

    # Dominios más comúnmente bloqueados
    blocked_domains = [
        domain
        for domain, data in domain_results.items()
        if data["total_urls"] == 0 and data["searches"] >= 2
    ]

    stats["common_blocked"] = blocked_domains[:5]  # Top 5

    return stats
