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
