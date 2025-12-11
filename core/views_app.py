import threading
import time
import re
import random
from urllib.parse import urljoin, urlparse
from defusedxml.ElementTree import fromstring as ET_fromstring
import requests
from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .forms import AdminSetPasswordForm, DominioForm
from .models import BusquedaDominio

# Variable global temporal para progreso (en producción usar cache/db)
crawling_progress = {}

# User-Agents rotativos para evitar detección
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


def try_sitemap_fallback(domain):
    """Intenta obtener URLs del sitemap cuando el crawling falla"""
    # Limpiar el dominio de cualquier protocolo previo
    clean_domain = domain.replace('https://', '').replace('http://', '').strip('/')
    
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
                print(f"[SITEMAP] ✅ robots.txt accesible")
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
                print(f"[SITEMAP] ✅ Sitemap accesible, parseando contenido...")
                urls = parse_sitemap_urls(response.content, domain)
                if urls:
                    print(f"[SITEMAP] 🎉 Encontradas {len(urls)} URLs en sitemap")
                    return urls
                else:
                    print(f"[SITEMAP] ⚠️ Sitemap válido pero sin URLs útiles")
            elif response.status_code == 403:
                print(f"[SITEMAP] ❌ Sitemap bloqueado (403)")
            else:
                print(f"[SITEMAP] ❌ Sitemap no disponible ({response.status_code})")

        except Exception as e:
            print(f"[SITEMAP] Error: {str(e)[:50]}")
            continue

    print(f"[SITEMAP] ❌ No se encontraron sitemaps accesibles para {domain}")
    return []


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


