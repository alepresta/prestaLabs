"""
Vistas para el módulo de crawling.

Este módulo contiene todas las vistas relacionadas con el análisis y crawling de dominios.
Código migrado desde views_app.py - funcionalidad exactamente igual que main.
"""

# Imports exactos de main para las funciones migradas
import re
import time
import threading
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.http import JsonResponse
from django.utils import timezone

from ..models import BusquedaDominio, CrawlingProgress

# Variable global para tracking de progreso de crawling
crawling_progress = {}


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
