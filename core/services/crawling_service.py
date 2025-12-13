"""
Servicio de crawling - Contiene toda la lógica de negocio para el crawling de sitios web.

Este servicio se encarga de:
- Crawling de URLs de un dominio
- Detección de bloqueos anti-bot
- Fallback a sitemaps cuando el crawling falla
- Gestión de delays y headers rotativos
- Parsing de sitemaps XML
"""

import time
import random
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from defusedxml.ElementTree import fromstring as ET_fromstring
from django.utils import timezone
from ..models import BusquedaDominio, CrawlingProgress
from ..utils.http_utils import get_random_headers
from ..utils.domain_utils import normalizar_dominio


class CrawlingService:
    """Servicio principal para operaciones de crawling"""
    
    def __init__(self):
        self.max_blocks = 3  # Máximo de bloqueos antes de cambiar estrategia
        self.crawl_delay = 1  # Delay inicial en segundos
    
    def crawl_urls(self, base_url, max_urls=None):
        """
        Función principal para crawlear URLs de un dominio.
        
        Args:
            base_url (str): URL base del sitio a crawlear
            max_urls (int, optional): Límite máximo de URLs a obtener
            
        Returns:
            dict: Resultado del crawling con URLs, status y metadatos
        """
        # Normalizar URL base
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"

        visited = set()
        to_visit = [base_url]
        urls = []
        domain = urlparse(base_url).netloc or base_url.replace("https://", "").replace("http://", "")
        blocked_count = 0

        print(f"[CRAWL] Iniciando crawling mejorado de {base_url}")
        print(f'[CRAWL] Límite de URLs: {max_urls or "Sin límite"}')

        # Verificar robots.txt para obtener delay recomendado
        self._check_robots_txt(domain)

        while to_visit and len(urls) < (max_urls or float("inf")):
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                # Aplicar delay inteligente
                if len(urls) > 0:  # No delay en la primera request
                    delay = self.crawl_delay * (1 + blocked_count * 0.5)
                    print(f"[CRAWL] Esperando {delay:.1f}s antes de la siguiente request...")
                    time.sleep(delay)

                # Request con headers aleatorios
                headers = get_random_headers()
                resp = requests.get(url, timeout=15, headers=headers)

                print(f"[CRAWL] {url} -> {resp.status_code}")

                # Detectar bloqueos
                is_blocked, block_reason = self.detect_blocking(resp, url)

                if is_blocked:
                    blocked_count += 1
                    print(f"[CRAWL] ⚠️ BLOQUEO DETECTADO: {block_reason}")

                    # Para HTTP 403/429 (acceso denegado), intentar sitemap inmediatamente
                    immediate_fallback = resp.status_code in [403, 429]
                    should_fallback = (blocked_count >= self.max_blocks) or (
                        immediate_fallback and len(urls) == 0
                    )

                    if should_fallback:
                        sitemap_urls = SitemapService().try_sitemap_fallback(domain)
                        if sitemap_urls:
                            print(f"[CRAWL] ✅ Sitemap encontrado con {len(sitemap_urls)} URLs")
                            urls.extend(
                                sitemap_urls[
                                    : (max_urls - len(urls) if max_urls else len(sitemap_urls))
                                ]
                            )
                            return {
                                "urls": urls,
                                "status": "blocked_fallback_sitemap",
                                "message": f"Acceso denegado por protección anti-bot. Se usó sitemap como alternativa ({len(sitemap_urls)} URLs).",
                                "blocked_count": blocked_count,
                                "sitemap_urls": len(sitemap_urls),
                            }
                        else:
                            return {
                                "urls": urls,
                                "status": "blocked_no_sitemap",
                                "message": f"Crawling bloqueado y no hay sitemap disponible. Motivo: {block_reason}",
                                "blocked_count": blocked_count,
                                "sitemap_urls": 0,
                            }

                    # Aumentar delay y continuar
                    self.crawl_delay *= 2
                    continue

                if resp.status_code != 200:
                    print(f"[CRAWL] Status no exitoso: {resp.status_code}")
                    continue

                soup = BeautifulSoup(resp.content, "html.parser")
                urls.append(url)
                print(f"[CRAWL] ✅ URL agregada. Total: {len(urls)}")

                if max_urls and len(urls) >= max_urls:
                    print(f"[CRAWL] 🎯 Límite alcanzado: {max_urls} URLs")
                    break

                # Extraer enlaces
                links_found = self._extract_links(soup, url, domain, visited, to_visit)
                print(f"[CRAWL] Enlaces internos encontrados: {links_found}")

            except requests.exceptions.Timeout:
                blocked_count += 1
                if self._handle_connection_error(blocked_count, urls, domain, "timeout"):
                    return self._handle_connection_error(blocked_count, urls, domain, "timeout")
                continue
            except requests.exceptions.ConnectionError:
                blocked_count += 1
                if self._handle_connection_error(blocked_count, urls, domain, "connection"):
                    return self._handle_connection_error(blocked_count, urls, domain, "connection")
                continue
            except Exception as e:
                print(f"[CRAWL] ❌ Error en {url}: {str(e)[:100]}")
                continue

        result = {
            "urls": urls,
            "status": "success",
            "message": f"Crawling completado exitosamente. {len(urls)} URLs encontradas.",
            "blocked_count": blocked_count,
            "total_visited": len(visited),
        }

        print(f"[CRAWL] 🏁 Finalizado: {len(urls)} URLs, {blocked_count} bloqueos")
        return result

    def detect_blocking(self, response, url):
        """
        Detecta si una respuesta indica bloqueo anti-bot.
        
        Args:
            response: Respuesta HTTP
            url: URL de la request
            
        Returns:
            tuple: (is_blocked: bool, reason: str)
        """
        status = response.status_code
        content = response.text.lower() if hasattr(response, "text") else ""

        # Códigos de estado que indican bloqueo
        if status in [403, 429, 503]:
            return True, f"HTTP {status}: Acceso bloqueado por el servidor"

        # Contenido que indica bloqueo
        blocking_keywords = [
            "blocked", "forbidden", "access denied", "cloudflare", "captcha",
            "robot", "bot detected", "rate limit", "too many requests", 
            "suspicious activity",
        ]

        if any(keyword in content for keyword in blocking_keywords):
            return True, "Contenido indica protección anti-bot"

        # Respuesta muy pequeña o vacía puede indicar bloqueo
        if len(content) < 100 and status == 200:
            return True, "Respuesta sospechosamente pequeña"

        return False, ""

    def _check_robots_txt(self, domain):
        """Verifica robots.txt para obtener delay recomendado"""
        try:
            robots_url = f"https://{domain}/robots.txt"
            robots_response = requests.get(robots_url, timeout=10, headers=get_random_headers())
            if robots_response.status_code == 200:
                for line in robots_response.text.split("\n"):
                    if line.lower().strip().startswith("crawl-delay:"):
                        try:
                            recommended_delay = int(line.split(":", 1)[1].strip())
                            self.crawl_delay = max(self.crawl_delay, recommended_delay)
                            print(f"[CRAWL] Delay recomendado por robots.txt: {self.crawl_delay}s")
                        except Exception:
                            pass
                    elif line.lower().strip().startswith("disallow: /"):
                        print("[CRAWL] ⚠️ robots.txt prohíbe el crawling completo")
        except Exception:
            pass

    def _extract_links(self, soup, current_url, domain, visited, to_visit):
        """Extrae enlaces de la página actual"""
        links_found = 0
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("#", "mailto:", "javascript:", "tel:", "ftp:")):
                continue

            abs_url = urljoin(current_url, href)
            parsed = urlparse(abs_url)

            # Normalizar dominio para comparación
            def normalize_domain(d):
                return d.lower().replace("www.", "")

            if parsed.netloc and normalize_domain(parsed.netloc) != normalize_domain(domain):
                continue

            if (
                abs_url not in visited
                and abs_url not in to_visit
                and abs_url.startswith("http")
                and len(to_visit) < 1000  # Evitar cola infinita
            ):
                to_visit.append(abs_url)
                links_found += 1

        return links_found

    def _handle_connection_error(self, blocked_count, urls, domain, error_type):
        """Maneja errores de conexión y timeout"""
        if blocked_count >= self.max_blocks and len(urls) == 0:
            print(f"[CRAWL] 🚨 Demasiados {error_type}s. Intentando sitemap...")
            sitemap_urls = SitemapService().try_sitemap_fallback(domain)
            
            status_map = {
                "timeout": "timeout_fallback_sitemap" if sitemap_urls else "timeout_no_sitemap",
                "connection": "connection_error_fallback_sitemap" if sitemap_urls else "connection_error_no_sitemap"
            }
            
            if sitemap_urls:
                urls.extend(sitemap_urls)
                
            return {
                "urls": urls,
                "status": status_map[error_type],
                "message": f'{error_type.title()}s repetidos. {"Se usó sitemap como alternativa." if sitemap_urls else "Sin sitemap disponible."}',
                "blocked_count": blocked_count,
                "sitemap_urls": len(sitemap_urls) if sitemap_urls else 0,
            }
        return None


