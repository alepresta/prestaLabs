"""
Vistas para gestión de usuarios.

Contiene todas las vistas relacionadas con:
- Administración de usuarios
- Cambio de contraseñas
- Listado de usuarios
"""

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from ..forms import AdminSetPasswordForm


@staff_member_required
def admin_set_password_view(request, user_id):
    """Vista para que administradores cambien contraseñas de usuarios"""

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = AdminSetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            user.set_password(new_password)
            user.save()
            messages.success(
                request, f"Contraseña actualizada exitosamente para {user.username}"
            )
            return redirect("listar_usuarios")
    else:
        form = AdminSetPasswordForm()

    context = {
        "form": form,
        "target_user": user,
    }

    return render(request, "usuarios/editar_usuarios.html", context)


@staff_member_required
def listar_usuarios_view(request):
    """Vista para listar todos los usuarios del sistema"""

    # Obtener query de búsqueda
    query = request.GET.get("q", "").strip()

    # Filtrar usuarios
    usuarios = User.objects.all().order_by("-date_joined")

    if query:
        usuarios = usuarios.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    # Paginación
    paginator = Paginator(usuarios, 10)
    page = request.GET.get("page", 1)
    usuarios_paginados = paginator.get_page(page)

    context = {
        "usuarios": usuarios_paginados,
        "query": query,
        "total_usuarios": User.objects.count(),
    }

    return render(request, "usuarios/listar_usuarios.html", context)


@login_required
def perfil_usuario_view(request):
    """Vista para el perfil del usuario actual"""

    if request.method == "POST":
        # Actualizar información del perfil
        user = request.user

        # Obtener datos del formulario
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()

        # Validar email único
        if email and User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, "Este email ya está en uso por otro usuario.")
        else:
            # Actualizar datos
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()

            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("perfil_usuario")

    return render(request, "usuarios/perfil.html", {"user": request.user})


@login_required
def cambiar_password_view(request):
    """Vista para que el usuario cambie su propia contraseña"""

    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Validaciones
        if not request.user.check_password(current_password):
            messages.error(request, "La contraseña actual no es correcta.")
        elif len(new_password) < 8:
            messages.error(
                request, "La nueva contraseña debe tener al menos 8 caracteres."
            )
        elif new_password != confirm_password:
            messages.error(request, "Las contraseñas nuevas no coinciden.")
        else:
            # Cambiar contraseña
            request.user.set_password(new_password)
            request.user.save()

            messages.success(request, "Contraseña cambiada correctamente.")
            return redirect("perfil_usuario")

    return render(request, "usuarios/cambiar_password.html")
