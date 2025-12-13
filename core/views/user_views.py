"""
Vistas para el módulo de usuarios.

Este módulo contiene todas las vistas relacionadas con la gestión de usuarios.
Solo maneja requests/responses y delega la lógica de negocio a los servicios.
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import render
from django.http import JsonResponse
from ..services.user_service import UserService


def is_staff_user(user):
    """Verifica si el usuario es staff"""
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_staff_user)
def listar_usuarios_view(request):
    """
    Vista para listar todos los usuarios del sistema.
    Permite filtrar por nombre, email y tipo (admin/lectura).
    """
    user_service = UserService()

    # Obtener parámetros de búsqueda
    search_query = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")

    # Obtener usuarios usando el servicio
    usuarios = user_service.get_user_list(search_query)

    # Aplicar filtro por tipo
    if tipo == "admin":
        usuarios = usuarios.filter(is_staff=True)
    elif tipo == "lectura":
        usuarios = usuarios.filter(is_staff=False)

    # Obtener estadísticas
    stats = user_service.get_user_stats()

    context = {
        "usuarios": usuarios,
        "stats": stats,
        "search_query": search_query,
        "tipo_filtro": tipo,
    }

    return render(request, "usuarios/listar_usuarios.html", context)


@login_required
@user_passes_test(is_staff_user)
def nuevo_usuario_view(request):
    """Vista para crear un nuevo usuario (admin o lectura)"""
    from ..forms import UsuarioLecturaForm

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


@login_required
@user_passes_test(is_staff_user)
def editar_usuarios_view(request):
    """Vista para editar usuarios con filtros, formularios y paginación"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    from ..forms import EditarUsuarioForm

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


def admin_set_password_view(request, user_id):
    """Vista para que un admin cambie la contraseña de cualquier usuario"""
    from ..forms import AdminSetPasswordForm

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


# API endpoints para operaciones AJAX
@login_required
@user_passes_test(is_staff_user)
def user_stats_api(request):
    """API endpoint para obtener estadísticas de usuarios"""
    user_service = UserService()
    stats = user_service.get_user_stats()
    return JsonResponse(stats)


@login_required
@user_passes_test(is_staff_user)
def toggle_user_status_api(request):
    """API endpoint para activar/desactivar usuarios via AJAX"""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        user_id = request.POST.get("user_id")
        user = User.objects.get(id=user_id)

        # Cambiar estado
        user.is_active = not user.is_active
        user.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Usuario {'activado' if user.is_active else 'desactivado'} exitosamente",
                "is_active": user.is_active,
            }
        )

    except User.DoesNotExist:
        return JsonResponse({"error": "Usuario no encontrado"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Error interno: {str(e)}"}, status=500)