class SitemapService:
    """Servicio para manejo de sitemaps XML"""
    
    def try_sitemap_fallback(self, domain):
        """
        Intenta obtener URLs del sitemap cuando el crawling falla.
        
        Args:
            domain (str): Dominio del sitio
            
        Returns:
            list: Lista de URLs encontradas en sitemaps
        """
        # Limpiar el dominio de cualquier protocolo previo
        clean_domain = domain.replace("https://", "").replace("http://", "").strip("/")

        print(f"[SITEMAP] Iniciando búsqueda de sitemap para {clean_domain}")

        sitemap_urls = [
            f"https://{clean_domain}/sitemap.xml",
            f"https://www.{clean_domain}/sitemap.xml",
            f"https://{clean_domain}/sitemap_index.xml",
            f"https://{clean_domain}/sitemaps.xml",
            f"https://{clean_domain}/sitemap/",
            f"https://{domain}/sitemap.txt",
        ]

        # Primero buscar en robots.txt
        sitemap_urls = self._find_sitemaps_in_robots(domain, sitemap_urls)

        # Intentar cada sitemap
        for i, sitemap_url in enumerate(sitemap_urls):
            try:
                print(f"[SITEMAP] Probando sitemap {i+1}/{len(sitemap_urls)}: {sitemap_url}")

                headers = get_random_headers()
                # Para algunos sitios, agregar headers más específicos
                if "udemy" in domain:
                    headers.update({
                        "Accept": "application/xml,text/xml,*/*;q=0.8",
                        "X-Requested-With": "XMLHttpRequest",
                    })

                response = requests.get(sitemap_url, timeout=15, headers=headers)
                print(f"[SITEMAP] Respuesta: {response.status_code}")

                if response.status_code == 200:
                    print("[SITEMAP] ✅ Sitemap accesible, parseando contenido...")
                    urls = self.parse_sitemap_urls(response.content, domain)
                    if urls:
                        print(f"[SITEMAP] 🎉 Encontradas {len(urls)} URLs en sitemap")
                        return urls
                    else:
                        print("[SITEMAP] ⚠️ Sitemap válido pero sin URLs útiles")

            except Exception as e:
                print(f"[SITEMAP] Error: {str(e)[:50]}")
                continue

        print(f"[SITEMAP] ❌ No se encontraron sitemaps accesibles para {domain}")
        return []

    def _find_sitemaps_in_robots(self, domain, sitemap_urls):
        """Busca sitemaps en robots.txt"""
        robots_urls = [f"https://{domain}/robots.txt", f"https://www.{domain}/robots.txt"]

        for robots_url in robots_urls:
            try:
                print(f"[SITEMAP] Revisando robots.txt: {robots_url}")
                headers = get_random_headers()
                robots_response = requests.get(robots_url, timeout=10, headers=headers)

                if robots_response.status_code == 200:
                    print("[SITEMAP] ✅ robots.txt accesible")
                    for line in robots_response.text.split("\n"):
                        if line.lower().strip().startswith("sitemap:"):
                            sitemap_url = line.split(":", 1)[1].strip()
                            print(f"[SITEMAP] Sitemap encontrado en robots.txt: {sitemap_url}")
                            sitemap_urls.insert(0, sitemap_url)
                    break
                else:
                    print(f"[SITEMAP] robots.txt no accesible: {robots_response.status_code}")
            except Exception as e:
                print(f"[SITEMAP] Error accediendo robots.txt: {str(e)[:50]}")
                continue

        return sitemap_urls

    def parse_sitemap_urls(self, content, base_domain, max_urls=100):
        """
        Extrae URLs de un sitemap XML.
        
        Args:
            content: Contenido XML del sitemap
            base_domain: Dominio base para filtrar URLs
            max_urls: Máximo número de URLs a extraer
            
        Returns:
            list: Lista de URLs encontradas
        """
        urls = []
        try:
            root = ET_fromstring(content)

            # Definir namespaces comunes
            namespaces = {
                "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
                "": "http://www.sitemaps.org/schemas/sitemap/0.9",
            }

            # Buscar URLs con namespace
            url_elements = root.findall(".//sm:url", namespaces)
            if not url_elements:
                # Buscar sin namespace
                url_elements = root.findall(".//url")

            for url_elem in url_elements:
                loc = url_elem.find("sm:loc", namespaces)
                if loc is None:
                    loc = url_elem.find("loc")

                if loc is not None and loc.text:
                    url = loc.text.strip()
                    if url.startswith("http") and base_domain in url:
                        urls.append(url)
                        if len(urls) >= max_urls:
                            break

            # Si no encontramos URLs, buscar sitemaps anidados
            if not urls:
                urls = self._parse_nested_sitemaps(root, namespaces, base_domain, max_urls)

        except Exception as e:
            print(f"Error parseando sitemap: {e}")

        return urls[:max_urls]

    def _parse_nested_sitemaps(self, root, namespaces, base_domain, max_urls):
        """Parsea sitemaps anidados"""
        urls = []
        sitemap_elements = root.findall(".//sm:sitemap", namespaces)
        if not sitemap_elements:
            sitemap_elements = root.findall(".//sitemap")

        for sitemap_elem in sitemap_elements[:5]:  # Máximo 5 sitemaps anidados
            loc = sitemap_elem.find("sm:loc", namespaces)
            if loc is None:
                loc = sitemap_elem.find("loc")

            if loc is not None and loc.text:
                nested_sitemap_url = loc.text.strip()
                try:
                    nested_response = requests.get(
                        nested_sitemap_url, timeout=10, headers=get_random_headers()
                    )
                    if nested_response.status_code == 200:
                        nested_urls = self.parse_sitemap_urls(
                            nested_response.content,
                            base_domain,
                            max_urls - len(urls),
                        )
                        urls.extend(nested_urls)
                        if len(urls) >= max_urls:
                            break
                except Exception:
                    continue

        return urls


