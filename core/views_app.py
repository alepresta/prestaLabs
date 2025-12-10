import re
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from .forms import AdminSetPasswordForm, DominioForm
from .models import BusquedaDominio


# Vista para que un admin cambie la contraseña de cualquier usuario
def admin_set_password_view(request, user_id):
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
            mensaje = f"Contraseña actualizada correctamente para {usuario.username}."
            form = AdminSetPasswordForm()  # Limpiar formulario
        else:
            mensaje = "Corrija los errores indicados."
    else:
        form = AdminSetPasswordForm()

    return render(
        request,
        "usuarios/cambiar_password.html",
        {"form": form, "usuario": usuario, "mensaje": mensaje},
    )


# Vista para listar usuarios (al final del archivo)
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
    """
    Vista para verificar el estado de la API
    """
    return JsonResponse({"status": "ok"})


def normalizar_dominio(dominio_raw):
    """
    Normaliza un dominio: quita protocolo, path, puerto, www, etc.
    """
    dominio_raw = dominio_raw.strip().lower()
    # Quitar protocolo
    dominio = re.sub(r"^https?://", "", dominio_raw)
    # Quitar path y query
    dominio = dominio.split("/")[0].split("?")[0]
    # Quitar puerto
    dominio = dominio.split(":")[0]
    # Quitar www. solo si es el único subdominio (no www1, www2, etc)
    partes = dominio.split(".")
    if len(partes) >= 3 and partes[0] == "www":
        dominio = ".".join(partes[1:])
    # Quitar punto final y puntos dobles
    dominio = dominio.rstrip(".")
    dominio = re.sub(r"\.{2,}", ".", dominio)
    return dominio


def analisis_dominio_view(request):
    """
    Vista para ingresar dominio y mostrar historial de dominios buscados
    """
    form = DominioForm()
    mensaje = ""

    # Validación estricta: solo letras, números, guiones, puntos
    regex_part1 = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?"
    regex_part2 = r"(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*"
    regex_part3 = r"$"
    regex = regex_part1 + regex_part2 + regex_part3

    if request.method == "POST":
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
                # Guardar en sesión para historial rápido
                if "dominios_buscados" not in request.session:
                    request.session["dominios_buscados"] = []

                if dominio not in request.session["dominios_buscados"]:
                    request.session["dominios_buscados"].append(dominio)
                    request.session.modified = True
                    mensaje = f"Dominio '{dominio}' agregado al historial."
                else:
                    mensaje = "El dominio ya fue ingresado."

                url = reverse("analisis_detalle") + f"?dominio={dominio}"
                return redirect(url)

    # Traer últimos 1000 registros, agrupar por dominio normalizado
    busquedas_qs = BusquedaDominio.objects.order_by("-fecha")[:1000]
    dominios_vistos = set()
    dominios_tabla = []

    for b in busquedas_qs:
        dom_norm = normalizar_dominio(b.dominio)
        if dom_norm not in dominios_vistos:
            dominios_vistos.add(dom_norm)
            dominios_tabla.append(
                {
                    "dominio": dom_norm,
                    "id": b.id,
                    "fecha": b.fecha,
                    "usuario": b.usuario.username if b.usuario else "-",
                    "urls": b.urls,
                }
            )

    # Ordenar por fecha descendente
    dominios_tabla.sort(key=lambda x: x["fecha"], reverse=True)

    # Paginación
    paginator = Paginator(dominios_tabla, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Debug (opcional)
    total_registros = BusquedaDominio.objects.count()
    print(f"Total registros en BD: {total_registros}")
    print(f"Registros únicos mostrados (página): {len(page_obj)}")

    for b in page_obj:
        urls_count = len(b["urls"].splitlines()) if b["urls"] else 0
        print(f"  - {b['dominio']} | {b['fecha']} | URLs: {urls_count}")

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
    """
    Vista para mostrar las URLs del sitemap de un dominio
    """
    form = DominioForm()
    mensaje = ""
    page_obj = []
    return render(
        request,
        "analisis_dominio.html",
        {
            "form": form,
            "dominios_tabla": page_obj,
            "mensaje": mensaje,
            "error": None,
            "page_obj": page_obj,
        },
    )


def analisis_url_view(request):
    """
    Vista básica para análisis de una URL específica
    """
    return render(request, "analisis/url_especifica.html")


def dashboard_view(request):
    """
    Vista básica para el dashboard
    """
    return render(request, "dashboard/index.html")


def reportes_view(request):
    """
    Vista básica para reportes
    """
    return render(request, "reportes.html")


def nuevo_reporte_view(request):
    """
    Vista básica para crear un nuevo reporte
    """
    return render(request, "reportes/nuevo_reporte.html")


def nuevo_usuario_view(request):
    """
    Vista para crear un nuevo usuario (admin o lectura)
    """
    from .forms import UsuarioLecturaForm
    from django.contrib.auth.models import User

    mensaje = ""
    if request.method == "POST":
        form = UsuarioLecturaForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            # Si el usuario ya existe, error
            if User.objects.filter(username=username).exists():
                mensaje = f"El usuario '{username}' ya existe."
            else:
                # Si el email ya existe, error
                if User.objects.filter(email=email).exists():
                    mensaje = f"El email '{email}' ya está en uso."
                else:
                    # Permitir elegir tipo de usuario (admin o lectura)
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

    # Mostrar todos los usuarios existentes
    usuarios = User.objects.all().order_by("-date_joined")
    return render(
        request,
        "usuarios/crear_usuario.html",
        {"form": form, "usuarios": usuarios, "mensaje": mensaje},
    )


def editar_usuarios_view(request):
    """
    Vista para editar usuarios con filtros, formularios y paginación
    """
    from .forms import EditarUsuarioForm  # noqa: F401

    mensaje = ""
    if request.method == "POST":
        # Eliminar usuario si se envía eliminar_id
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
                        mensaje = (
                            f"Usuario '{usuario.username}' actualizado correctamente."
                        )
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

    # Paginación
    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Formularios individuales para cada usuario
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
    """
    Vista básica para soporte
    """
    return render(request, "soporte.html")


def configuracion_view(request):
    """
    Vista básica para configuración
    """
    return render(request, "configuracion.html")


def documentacion_view(request):
    """
    Vista básica para documentación
    """
    return render(request, "documentacion.html")


def json_response_view(request):
    """
    Vista para respuesta JSON básica
    """
    return JsonResponse({"status": "ok"})


def index(request):
    """
    Vista principal del dashboard institucional
    """
    return render(request, "dashboard/index.html")
