import threading
import time
import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render

from .forms import AdminSetPasswordForm, DominioForm
from .models import BusquedaDominio

# Variable global temporal para progreso (en producción usar cache/db)
crawling_progress = {}


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
    """Función auxiliar para crawlear URLs de un dominio"""
    visited = set()
    to_visit = [base_url]
    urls = []
    domain = urlparse(base_url).netloc or base_url

    while to_visit:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "PrestaLab"})
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.content, "html.parser")
            urls.append(url)

            if max_urls and len(urls) >= max_urls:
                break

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if (
                    href.startswith("#")
                    or href.startswith("mailto:")
                    or href.startswith("javascript:")
                ):
                    continue

                abs_url = urljoin(url, href)
                parsed = urlparse(abs_url)

                if parsed.netloc and parsed.netloc != domain:
                    continue

                if (
                    abs_url not in visited
                    and abs_url not in to_visit
                    and abs_url.startswith("http")
                ):
                    to_visit.append(abs_url)

        except Exception:
            continue  # nosec

    return urls


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

                    urls_encontradas = crawl_urls(base_url, max_urls=limite_urls)
                    BusquedaDominio.objects.create(
                        dominio=dominio,
                        usuario=(
                            request.user if request.user.is_authenticated else None
                        ),
                        urls="\n".join(urls_encontradas),
                    )

                    if "dominios_buscados" not in request.session:
                        request.session["dominios_buscados"] = []

                    if dominio not in request.session["dominios_buscados"]:
                        request.session["dominios_buscados"].append(dominio)
                        request.session.modified = True

                    mensaje = f"Dominio '{dominio}' analizado correctamente."

    busquedas_qs = BusquedaDominio.objects.order_by("-fecha")[:1000]
    dominios_tabla = []
    from django.utils import timezone

    for b in busquedas_qs:
        dom_norm = normalizar_dominio(b.dominio)
        fecha_inicio = timezone.localtime(b.fecha)
        fecha_fin = timezone.localtime(b.fecha_fin) if b.fecha_fin else None
        duracion = None
        estado = "En progreso"
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
        dominios_tabla.append(
            {
                "id": b.id,
                "dominio": dom_norm,
                "inicio": fecha_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                "fin": fecha_fin.strftime("%Y-%m-%d %H:%M:%S") if fecha_fin else "",
                "duracion": duracion or "",
                "usuario": b.usuario.username if b.usuario else "-",
                "total_urls": len(b.get_urls()),
                "estado": estado,
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
    """Vista básica para el dashboard"""
    return render(request, "dashboard/index.html")


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
