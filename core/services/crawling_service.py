"""
Servicios de crawling y análisis de sitios web.

Contiene toda la lógica de negocio relacionada con:
- Crawling de sitios web
- Análisis de URLs
- Manejo de sitemaps
- Gestión del progreso de crawling
"""

import json
import time
import random
from urllib.parse import urljoin, urlparse
from defusedxml.ElementTree import fromstring as ET_fromstring
import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from ..models import BusquedaDominio, CrawlingProgress
from ..utils.web_utils import get_random_headers, detect_blocking


# Variable global temporal para progreso (en producción usar cache/db)
crawling_progress = {}


class CrawlingService:
    """Servicio para manejo del crawling de sitios web"""

    @staticmethod
    def limpiar_procesos_colgados():
        """Limpia procesos de crawling que han quedado colgados"""

        # Buscar procesos que no han sido actualizados en más de 10 minutos
        hace_10min = timezone.now() - timezone.timedelta(minutes=10)

        procesos_colgados = CrawlingProgress.objects.filter(
            is_done=False, updated_at__lt=hace_10min
        )

        for proceso in procesos_colgados:
            # Marcar como terminado
            proceso.is_done = True
            proceso.save()

            # Actualizar también el BusquedaDominio correspondiente si existe
            if proceso.busqueda_id:
                try:
                    busqueda = BusquedaDominio.objects.get(id=proceso.busqueda_id)
                    if not busqueda.fecha_fin:
                        busqueda.fecha_fin = timezone.now()
                        busqueda.save()
                except BusquedaDominio.DoesNotExist:
                    pass

    @staticmethod
    def sincronizar_estados_crawling():
        """Sincroniza el estado de crawling entre el progreso temporal y la BD"""

        # Obtener todos los procesos de crawling activos de la BD
        procesos_activos = CrawlingProgress.objects.filter(is_done=False)

        for proceso in procesos_activos:
            progress_key = f"crawl_{proceso.busqueda_id}"

            # Si existe en memoria temporal, actualizar BD
            if progress_key in crawling_progress:
                progreso_memoria = crawling_progress[progress_key]

                # Actualizar progreso en BD
                proceso.urls_encontradas = progreso_memoria.get("urls_encontradas", 0)
                proceso.urls_procesadas = progreso_memoria.get("urls_procesadas", 0)
                proceso.errores = progreso_memoria.get("errores", 0)
                proceso.is_done = progreso_memoria.get("completed", False)
                proceso.mensaje_estado = progreso_memoria.get("status", "")
                proceso.save()

                # Si está completo, limpiar de memoria
                if proceso.is_done:
                    del crawling_progress[progress_key]

            # Si no existe en memoria pero está activo en BD, marcarlo como terminado
            elif not proceso.is_done:
                proceso.is_done = True
                proceso.mensaje_estado = (
                    "Proceso interrumpido - no encontrado en memoria"
                )
                proceso.save()

    @staticmethod
    def verificar_crawling_activo(busqueda_id=None):
        """Verifica si hay crawling activo"""

        if busqueda_id:
            # Verificar por ID específico
            return CrawlingProgress.objects.filter(
                busqueda_id=busqueda_id, is_done=False
            ).exists()
        else:
            # Verificar cualquier crawling activo
            return CrawlingProgress.objects.filter(is_done=False).exists()


class SitemapService:
    """Servicio para manejo de sitemaps"""

    @staticmethod
    def try_sitemap_fallback(domain):
        """Intenta obtener URLs del sitemap como fallback"""

        sitemap_urls = [
            f"https://{domain}/sitemap.xml",
            f"http://{domain}/sitemap.xml",
            f"https://{domain}/sitemap_index.xml",
            f"http://{domain}/sitemap_index.xml",
            f"https://{domain}/sitemaps.xml",
            f"http://{domain}/sitemaps.xml",
        ]

        for sitemap_url in sitemap_urls:
            try:
                response = requests.get(
                    sitemap_url, timeout=10, headers=get_random_headers()
                )
                if response.status_code == 200:
                    urls = SitemapService.parse_sitemap_urls(response.content, domain)
                    if urls:
                        return urls
            except Exception:
                continue

        return []

    @staticmethod
    def parse_sitemap_urls(content, base_domain, max_urls=100):
        """Parsea URLs de un sitemap XML"""

        urls = []
        try:
            # Intentar parsear como XML
            root = ET_fromstring(content)

            # Manejar namespaces comunes de sitemaps
            namespaces = {
                "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
                "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
            }

            # Buscar elementos <url> con namespace
            for url_elem in root.findall(".//sm:url", namespaces):
                loc_elem = url_elem.find("sm:loc", namespaces)
                if loc_elem is not None:
                    url = loc_elem.text
                    if url and base_domain.lower() in url.lower():
                        urls.append(url)
                        if len(urls) >= max_urls:
                            break

            # Si no encontró con namespace, intentar sin namespace
            if not urls:
                for url_elem in root.findall(".//url"):
                    loc_elem = url_elem.find("loc")
                    if loc_elem is not None:
                        url = loc_elem.text
                        if url and base_domain.lower() in url.lower():
                            urls.append(url)
                            if len(urls) >= max_urls:
                                break

        except Exception:
            # Si falla el parsing XML, intentar extraer URLs con regex
            try:
                import re

                pattern = r"<loc[^>]*>(.*?)</loc>"
                matches = re.findall(pattern, content.decode("utf-8", errors="ignore"))

                for match in matches:
                    if base_domain.lower() in match.lower():
                        urls.append(match.strip())
                        if len(urls) >= max_urls:
                            break
            except Exception:
                pass

        return urls[:max_urls]