# --- Guardar búsqueda desde AJAX ---
def guardar_busqueda_ajax(dominio, urls, user=None):
    # Limpiar: quitar vacíos, espacios y duplicados
    urls_limpias = list(dict.fromkeys([u.strip() for u in urls if u and u.strip()]))
    from django.utils import timezone

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
            # Actualizar progreso
            crawling_progress[progress_key] = {
                "count": len(urls),
                "last": url,
                "done": False,
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
    crawling_progress[progress_key] = {
        "count": len(urls),
        "last": None,
        "done": True,
        "urls": urls,
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
        crawling_progress[progress_key] = {"count": 0, "last": None, "done": False}

        # Crear el objeto BusquedaDominio al iniciar
        from django.utils import timezone

        obj = BusquedaDominio.objects.create(
            dominio=dominio,
            usuario=(request.user if request.user.is_authenticated else None),
            urls="",
            fecha=timezone.now(),
        )
        # Guardar el id en la sesión para referencia
        request.session["busqueda_id"] = obj.id

        def crawl_and_save():
            urls = crawl_urls_progress(base_url, limite_urls, progress_key)
            # Al finalizar, actualizar el objeto con urls y fecha_fin
            obj.urls = "\n".join(urls)
            obj.fecha_fin = timezone.now()
            obj.save()

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


def admin_set_password_view(request, user_id):
    """Vista para que un admin cambie la contraseña de cualquier usuario"""
    try:
        usuario = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return render(
            request,
            "usuarios/cambiar_password.html",
            {"error": "Usuario no encontrado."},
        )

    mensaje = ""
    if request.method == "POST":
        form = AdminSetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password1"]
            usuario.set_password(new_password)
            usuario.save()
            mensaje = f"Contraseña actualizada para {usuario.username}."
            form = AdminSetPasswordForm()
        else:
            mensaje = "Corrija los errores indicados."
    else:
        form = AdminSetPasswordForm()

    return render(
        request,
        "usuarios/cambiar_password.html",
        {"form": form, "usuario": usuario, "mensaje": mensaje},
    )


def listar_usuarios_view(request):
    """
    Vista para listar todos los usuarios del sistema.
    Permite filtrar por nombre, email y tipo (admin/lectura).
    """
    q = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    usuarios = User.objects.all()
    if q:
        usuarios = usuarios.filter(username__icontains=q) | usuarios.filter(
            email__icontains=q
        )
    if tipo == "admin":
        usuarios = usuarios.filter(is_staff=True)
    elif tipo == "lectura":
        usuarios = usuarios.filter(is_staff=False)
    usuarios = usuarios.order_by("-date_joined")
    return render(request, "usuarios/listar_usuarios.html", {"usuarios": usuarios})


def api_status(request):
    """Vista para verificar el estado de la API"""
    return JsonResponse({"status": "ok"})


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


def crawl_urls(base_url, max_urls=None):
    """Función auxiliar mejorada para crawlear URLs de un dominio"""
    # Normalizar URL base
    if not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"
    
    visited = set()
    to_visit = [base_url]
    urls = []
    domain = urlparse(base_url).netloc or base_url.replace('https://', '').replace('http://', '')
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
                    except:
                        pass
                elif line.lower().strip().startswith("disallow: /"):
                    print(f"[CRAWL] ⚠️ robots.txt prohíbe el crawling completo")
    except:
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
                            f"[CRAWL] ✅ Sitemap encontrado con {len(sitemap_urls)} URLs"
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
                        print(f"[CRAWL] ❌ No se encontró sitemap accesible")
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
                print(f"[CRAWL] 🚨 Demasiados timeouts. Intentando sitemap...")
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
                    f"[CRAWL] 🚨 Demasiados errores de conexión. Intentando sitemap..."
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


def analisis_dominio_view(request):
    """Vista para ingresar dominio y mostrar historial de búsquedas"""
    form = DominioForm()
    mensaje = ""

    regex_part1 = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?"
    regex_part2 = r"(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*"
    regex_part3 = r"$"
    regex = regex_part1 + regex_part2 + regex_part3

    if request.method == "POST":
        if "eliminar_individual" in request.POST:
            eliminar_id = request.POST.get("eliminar_individual")
            BusquedaDominio.objects.filter(id=eliminar_id).delete()
            mensaje = "Búsqueda eliminada correctamente."
        elif "eliminar_seleccionados" in request.POST:
            ids = request.POST.getlist("eliminar_ids")
            BusquedaDominio.objects.filter(id__in=ids).delete()
            mensaje = f"{len(ids)} búsquedas eliminadas correctamente."
        else:
            form = DominioForm(request.POST)
            if form.is_valid():
                dominio_raw = form.cleaned_data["dominio"]
                dominio = normalizar_dominio(dominio_raw)

                if not re.match(regex, dominio):
                    mensaje = "Dominio inválido."
                    return render(
                        request,
                        "analisis_dominio.html",
                        {
                            "form": form,
                            "dominios_tabla": [],
                            "mensaje": mensaje,
                            "error": None,
                            "page_obj": None,
                        },
                    )
                elif not dominio:
                    mensaje = "Dominio vacío."
                    return render(
                        request,
                        "analisis_dominio.html",
                        {
                            "form": form,
                            "dominios_tabla": [],
                            "mensaje": mensaje,
                            "error": None,
                            "page_obj": None,
                        },
                    )
                else:
                    base_url = f"https://{dominio}"
                    limite_urls = request.POST.get("limite_urls")
                    try:
                        limite_urls = int(limite_urls) if limite_urls else None
                    except Exception:
                        limite_urls = None

                    resultado_crawl = crawl_urls(base_url, max_urls=limite_urls)

                    # Manejar tanto formato nuevo (dict) como antiguo (list)
                    if isinstance(resultado_crawl, dict):
                        urls_encontradas = resultado_crawl["urls"]
                        crawl_status = resultado_crawl["status"]
                        blocked_count = resultado_crawl.get("blocked_count", 0)
                    else:
                        # Compatibilidad con formato anterior
                        urls_encontradas = resultado_crawl
                        crawl_status = "legacy"
                        blocked_count = 0

                    # Crear registro en base de datos
                    busqueda = BusquedaDominio.objects.create(
                        dominio=dominio,
                        usuario=(
                            request.user if request.user.is_authenticated else None
                        ),
                        urls="\n".join(urls_encontradas),
                    )

                    # Actualizar fecha de finalización
                    busqueda.fecha_fin = timezone.now()
                    busqueda.save()

                    if "dominios_buscados" not in request.session:
                        request.session["dominios_buscados"] = []

                    if dominio not in request.session["dominios_buscados"]:
                        request.session["dominios_buscados"].append(dominio)
                        request.session.modified = True

                    # Generar mensaje informativo según el estado del crawling
                    from .recommendations import get_domain_recommendations
                    from django.utils.safestring import mark_safe
                    
                    base_msg = f"Dominio '{dominio}' analizado: {len(urls_encontradas)} URLs encontradas."
                    recommendations = get_domain_recommendations(dominio, result)

                    # Determinar clase CSS según el resultado
                    message_class = "info"
                    if crawl_status == "blocked_fallback_sitemap":
                        mensaje = f"{base_msg} ⚠️ Se detectó protección anti-bot, se usó sitemap como alternativa."
                        message_class = "warning"
                    elif crawl_status == "timeout_fallback_sitemap":
                        mensaje = f"{base_msg} ⚠️ El servidor no responde (timeouts), se usó sitemap como alternativa."
                        message_class = "warning"
                    elif crawl_status == "connection_error_fallback_sitemap":
                        mensaje = f"{base_msg} ⚠️ Errores de conexión, se usó sitemap como alternativa."
                        message_class = "warning"
                    elif "no_sitemap" in crawl_status:
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
                    elif blocked_count > 0:
                        mensaje = f"{base_msg} ⚠️ Se detectaron {blocked_count} bloqueos/problemas durante el crawling."
                        message_class = "warning"
                    else:
                        mensaje = f"{base_msg} ✅ Crawling completado exitosamente."
                        message_class = "success"

                    # Generar HTML para recomendaciones si existen
                    if recommendations:
                        recommendations_html = f'''
                        <div class="domain-recommendations domain-{message_class}">
                            <div class="recommendation-title">
                                <i class="bi bi-lightbulb-fill recommendation-icon"></i>
                                Recomendaciones para {dominio}
                            </div>
                        '''
                        
                        for rec in recommendations:
                            recommendations_html += f'''
                            <div class="recommendation-item">
                                <span class="recommendation-icon">{rec[:2]}</span>
                                <span>{rec[2:]}</span>
                            </div>
                            '''
                        
                        recommendations_html += '</div>'
                        mensaje = mark_safe(f'<div class="crawl-message {message_class}">{mensaje}</div>{recommendations_html}')
                    else:
                        mensaje = mark_safe(f'<div class="crawl-message {message_class}">{mensaje}</div>')

    busquedas_qs = BusquedaDominio.objects.order_by("-fecha")[:1000]
    dominios_tabla = []
    from django.utils import timezone

    for b in busquedas_qs:
        dom_norm = normalizar_dominio(b.dominio)
        fecha_inicio = timezone.localtime(b.fecha)
        fecha_fin = timezone.localtime(b.fecha_fin) if b.fecha_fin else None
        duracion = None
        estado = "En progreso"
        estado_detalle = ""
        estado_clase = "secondary"
        
        total_urls = len(b.get_urls())
        
        if fecha_fin:
            delta = fecha_fin - fecha_inicio
            total_seconds = int(delta.total_seconds())
            if total_seconds < 0:
                duracion = "-"
            else:
                h = total_seconds // 3600
                m = (total_seconds % 3600) // 60
                s = total_seconds % 60
                duracion = f"{h:02}:{m:02}:{s:02}"
            estado = "Finalizado"
            
            # Determinar estado específico basado en resultados
            if total_urls == 0 and total_seconds <= 2:
                # Probablemente bloqueado (finaliza muy rápido con 0 URLs)
                if dom_norm.lower() in ['udemy.com', 'netflix.com', 'hulu.com', 'disney.com']:
                    estado_detalle = "🛡️ Dominio completamente protegido"
                    estado_clase = "danger"
                else:
                    estado_detalle = "⚠️ Posible bloqueo o error"
                    estado_clase = "warning"
            elif total_urls == 0 and total_seconds > 15:
                estado_detalle = "⏰ Timeout o problemas de conexión"  
                estado_clase = "warning"
            elif total_urls == 0 and 3 <= total_seconds <= 15:
                # Casos como jw.org: intenta crawling pero no encuentra sitemap
                if 'jw.org' in dom_norm.lower():
                    estado_detalle = "🔒 Restricciones de acceso o geobloqueo"
                    estado_clase = "warning"
                elif any(keyword in dom_norm.lower() for keyword in ['redlink', 'hb.']):
                    estado_detalle = "🌐 Error de conexión o dominio inaccesible"
                    estado_clase = "warning" 
                else:
                    estado_detalle = "🔍 Sin sitemap encontrado"
                    estado_clase = "info"
            elif total_urls > 0 and total_seconds <= 5:
                estado_detalle = "✅ Éxito rápido (sitemap)"
                estado_clase = "success"
            elif total_urls > 0:
                estado_detalle = "✅ Crawling exitoso"
                estado_clase = "success" 
            else:
                estado_detalle = "ℹ️ Finalizado"
                estado_clase = "info"
        else:
            estado_detalle = "🔄 En curso..."
            estado_clase = "primary"
            
        dominios_tabla.append(
            {
                "id": b.id,
                "dominio": dom_norm,
                "inicio": fecha_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                "fin": fecha_fin.strftime("%Y-%m-%d %H:%M:%S") if fecha_fin else "",
                "duracion": duracion or "",
                "usuario": b.usuario.username if b.usuario else "-",
                "total_urls": total_urls,
                "estado": estado,
                "estado_detalle": estado_detalle,
                "estado_clase": estado_clase,
                "url_original": b.dominio,
            }
        )

    paginator = Paginator(dominios_tabla, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    total_registros = BusquedaDominio.objects.count()
    print(f"Total registros en BD: {total_registros}")
    print(f"Registros mostrados (página): {len(page_obj)}")

    for b in page_obj:
        print(
            f"  - {b['dominio']} | Inicio: {b['inicio']} | Fin: {b['fin']} | "
            f"Duración: {b['duracion']} | URLs: {b['total_urls']}"
        )

    return render(
        request,
        "analisis_dominio.html",
        {
            "form": form,
            "dominios_tabla": list(page_obj),
            "mensaje": mensaje,
            "error": None,
            "page_obj": page_obj,
        },
    )


def analisis_detalle(request):
    """Vista para mostrar las URLs del sitemap de un dominio"""
    busqueda_id = request.GET.get("id")
    error = None
    busquedas = []
    dominio = ""
    if busqueda_id:
        try:
            busq = BusquedaDominio.objects.get(id=busqueda_id)
            busquedas = [busq]
            dominio = busq.dominio
        except BusquedaDominio.DoesNotExist:
            error = "No se encontró la búsqueda solicitada."
    else:
        error = "No se especificó una búsqueda."

    form = DominioForm(initial={"dominio": dominio})
    return render(
        request,
        "analisis/detalle.html",
        {
            "form": form,
            "dominio": dominio,
            "busquedas": busquedas,
            "error": error,
        },
    )


def analisis_url_view(request):
    """Vista básica para análisis de una URL específica"""
    return render(request, "analisis/url_especifica.html")


def dashboard_view(request):
    """Vista del dashboard con estadísticas de dominios bloqueados"""
    from .recommendations import get_blocked_domains_stats
    
    # Obtener estadísticas de dominios bloqueados
    blocked_stats = get_blocked_domains_stats()
    
    # Obtener búsquedas recientes (últimas 10)
    recent_searches = BusquedaDominio.objects.order_by("-fecha")[:10]
    
    # Calcular métricas generales
    total_searches_all_time = BusquedaDominio.objects.count()
    
    context = {
        'blocked_stats': blocked_stats,
        'recent_searches': recent_searches,
        'total_searches_all_time': total_searches_all_time,
    }
    
    return render(request, "dashboard/index.html", context)


def reportes_view(request):
    """Vista básica para reportes"""
    return render(request, "reportes.html")


def nuevo_reporte_view(request):
    """Vista básica para crear un nuevo reporte"""
    return render(request, "reportes/nuevo_reporte.html")


def nuevo_usuario_view(request):
    """Vista para crear un nuevo usuario (admin o lectura)"""
    from .forms import UsuarioLecturaForm

    mensaje = ""
    if request.method == "POST":
        form = UsuarioLecturaForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            if User.objects.filter(username=username).exists():
                mensaje = f"El usuario '{username}' ya existe."
            elif User.objects.filter(email=email).exists():
                mensaje = f"El email '{email}' ya está en uso."
            else:
                is_staff = request.POST.get("is_staff") == "on"
                user = User.objects.create_user(
                    username=username, email=email, password=password
                )
                user.is_staff = is_staff
                user.save()
                mensaje = f"Usuario '{username}' creado correctamente."
                form = UsuarioLecturaForm()
        else:
            mensaje = "Corrija los errores indicados."
    else:
        form = UsuarioLecturaForm()

    usuarios = User.objects.all().order_by("-date_joined")
    return render(
        request,
        "usuarios/crear_usuario.html",
        {"form": form, "usuarios": usuarios, "mensaje": mensaje},
    )


def editar_usuarios_view(request):
    """Vista para editar usuarios con filtros, formularios y paginación"""
    from .forms import EditarUsuarioForm

    mensaje = ""
    if request.method == "POST":
        eliminar_id = request.POST.get("eliminar_id")
        if eliminar_id:
            try:
                usuario = User.objects.get(pk=eliminar_id)
                usuario.delete()
                mensaje = "Usuario eliminado correctamente."
            except User.DoesNotExist:
                mensaje = "Usuario no encontrado para eliminar."
        else:
            user_id = request.POST.get("user_id")
            if user_id:
                try:
                    usuario = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    mensaje = "Usuario no encontrado."
                else:
                    form = EditarUsuarioForm(request.POST, instance=usuario)
                    if form.is_valid():
                        form.save()
                        mensaje = f"Usuario '{usuario.username}' actualizado."
                    else:
                        mensaje = "Error al actualizar el usuario."

    q = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    usuarios = User.objects.all()

    if q:
        usuarios = usuarios.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if tipo == "admin":
        usuarios = usuarios.filter(is_staff=True)
    elif tipo == "lectura":
        usuarios = usuarios.filter(is_staff=False)

    usuarios = usuarios.order_by("-date_joined")

    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    forms_dict = {}
    for usuario in page_obj:
        forms_dict[usuario.id] = EditarUsuarioForm(instance=usuario)

    context = {
        "usuarios": page_obj,
        "forms_dict": forms_dict,
        "page_obj": page_obj,
        "mensaje": mensaje,
    }
    return render(request, "usuarios/editar_usuarios.html", context)


def soporte_view(request):
    """Vista básica para soporte"""
    return render(request, "soporte.html")


def configuracion_view(request):
    """Vista básica para configuración"""
    return render(request, "configuracion.html")


def documentacion_view(request):
    """Vista básica para documentación"""
    return render(request, "documentacion.html")


def json_response_view(request):
    """Vista para respuesta JSON básica"""
    return JsonResponse({"status": "ok"})


def index(request):
    """Vista principal del dashboard institucional"""
    return render(request, "dashboard/index.html")