class CrawlingProgressService:
    """Servicio para gestionar el progreso de crawling"""

    def limpiar_procesos_colgados(self):
        """Limpia procesos de crawling que han quedado colgados"""
        hace_10min = timezone.now() - timezone.timedelta(minutes=10)

        procesos_colgados = CrawlingProgress.objects.filter(
            is_done=False, updated_at__lt=hace_10min
        )

        for proceso in procesos_colgados:
            proceso.is_done = True
            proceso.save()

            # Actualizar también el BusquedaDominio correspondiente si existe
            if proceso.busqueda_id:
                try:
                    busqueda = BusquedaDominio.objects.get(id=proceso.busqueda_id)
                    if not busqueda.fecha_fin:
                        busqueda.fecha_fin = timezone.now()
                        if proceso.count > 0 and not busqueda.urls:
                            urls_list = proceso.get_urls_list()
                            busqueda.urls = "\n".join(urls_list[: proceso.count])
                        busqueda.save()
                except BusquedaDominio.DoesNotExist:
                    pass

        return procesos_colgados.count()

    def sincronizar_estados_crawling(self):
        """Sincroniza los estados entre CrawlingProgress y BusquedaDominio"""
        # Buscar CrawlingProgress terminados que tienen BusquedaDominio sin fecha_fin
        progresos_terminados = CrawlingProgress.objects.filter(
            is_done=True, busqueda_id__isnull=False
        )

        for progreso in progresos_terminados:
            try:
                busqueda = BusquedaDominio.objects.get(id=progreso.busqueda_id)
                if not busqueda.fecha_fin:
                    busqueda.fecha_fin = timezone.now()
                    if progreso.count > 0 and not busqueda.urls:
                        urls_list = progreso.get_urls_list()
                        busqueda.urls = "\n".join(urls_list[: progreso.count])
                    busqueda.save()
                    print(f"[SYNC] Sincronizado BusquedaDominio ID {busqueda.id}")
            except BusquedaDominio.DoesNotExist:
                pass

        # Sincronizar en dirección opuesta
        busquedas_terminadas = BusquedaDominio.objects.filter(
            fecha_fin__isnull=False
        ).exclude(
            id__in=CrawlingProgress.objects.filter(is_done=True).values_list(
                "busqueda_id", flat=True
            )
        )

        for busqueda in busquedas_terminadas:
            progresos_activos = CrawlingProgress.objects.filter(
                busqueda_id=busqueda.id, is_done=False
            )
            for progreso in progresos_activos:
                progreso.is_done = True
                progreso.save()
                print(f"[SYNC] Marcado como terminado progreso ID {progreso.id}")

    def limpiar_procesos_fantasma(self):
        """Limpia todos los procesos fantasma de la base de datos"""
        hace_1h = timezone.now() - timezone.timedelta(hours=1)

        procesos_huerfanos = CrawlingProgress.objects.filter(
            is_done=False, updated_at__lt=hace_1h
        )
        count_progress = procesos_huerfanos.count()
        procesos_huerfanos.update(is_done=True)

        busquedas_huerfanas = BusquedaDominio.objects.filter(
            fecha_fin__isnull=True, fecha__lt=hace_1h
        )
        count_busquedas = busquedas_huerfanas.count()
        busquedas_huerfanas.update(fecha_fin=timezone.now())

        return count_progress, count_busquedas