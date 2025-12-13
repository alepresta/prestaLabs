"""
Vistas para el módulo de usuarios.

Este módulo contiene todas las vistas relacionadas con la gestión de usuarios.
Solo maneja requests/responses y delega la lógica de negocio a los servicios.
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
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
    """Vista para crear un nuevo usuario"""
    user_service = UserService()
    
    if request.method == "POST":
        # Obtener datos del formulario
        data = {
            'username': request.POST.get('username', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'password': request.POST.get('password', ''),
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
        }
        
        # Validar datos
        is_valid, errors = user_service.validate_user_data(data, is_update=False)
        
        if is_valid:
            # Crear usuario
            user, created, error_msg = user_service.create_user(
                data['username'],
                data['email'],
                data['password'],
                data['first_name'],
                data['last_name']
            )
            
            if created:
                messages.success(
                    request, 
                    f"Usuario '{data['username']}' creado exitosamente"
                )
                return redirect('listar_usuarios')
            else:
                messages.error(request, error_msg)
        else:
            # Mostrar errores de validación
            for field, error in errors.items():
                messages.error(request, f"{field.title()}: {error}")
    
    return render(request, "usuarios/nuevo_usuario.html")


@login_required
@user_passes_test(is_staff_user)
def editar_usuarios_view(request):
    """Vista para editar usuarios existentes"""
    user_service = UserService()
    
    if request.method == "POST":
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        if action == 'update_info':
            # Actualizar información del usuario
            data = {
                'first_name': request.POST.get('first_name', '').strip(),
                'last_name': request.POST.get('last_name', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'is_active': request.POST.get('is_active') == 'on',
                'is_staff': request.POST.get('is_staff') == 'on',
            }
            
            # Validar solo los datos de actualización
            validation_data = {
                'email': data['email'],
                'username': request.POST.get('username', '')  # Para validación
            }
            is_valid, errors = user_service.validate_user_data(
                validation_data, 
                is_update=True, 
                user_id=int(user_id)
            )
            
            if is_valid:
                success, error_msg = user_service.update_user_info(user_id, data)
                if success:
                    messages.success(request, "Usuario actualizado exitosamente")
                else:
                    messages.error(request, error_msg)
            else:
                for field, error in errors.items():
                    messages.error(request, f"{field.title()}: {error}")
        
        elif action == 'delete':
            # Eliminar usuario
            try:
                user = User.objects.get(id=user_id)
                username = user.username
                user.delete()
                messages.success(request, f"Usuario '{username}' eliminado exitosamente")
            except User.DoesNotExist:
                messages.error(request, "Usuario no encontrado")
            except Exception as e:
                messages.error(request, f"Error eliminando usuario: {str(e)}")
    
    # Obtener lista de usuarios para mostrar
    usuarios = user_service.get_user_list()
    
    return render(request, "usuarios/editar_usuarios.html", {"usuarios": usuarios})


@login_required
@user_passes_test(is_staff_user)
def admin_set_password_view(request, user_id):
    """Vista para que un admin cambie la contraseña de un usuario"""
    user_service = UserService()
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validaciones básicas
        if not new_password:
            messages.error(request, "La nueva contraseña es obligatoria")
        elif len(new_password) < 6:
            messages.error(request, "La contraseña debe tener al menos 6 caracteres")
        elif new_password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden")
        else:
            # Cambiar contraseña usando el servicio
            success, error_msg = user_service.update_user_password(user_id, new_password)
            
            if success:
                messages.success(
                    request, 
                    f"Contraseña actualizada exitosamente para '{target_user.username}'"
                )
                return redirect('listar_usuarios')
            else:
                messages.error(request, error_msg)
    
    context = {
        "target_user": target_user,
    }
    
    return render(request, "usuarios/admin_set_password.html", context)


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
        user_id = request.POST.get('user_id')
        user = User.objects.get(id=user_id)
        
        # Cambiar estado
        user.is_active = not user.is_active
        user.save()
        
        return JsonResponse({
            "success": True,
            "message": f"Usuario {'activado' if user.is_active else 'desactivado'} exitosamente",
            "is_active": user.is_active
        })
        
    except User.DoesNotExist:
        return JsonResponse({"error": "Usuario no encontrado"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Error interno: {str(e)}"}, status=500)