class AnalysisService:
    """Servicio para análisis de sitios web"""

    @staticmethod
    def guardar_busqueda_ajax(dominio, urls, user=None):
        """Guarda una búsqueda de dominio con sus URLs"""

        busqueda = BusquedaDominio(dominio=dominio, usuario=user, fecha=timezone.now())
        busqueda.save()

        # Guardar URLs como JSON en el campo correspondiente
        busqueda.urls = json.dumps(urls) if urls else "[]"
        busqueda.save()

        return busqueda

    @staticmethod
    def crawl_urls_progress(base_url, max_urls, progress_key):
        """Ejecuta el crawling con seguimiento de progreso"""

        # Inicializar progreso
        crawling_progress[progress_key] = {
            "urls_encontradas": 0,
            "urls_procesadas": 0,
            "errores": 0,
            "completed": False,
            "status": "Iniciando crawling...",
        }

        try:
            # Normalizar la URL base
            if not base_url.startswith(("http://", "https://")):
                base_url = "https://" + base_url

            parsed_base = urlparse(base_url)
            domain = parsed_base.netloc

            # Set para URLs únicas
            urls_encontradas = set()
            urls_procesadas = set()
            urls_a_procesar = [base_url]

            # Headers para parecer más humano
            headers = get_random_headers()

            # Actualizar estado
            crawling_progress[progress_key]["status"] = f"Analizando {domain}..."

            while urls_a_procesar and len(urls_encontradas) < max_urls:
                current_url = urls_a_procesar.pop(0)

                if current_url in urls_procesadas:
                    continue

                try:
                    # Delay aleatorio entre requests
                    time.sleep(random.uniform(0.5, 2.0))

                    response = requests.get(current_url, timeout=10, headers=headers)

                    # Verificar si estamos siendo bloqueados
                    if detect_blocking(response, current_url):
                        crawling_progress[progress_key][
                            "status"
                        ] = "Detectado bloqueo, usando sitemap..."
                        sitemap_urls = SitemapService.try_sitemap_fallback(domain)
                        if sitemap_urls:
                            urls_encontradas.update(sitemap_urls[:max_urls])
                        break

                    urls_procesadas.add(current_url)
                    urls_encontradas.add(current_url)

                    # Actualizar progreso
                    crawling_progress[progress_key].update(
                        {
                            "urls_encontradas": len(urls_encontradas),
                            "urls_procesadas": len(urls_procesadas),
                            "status": f"Procesando: {current_url[:50]}...",
                        }
                    )

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, "html.parser")

                        # Buscar enlaces
                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            full_url = urljoin(current_url, href)
                            parsed_url = urlparse(full_url)

                            # Solo URLs del mismo dominio
                            if (
                                parsed_url.netloc == domain
                                and full_url not in urls_procesadas
                            ):
                                if len(urls_encontradas) < max_urls:
                                    urls_a_procesar.append(full_url)
                                    urls_encontradas.add(full_url)
                                else:
                                    break

except Exception:
                    crawling_progress[progress_key]["errores"] += 1

            # Finalizar
            crawling_progress[progress_key].update(
                {
                    "completed": True,
                    "status": f"Completado: {len(urls_encontradas)} URLs encontradas",
                }
            )

            return list(urls_encontradas)

        except Exception as e:
            crawling_progress[progress_key].update(
                {
                    "completed": True,
                    "status": f"Error: {str(e)}",
                    "errores": crawling_progress[progress_key]["errores"] + 1,
                }
            )
            return []
