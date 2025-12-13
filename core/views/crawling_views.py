"""
Vistas para el módulo de crawling.

Este módulo contiene todas las vistas relacionadas con el análisis y crawling de dominios.
Código migrado desde views_app.py - funcionalidad exactamente igual que main.
"""

# Imports exactos de main para las funciones migradas
import random
import re
import time
import threading
from urllib.parse import urljoin, urlparse
from xml.etree.ElementTree import fromstring as ET_fromstring

import requests
from bs4 import BeautifulSoup
from django.http import JsonResponse
from django.utils import timezone

from ..models import BusquedaDominio, CrawlingProgress

# Variable global para tracking de progreso de crawling
crawling_progress = {}

# User agents para simulación de navegadores reales
USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Edge/119.0.0.0"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
]


def get_random_headers():
    """Genera headers aleatorios para simular navegador real"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }


def detect_blocking(response, url):
    """Detecta si una respuesta indica bloqueo anti-bot"""
    status = response.status_code
    content = response.text.lower() if hasattr(response, "text") else ""

    # Códigos de estado que indican bloqueo
    if status in [403, 429, 503]:
        return True, f"HTTP {status}: Acceso bloqueado por el servidor"

    # Contenido que indica bloqueo
    blocking_keywords = [
        "blocked",
        "forbidden",
        "access denied",
        "cloudflare",
        "captcha",
        "robot",
        "bot detected",
        "rate limit",
        "too many requests",
        "suspicious activity",
    ]

    if any(keyword in content for keyword in blocking_keywords):
        return True, "Contenido indica protección anti-bot"

    # Respuesta muy pequeña o vacía puede indicar bloqueo
    if len(content) < 100 and status == 200:
        return True, "Respuesta sospechosamente pequeña"

    return False, ""


def parse_sitemap_urls(content, base_domain, max_urls=100):
    """Extrae URLs de un sitemap XML"""
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
                            nested_urls = parse_sitemap_urls(
                                nested_response.content,
                                base_domain,
                                max_urls - len(urls),
                            )
                            urls.extend(nested_urls)
                            if len(urls) >= max_urls:
                                break
                    except Exception:
                        continue

    except Exception as e:
        print(f"Error parseando sitemap: {e}")

    return urls[:max_urls]


def try_sitemap_fallback(domain):
    """Intenta obtener URLs del sitemap cuando el crawling falla"""
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

    # Primero buscar en robots.txt con diferentes estrategias
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
                        print(
                            f"[SITEMAP] Sitemap encontrado en robots.txt: {sitemap_url}"
                        )
                        sitemap_urls.insert(0, sitemap_url)
                break
            else:
                print(
                    f"[SITEMAP] robots.txt no accesible: {robots_response.status_code}"
                )
        except Exception as e:
            print(f"[SITEMAP] Error accediendo robots.txt: {str(e)[:50]}")
            continue

    # Intentar cada sitemap con diferentes estrategias
    for i, sitemap_url in enumerate(sitemap_urls):
        try:
            print(
                f"[SITEMAP] Probando sitemap {i+1}/{len(sitemap_urls)}: {sitemap_url}"
            )

            # Usar diferentes headers para cada intento
            headers = get_random_headers()
            # Para algunos sitios, agregar headers más específicos
            if "udemy" in domain:
                headers.update(
                    {
                        "Accept": "application/xml,text/xml,*/*;q=0.8",
                        "X-Requested-With": "XMLHttpRequest",
                    }
                )

            response = requests.get(sitemap_url, timeout=15, headers=headers)

            print(f"[SITEMAP] Respuesta: {response.status_code}")

            if response.status_code == 200:
                print("[SITEMAP] ✅ Sitemap accesible, parseando contenido...")
                urls = parse_sitemap_urls(response.content, domain)
                if urls:
                    print(f"[SITEMAP] 🎉 Encontradas {len(urls)} URLs en sitemap")
                    return urls
                else:
                    print("[SITEMAP] ⚠️ Sitemap válido pero sin URLs útiles")
            elif response.status_code == 403:
                print("[SITEMAP] ❌ Sitemap bloqueado (403)")
            else:
                print(f"[SITEMAP] ❌ Sitemap no disponible ({response.status_code})")

        except Exception as e:
            print(f"[SITEMAP] Error: {str(e)[:50]}")
            continue

    print(f"[SITEMAP] ❌ No se encontraron sitemaps accesibles para {domain}")
    return []


def normalizar_dominio(dominio_raw):
    """Normaliza un dominio: quita protocolo, path, puerto, www, etc."""
    dominio_raw = dominio_raw.strip().lower()
    dominio = re.sub(r"^https?://", "", dominio_raw)
    dominio = dominio.split("/")[0].split("?")[0]
    dominio = dominio.split(":")[0]
    partes = dominio.split(".")
    if len(partes) >= 3 and partes[0] == "www":
        dominio = ".".join(partes[1:])
    dominio = dominio.rstrip(".")
    dominio = re.sub(r"\.{2,}", ".", dominio)
    return dominio


def crawl_urls_progress(base_url, max_urls, progress_key):
    visited = set()
    to_visit = [base_url]
    urls = []

    def normalize_netloc(netloc):
        return netloc.lower().replace("www.", "")

    domain = normalize_netloc(urlparse(base_url).netloc or base_url)

    while to_visit:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        # VERIFICAR SI DEBE DETENERSE
        try:
            progress_obj = CrawlingProgress.objects.get(progress_key=progress_key)
            if progress_obj.is_done:
                print(
                    f"[CRAWL] ⏹️ DETENIDO - Se recibió señal de stop para {progress_key}"
                )
                break
        except CrawlingProgress.DoesNotExist:
            print(f"[CRAWL] ⏹️ DETENIDO - Progreso eliminado: {progress_key}")
            break

        try:
            resp = requests.get(
                url,
                timeout=8,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/119.0.0.0 Safari/537.36"
                    )
                },
            )
            print(f"[CRAWL] URL: {url} | Status: {resp.status_code}")
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.content, "html.parser")
            urls.append(url)
            enlaces = [a["href"].strip() for a in soup.find_all("a", href=True)]
            print(f"[CRAWL] Enlaces encontrados en {url}: {len(enlaces)}")
            if enlaces:
                print(f"[CRAWL] Primeros 5 enlaces: {enlaces[:5]}")
            # Actualizar progreso en base de datos
            progress_obj, created = CrawlingProgress.objects.get_or_create(
                progress_key=progress_key, defaults={"dominio": domain, "usuario": None}
            )
            progress_obj.count = len(urls)
            progress_obj.last_url = url
            progress_obj.urls_found = "|".join(urls)
            progress_obj.save()

            # Mantener también en memoria para compatibilidad
            crawling_progress[progress_key] = {
                "count": len(urls),
                "last": url,
                "done": False,
                "urls": urls.copy(),
            }
            if max_urls and len(urls) >= max_urls:
                break
            for href in enlaces:
                if (
                    href.startswith("#")
                    or href.startswith("mailto:")
                    or href.startswith("javascript:")
                ):
                    continue
                abs_url = urljoin(url, href)
                parsed = urlparse(abs_url)
                # Permitir tanto con como sin www
                if parsed.netloc and normalize_netloc(parsed.netloc) != domain:
                    continue
                if (
                    abs_url not in visited
                    and abs_url not in to_visit
                    and abs_url.startswith("http")
                ):
                    to_visit.append(abs_url)
        except Exception as e:
            print(f"[CRAWL][ERROR] {url}: {e}")
            continue  # nosec
    # Actualizar progreso final en base de datos
    progress_obj, created = CrawlingProgress.objects.get_or_create(
        progress_key=progress_key, defaults={"dominio": domain, "usuario": None}
    )
    progress_obj.count = len(urls)
    progress_obj.last_url = ""
    progress_obj.urls_found = "|".join(urls)
    progress_obj.is_done = True
    progress_obj.save()

    # Mantener también en memoria
    crawling_progress[progress_key] = {
        "count": len(urls),
        "last": None,
        "done": True,
        "urls": urls.copy(),
    }
    return urls


def iniciar_crawling_ajax(request):
    """Inicia el crawling en background y retorna una key de progreso"""
    if request.method == "POST":
        dominio = request.POST.get("dominio")
        limite_urls = request.POST.get("limite_urls")
        try:
            limite_urls = int(limite_urls) if limite_urls else None
        except Exception:
            limite_urls = None

        # Probar primero con https, si falla probar con http
        def limpiar_dominio(d):
            d = d.strip()
            if d.startswith("http://"):
                d = d[7:]
            elif d.startswith("https://"):
                d = d[8:]
            return d.rstrip("/")

        dominio_limpio = limpiar_dominio(dominio)

        def get_working_base_url(dominio):
            for proto in ["https", "http"]:
                url = f"{proto}://{dominio}"
                try:
                    resp = requests.get(
                        url, timeout=6, headers={"User-Agent": "PrestaLab"}
                    )
                    if resp.status_code == 200:
                        return url
                except Exception:
                    continue  # nosec
            return f"https://{dominio}"  # fallback

        base_url = get_working_base_url(dominio_limpio)
        progress_key = f"{dominio}_{int(time.time())}"

        # Crear el objeto BusquedaDominio al iniciar

        obj = BusquedaDominio.objects.create(
            dominio=dominio,
            usuario=(request.user if request.user.is_authenticated else None),
            urls="",
            fecha=timezone.now(),
        )

        # Crear progreso persistente en base de datos
        progress_obj = CrawlingProgress.objects.create(
            progress_key=progress_key,
            usuario=(request.user if request.user.is_authenticated else None),
            dominio=dominio,
            busqueda_id=obj.id,
        )

        # Mantener también en memoria para compatibilidad
        crawling_progress[progress_key] = {"count": 0, "last": None, "done": False}

        # Guardar el id en la sesión para referencia
        request.session["busqueda_id"] = obj.id

        def crawl_and_save():
            try:
                urls = crawl_urls_progress(base_url, limite_urls, progress_key)
                # Al finalizar, actualizar ambos objetos
                obj.urls = "\n".join(urls)
                obj.fecha_fin = timezone.now()
                obj.save()

                # Actualizar también CrawlingProgress
                progress_obj.is_done = True
                progress_obj.save()

                print(
                    f"[AJAX] Crawling completado para {dominio}. URLs encontradas: {len(urls)}"
                )
            except Exception as e:
                # En caso de error, asegurar que ambos se marquen como finalizados
                print(f"[AJAX] Error en crawling: {e}")
                obj.urls = ""
                obj.fecha_fin = timezone.now()
                obj.save()

                # Marcar también como terminado en CrawlingProgress
                progress_obj.is_done = True
                progress_obj.save()

        t = threading.Thread(target=crawl_and_save)
        t.start()
        return JsonResponse({"progress_key": progress_key})
    return JsonResponse({"error": "Método no permitido"}, status=405)


def progreso_crawling_ajax(request):
    """Devuelve el progreso actual del crawling"""
    key = request.GET.get("progress_key")
    if not key or key not in crawling_progress:
        return JsonResponse({"error": "Clave inválida"}, status=404)
    prog = crawling_progress[key]
    return JsonResponse(prog)


def sincronizar_estados_crawling():
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
                # Actualizar URLs si no existen
                if progreso.count > 0 and not busqueda.urls:
                    urls_list = progreso.get_urls_list()
                    busqueda.urls = "\n".join(urls_list[: progreso.count])
                busqueda.save()
                print(f"[SYNC] Sincronizado BusquedaDominio ID {busqueda.id}")
        except BusquedaDominio.DoesNotExist:
            pass

    # Buscar BusquedaDominio con fecha_fin que tienen CrawlingProgress sin terminar
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
            print(f"[SYNC] Marcado progreso como terminado: {progreso.progress_key}")


def verificar_crawling_activo(request):
    """Verifica si hay un crawling activo para el usuario"""
    usuario = request.user if request.user.is_authenticated else None

    # Primero limpiar procesos colgados y sincronizar estados
    # Nota: limpiar_procesos_colgados no migrado aún, se saltea por ahora
    
    # Sincronizar estados entre CrawlingProgress y BusquedaDominio
    sincronizar_estados_crawling()

    # Buscar crawlings activos (no completados) de las últimas 24 horas

    hace_24h = timezone.now() - timezone.timedelta(hours=24)

    crawlings_activos = CrawlingProgress.objects.filter(
        usuario=usuario, is_done=False, created_at__gte=hace_24h
    ).order_by("-created_at")[:1]

    if crawlings_activos:
        progress_obj = crawlings_activos[0]

        # Verificar si realmente está activo (actualizado en los últimos 5 minutos)
        hace_5min = timezone.now() - timezone.timedelta(minutes=5)
        if progress_obj.updated_at < hace_5min:
            # Proceso probablemente abandonado, marcarlo como terminado
            progress_obj.is_done = True
            progress_obj.save()

            # También actualizar BusquedaDominio si existe
            if progress_obj.busqueda_id:
                try:
                    busqueda = BusquedaDominio.objects.get(id=progress_obj.busqueda_id)
                    if not busqueda.fecha_fin:
                        busqueda.fecha_fin = timezone.now()
                        # Actualizar URLs con el progreso actual
                        if progress_obj.count > 0 and not busqueda.urls:
                            urls_list = progress_obj.get_urls_list()
                            busqueda.urls = "\n".join(urls_list[: progress_obj.count])
                        busqueda.save()
                        print(
                            f"[SYNC] Finalizado proceso abandonado: ID {busqueda.id}, URLs: {progress_obj.count}"
                        )
                except BusquedaDominio.DoesNotExist:
                    pass

            return JsonResponse({"active": False})

        return JsonResponse(
            {
                "active": True,
                "progress_key": progress_obj.progress_key,
                "dominio": progress_obj.dominio,
                "count": progress_obj.count,
                "last": progress_obj.last_url,
                "urls": progress_obj.get_urls_list(),
            }
        )

    return JsonResponse({"active": False})


def detener_crawling_ajax(request):
    """Detiene un proceso de crawling activo específico o el más reciente"""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    # Buscar crawling activo del usuario
    usuario = request.user if request.user.is_authenticated else None

    try:
        # Verificar si se especifica un ID de proceso específico
        import json

        try:
            body = json.loads(request.body.decode("utf-8"))
            progress_id = body.get("progress_id")
        except (json.JSONDecodeError, UnicodeDecodeError):
            progress_id = request.POST.get("progress_id")

        if progress_id:
            # Detener proceso específico
            try:
                progress_obj = CrawlingProgress.objects.get(
                    id=progress_id, is_done=False
                )
                # Verificar permisos - solo el usuario propietario o admin
                if progress_obj.usuario != usuario and not (
                    usuario and usuario.is_staff
                ):
                    return JsonResponse(
                        {"error": "No tienes permisos para detener este proceso"},
                        status=403,
                    )
            except CrawlingProgress.DoesNotExist:
                return JsonResponse(
                    {"error": "Proceso no encontrado o ya terminado"}, status=404
                )
        else:
            # Buscar progreso activo - primero por usuario, sino cualquiera
            progress_obj = (
                CrawlingProgress.objects.filter(usuario=usuario, is_done=False)
                .order_by("-created_at")
                .first()
            )

            # Si no hay del usuario, buscar cualquier crawling activo
            if not progress_obj:
                progress_obj = (
                    CrawlingProgress.objects.filter(is_done=False)
                    .order_by("-created_at")
                    .first()
                )

        if not progress_obj:
            return JsonResponse(
                {"error": "No hay crawling activo para detener"}, status=404
            )

        print(
            f"[STOP] Deteniendo crawling: {progress_obj.progress_key} del dominio {progress_obj.dominio}"
        )

        # Marcar como detenido
        progress_obj.is_done = True
        progress_obj.save()

        # También detener en BusquedaDominio si existe
        if progress_obj.busqueda_id:
            try:

                busqueda = BusquedaDominio.objects.get(id=progress_obj.busqueda_id)
                if not busqueda.fecha_fin:  # Solo si no está ya terminado
                    busqueda.fecha_fin = timezone.now()
                    # Guardar URLs parciales si existen
                    if progress_obj.count > 0 and not busqueda.urls:
                        urls_list = progress_obj.get_urls_list()
                        busqueda.urls = "\n".join(urls_list)
                    busqueda.save()
                    print(f"[STOP] También terminado BusquedaDominio ID: {busqueda.id}")
            except BusquedaDominio.DoesNotExist:
                print(
                    f"[STOP] BusquedaDominio {progress_obj.busqueda_id} no encontrado"
                )
                pass

        # Limpiar de memoria
        if progress_obj.progress_key in crawling_progress:
            crawling_progress[progress_obj.progress_key]["done"] = True
            print(f"[STOP] Limpiado de memoria: {progress_obj.progress_key}")

        print(f"[STOP] Crawling detenido exitosamente: {progress_obj.progress_key}")
        return JsonResponse(
            {
                "success": True,
                "message": f"Crawling detenido exitosamente: {progress_obj.dominio}",
                "dominio": progress_obj.dominio,
                "progress_key": progress_obj.progress_key,
            }
        )

    except Exception as e:
        print(f"[STOP] Error deteniendo crawling: {e}")
        import traceback

        traceback.print_exc()
        return JsonResponse(
            {"error": f"Error interno del servidor: {str(e)}"}, status=500
        )


def listar_crawlings_activos_ajax(request):
    """Lista todos los crawlings activos del usuario"""
    if request.method != "GET":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    usuario = request.user if request.user.is_authenticated else None

    try:

        # Buscar todos los crawlings activos del usuario (últimas 24 horas)
        hace_24h = timezone.now() - timezone.timedelta(hours=24)

        crawlings_activos = CrawlingProgress.objects.filter(
            usuario=usuario, is_done=False, created_at__gte=hace_24h
        ).order_by("-created_at")

        procesos = []
        for crawling in crawlings_activos:
            # Verificar si está realmente activo (actualizado en los últimos 5 minutos)
            hace_5min = timezone.now() - timezone.timedelta(minutes=5)
            esta_activo = crawling.updated_at >= hace_5min

            procesos.append(
                {
                    "id": crawling.id,
                    "progress_key": crawling.progress_key,
                    "dominio": crawling.dominio,
                    "count": crawling.count,
                    "last_url": crawling.last_url,
                    "created_at": crawling.created_at.isoformat(),
                    "updated_at": crawling.updated_at.isoformat(),
                    "esta_activo": esta_activo,
                    "busqueda_id": crawling.busqueda_id,
                }
            )

        return JsonResponse(
            {"success": True, "procesos": procesos, "total": len(procesos)}
        )

    except Exception as e:
        print(f"[CRAWLINGS_ACTIVOS] Error: {e}")
        import traceback

        traceback.print_exc()
        return JsonResponse({"error": f"Error interno: {str(e)}"}, status=500)


def limpiar_procesos_fantasma_ajax(request):
    """Limpia todos los procesos fantasma de la base de datos"""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:

        # Limpiar CrawlingProgress huérfanos (más de 1 hora sin actualizar)
        hace_1h = timezone.now() - timezone.timedelta(hours=1)

        procesos_huerfanos = CrawlingProgress.objects.filter(
            is_done=False, updated_at__lt=hace_1h
        )

        count_progress = procesos_huerfanos.count()
        procesos_huerfanos.update(is_done=True)

        # Limpiar BusquedaDominio sin terminar (más de 1 hora)
        busquedas_huerfanas = BusquedaDominio.objects.filter(
            fecha_fin__isnull=True, fecha__lt=hace_1h
        )

        count_busquedas = busquedas_huerfanas.count()
        busquedas_huerfanas.update(fecha_fin=timezone.now())

        # Limpiar memoria
        global crawling_progress
        crawling_progress.clear()

        mensaje = f"Limpiados {count_progress} procesos fantasma y {count_busquedas} búsquedas huérfanas"
        print(f"[CLEANUP] {mensaje}")

        return JsonResponse(
            {
                "success": True,
                "message": mensaje,
                "cleaned_progress": count_progress,
                "cleaned_searches": count_busquedas,
            }
        )

    except Exception as e:
        print(f"[CLEANUP] Error limpiando procesos fantasma: {e}")
        return JsonResponse({"error": "Error interno del servidor"}, status=500)


def guardar_busqueda_ajax(dominio, urls, user=None):
    # Limpiar: quitar vacíos, espacios y duplicados
    urls_limpias = list(dict.fromkeys([u.strip() for u in urls if u and u.strip()]))

    # Buscar la última búsqueda sin fecha_fin para este usuario y dominio

    obj = None
    if user and hasattr(user, "is_authenticated") and user.is_authenticated:
        obj = (
            BusquedaDominio.objects.filter(
                dominio=dominio, usuario=user, fecha_fin__isnull=True
            )
            .order_by("-fecha")
            .first()
        )
    else:
        obj = (
            BusquedaDominio.objects.filter(
                dominio=dominio, usuario=None, fecha_fin__isnull=True
            )
            .order_by("-fecha")
            .first()
        )
    if obj:
        obj.urls = "\n".join(urls_limpias)
        obj.fecha_fin = timezone.now()
        obj.save()
    else:
        BusquedaDominio.objects.create(
            dominio=dominio,
            usuario=(
                user
                if user and hasattr(user, "is_authenticated") and user.is_authenticated
                else None
            ),
            urls="\n".join(urls_limpias),
            fecha=timezone.now(),
        )


def crawl_urls(base_url, max_urls=None):
    """Función auxiliar mejorada para crawlear URLs de un dominio"""
    # Normalizar URL base
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    visited = set()
    to_visit = [base_url]
    urls = []
    domain = urlparse(base_url).netloc or base_url.replace("https://", "").replace(
        "http://", ""
    )
    blocked_count = 0
    max_blocks = 3  # Máximo de bloqueos antes de cambiar estrategia
    crawl_delay = 1  # Delay inicial en segundos

    print(f"[CRAWL] Iniciando crawling mejorado de {base_url}")
    print(f'[CRAWL] Límite de URLs: {max_urls or "Sin límite"}')

    # Verificar robots.txt para obtener delay recomendado
    try:
        robots_url = f"https://{domain}/robots.txt"
        robots_response = requests.get(
            robots_url, timeout=10, headers=get_random_headers()
        )
        if robots_response.status_code == 200:
            for line in robots_response.text.split("\n"):
                if line.lower().strip().startswith("crawl-delay:"):
                    try:
                        recommended_delay = int(line.split(":", 1)[1].strip())
                        crawl_delay = max(crawl_delay, recommended_delay)
                        print(
                            f"[CRAWL] Delay recomendado por robots.txt: {crawl_delay}s"
                        )
                    except Exception:
                        pass
                elif line.lower().strip().startswith("disallow: /"):
                    print("[CRAWL] ⚠️ robots.txt prohíbe el crawling completo")
    except Exception:
        pass

    while to_visit and len(urls) < (max_urls or float("inf")):
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            # Aplicar delay inteligente
            if len(urls) > 0:  # No delay en la primera request
                delay = crawl_delay * (
                    1 + blocked_count * 0.5
                )  # Aumentar delay si hay bloqueos
                print(
                    f"[CRAWL] Esperando {delay:.1f}s antes de la siguiente request..."
                )
                time.sleep(delay)

            # Request con headers aleatorios
            headers = get_random_headers()
            resp = requests.get(url, timeout=15, headers=headers)

            print(f"[CRAWL] {url} -> {resp.status_code}")

            # Detectar bloqueos
            is_blocked, block_reason = detect_blocking(resp, url)

            if is_blocked:
                blocked_count += 1
                print(f"[CRAWL] ⚠️ BLOQUEO DETECTADO: {block_reason}")

                # Para HTTP 403/429 (acceso denegado), intentar sitemap inmediatamente
                # Para otros bloqueos, esperar max_blocks intentos
                immediate_fallback = resp.status_code in [403, 429]
                should_fallback = (blocked_count >= max_blocks) or (
                    immediate_fallback and len(urls) == 0
                )

                if should_fallback:
                    if immediate_fallback:
                        print(
                            f"[CRAWL] 🚨 Acceso denegado ({resp.status_code}). Intentando sitemap inmediatamente..."
                        )
                    else:
                        print(
                            f"[CRAWL] 🚨 Demasiados bloqueos ({blocked_count}). Cambiando a estrategia de sitemap..."
                        )

                    sitemap_urls = try_sitemap_fallback(domain)
                    if sitemap_urls:
                        print(
                            f"[CRAWL] ✅ Sitemap encontrado con "
                            f"{len(sitemap_urls)} URLs"
                        )
                        urls.extend(
                            sitemap_urls[
                                : (
                                    max_urls - len(urls)
                                    if max_urls
                                    else len(sitemap_urls)
                                )
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
                        print("[CRAWL] ❌ No se encontró sitemap accesible")
                        return {
                            "urls": urls,
                            "status": "blocked_no_sitemap",
                            "message": f"Crawling bloqueado y no hay sitemap disponible. Motivo: {block_reason}",
                            "blocked_count": blocked_count,
                            "sitemap_urls": 0,
                        }

                # Aumentar delay y continuar
                crawl_delay *= 2
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
            links_found = 0
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if (
                    href.startswith("#")
                    or href.startswith("mailto:")
                    or href.startswith("javascript:")
                    or href.startswith("tel:")
                    or href.startswith("ftp:")
                ):
                    continue

                abs_url = urljoin(url, href)
                parsed = urlparse(abs_url)

                # Normalizar dominio para comparación
                def normalize_domain(d):
                    return d.lower().replace("www.", "")

                if parsed.netloc and normalize_domain(
                    parsed.netloc
                ) != normalize_domain(domain):
                    continue

                if (
                    abs_url not in visited
                    and abs_url not in to_visit
                    and abs_url.startswith("http")
                    and len(to_visit) < 1000  # Evitar cola infinita
                ):
                    to_visit.append(abs_url)
                    links_found += 1

            print(f"[CRAWL] Enlaces internos encontrados: {links_found}")

        except requests.exceptions.Timeout:
            print(f"[CRAWL] ⏰ Timeout en {url}")
            blocked_count += 1
            if blocked_count >= max_blocks and len(urls) == 0:
                print("[CRAWL] 🚨 Demasiados timeouts. Intentando sitemap...")
                sitemap_urls = try_sitemap_fallback(domain)
                if sitemap_urls:
                    print(f"[CRAWL] ✅ Sitemap encontrado con {len(sitemap_urls)} URLs")
                    urls.extend(sitemap_urls[: max_urls or len(sitemap_urls)])
                return {
                    "urls": urls,
                    "status": (
                        "timeout_fallback_sitemap"
                        if sitemap_urls
                        else "timeout_no_sitemap"
                    ),
                    "message": f'Timeouts repetidos. {"Se usó sitemap como alternativa." if sitemap_urls else "Sin sitemap disponible."}',
                    "blocked_count": blocked_count,
                    "sitemap_urls": len(sitemap_urls) if sitemap_urls else 0,
                }
            continue
        except requests.exceptions.ConnectionError:
            print(f"[CRAWL] 🔌 Error de conexión en {url}")
            blocked_count += 1
            if blocked_count >= max_blocks and len(urls) == 0:
                print(
                    "[CRAWL] 🚨 Demasiados errores de conexión. Intentando sitemap..."
                )
                sitemap_urls = try_sitemap_fallback(domain)
                if sitemap_urls:
                    print(f"[CRAWL] ✅ Sitemap encontrado con {len(sitemap_urls)} URLs")
                    urls.extend(sitemap_urls[: max_urls or len(sitemap_urls)])
                return {
                    "urls": urls,
                    "status": (
                        "connection_error_fallback_sitemap"
                        if sitemap_urls
                        else "connection_error_no_sitemap"
                    ),
                    "message": f'Errores de conexión repetidos. {"Se usó sitemap como alternativa." if sitemap_urls else "Sin sitemap disponible."}',
                    "blocked_count": blocked_count,
                    "sitemap_urls": len(sitemap_urls) if sitemap_urls else 0,
                }
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


def iniciar_crawling_multiple_ajax(request):
    """Inicia el crawling para múltiples dominios en background"""
    if request.method == "POST":
        dominios_text = request.POST.get("dominios_multiple", "")
        limite_urls = request.POST.get("limite_urls_multiple")

        try:
            limite_urls = int(limite_urls) if limite_urls else 50
        except Exception:
            limite_urls = 50

        # Limitar el límite máximo para análisis múltiple
        if limite_urls > 500:
            limite_urls = 500

        # Procesar lista de dominios
        dominios_raw = [d.strip() for d in dominios_text.split("\n") if d.strip()]

        # Validar cantidad de dominios
        if len(dominios_raw) > 10:
            return JsonResponse({"error": "Máximo 10 dominios permitidos"}, status=400)

        if len(dominios_raw) == 0:
            return JsonResponse({"error": "No se proporcionaron dominios"}, status=400)

        # Validar y normalizar dominios
        regex = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$"
        dominios_validos = []

        for dominio_raw in dominios_raw:
            dominio_normalizado = normalizar_dominio(dominio_raw)
            if re.match(regex, dominio_normalizado):
                dominios_validos.append(dominio_normalizado)

        if len(dominios_validos) == 0:
            return JsonResponse(
                {"error": "No se encontraron dominios válidos"}, status=400
            )

        # Generar clave de progreso única para el lote
        batch_key = f"batch_{int(time.time())}"
        crawling_progress[batch_key] = {
            "type": "multiple",
            "total_domains": len(dominios_validos),
            "completed_domains": 0,
            "current_domain": None,
            "results": {},
            "done": False,
        }

        def crawl_multiple_and_save():

            for i, dominio in enumerate(dominios_validos):
                try:
                    # Actualizar progreso
                    crawling_progress[batch_key]["current_domain"] = dominio
                    crawling_progress[batch_key]["completed_domains"] = i

                    # Realizar crawling individual
                    base_url = f"https://{dominio}"
                    resultado_crawl = crawl_urls(base_url, max_urls=limite_urls)

                    # Manejar resultado
                    if isinstance(resultado_crawl, dict):
                        urls_encontradas = resultado_crawl["urls"]
                        crawl_status = resultado_crawl["status"]
                    else:
                        urls_encontradas = resultado_crawl
                        crawl_status = "legacy"

                    # Crear registro en BD con fecha_fin inmediata
                    busqueda = BusquedaDominio.objects.create(
                        dominio=dominio,
                        usuario=(
                            request.user if request.user.is_authenticated else None
                        ),
                        urls="\n".join(urls_encontradas),
                        fecha=timezone.now(),
                        fecha_fin=timezone.now(),  # Marcar como completado inmediatamente
                    )

                    # Guardar resultado
                    crawling_progress[batch_key]["results"][dominio] = {
                        "urls_count": len(urls_encontradas),
                        "status": crawl_status,
                        "id": busqueda.id,
                    }

                    # Pequeña pausa entre dominios para evitar sobrecarga
                    if i < len(dominios_validos) - 1:  # No pausar en el último
                        time.sleep(2)

                except Exception as e:
                    # Manejar errores individuales
                    crawling_progress[batch_key]["results"][dominio] = {
                        "urls_count": 0,
                        "status": "error",
                        "error": str(e)[:100],
                    }

            # Marcar como completado
            crawling_progress[batch_key]["done"] = True
            crawling_progress[batch_key]["completed_domains"] = len(dominios_validos)

        # Iniciar proceso en hilo separado
        t = threading.Thread(target=crawl_multiple_and_save)
        t.start()

        return JsonResponse(
            {
                "progress_key": batch_key,
                "total_domains": len(dominios_validos),
                "valid_domains": dominios_validos,
            }
        )

    return JsonResponse({"error": "Método no permitido"}, status=405)

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
                    # Guardar URLs del progreso si no existen en BusquedaDominio
                    if proceso.count > 0 and not busqueda.urls:
                        urls_list = proceso.get_urls_list()
                        busqueda.urls = "\n".join(urls_list[: proceso.count])
                    busqueda.save()
            except BusquedaDominio.DoesNotExist:
                pass

    return procesos_colgados.count()