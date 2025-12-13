"""
Servicio de gestión de usuarios.

Contiene toda la lógica de negocio para operaciones de usuarios.
"""

from django.contrib.auth.models import User
from django.utils import timezone


class UserService:
    """Servicio principal para operaciones de usuarios"""

    def create_user(self, username, email, password, first_name="", last_name=""):
        """
        Crea un nuevo usuario.
        
        Args:
            username (str): Nombre de usuario
            email (str): Email del usuario
            password (str): Contraseña
            first_name (str): Nombre
            last_name (str): Apellido
            
        Returns:
            tuple: (user, created, error_message)
        """
        try:
            # Verificar si ya existe
            if User.objects.filter(username=username).exists():
                return None, False, f"El usuario '{username}' ya existe"
            
            if User.objects.filter(email=email).exists():
                return None, False, f"El email '{email}' ya está registrado"

            # Crear usuario
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            return user, True, None
            
        except Exception as e:
            return None, False, f"Error creando usuario: {str(e)}"

    def update_user_password(self, user_id, new_password):
        """
        Actualiza la contraseña de un usuario.
        
        Args:
            user_id (int): ID del usuario
            new_password (str): Nueva contraseña
            
        Returns:
            tuple: (success, error_message)
        """
        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            return True, None
        except User.DoesNotExist:
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, f"Error actualizando contraseña: {str(e)}"

    def get_user_list(self, search_query=None):
        """
        Obtiene lista de usuarios con filtros opcionales.
        
        Args:
            search_query (str, optional): Término de búsqueda
            
        Returns:
            QuerySet: Lista de usuarios
        """
        queryset = User.objects.all().order_by('-date_joined')
        
        if search_query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
            
        return queryset

    def update_user_info(self, user_id, data):
        """
        Actualiza información de un usuario.
        
        Args:
            user_id (int): ID del usuario
            data (dict): Datos a actualizar
            
        Returns:
            tuple: (success, error_message)
        """
        try:
            user = User.objects.get(id=user_id)
            
            # Campos permitidos para actualizar
            allowed_fields = ['first_name', 'last_name', 'email', 'is_active', 'is_staff']
            
            for field in allowed_fields:
                if field in data:
                    setattr(user, field, data[field])
            
            user.save()
            return True, None
            
        except User.DoesNotExist:
            return False, "Usuario no encontrado"
        except Exception as e:
            return False, f"Error actualizando usuario: {str(e)}"

    def validate_user_data(self, data, is_update=False, user_id=None):
        """
        Valida datos de usuario antes de crear/actualizar.
        
        Args:
            data (dict): Datos del usuario
            is_update (bool): True si es actualización
            user_id (int, optional): ID del usuario en caso de actualización
            
        Returns:
            tuple: (is_valid, errors_dict)
        """
        errors = {}
        
        # Validar username
        username = data.get('username', '').strip()
        if not username:
            errors['username'] = 'El nombre de usuario es obligatorio'
        elif len(username) < 3:
            errors['username'] = 'El nombre de usuario debe tener al menos 3 caracteres'
        elif not is_update or (is_update and user_id):
            # Verificar duplicados
            existing_user = User.objects.filter(username=username)
            if is_update and user_id:
                existing_user = existing_user.exclude(id=user_id)
            if existing_user.exists():
                errors['username'] = 'Este nombre de usuario ya existe'
        
        # Validar email
        email = data.get('email', '').strip()
        if not email:
            errors['email'] = 'El email es obligatorio'
        else:
            import re
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                errors['email'] = 'El formato del email no es válido'
            else:
                # Verificar duplicados
                existing_user = User.objects.filter(email=email)
                if is_update and user_id:
                    existing_user = existing_user.exclude(id=user_id)
                if existing_user.exists():
                    errors['email'] = 'Este email ya está registrado'
        
        # Validar password (solo para creación)
        if not is_update:
            password = data.get('password', '')
            if not password:
                errors['password'] = 'La contraseña es obligatoria'
            elif len(password) < 6:
                errors['password'] = 'La contraseña debe tener al menos 6 caracteres'
        
        return len(errors) == 0, errors

    def get_user_stats(self):
        """
        Obtiene estadísticas básicas de usuarios.
        
        Returns:
            dict: Estadísticas de usuarios
        """
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        staff_users = User.objects.filter(is_staff=True).count()
        
        # Usuarios registrados en los últimos 30 días
        from datetime import timedelta
        last_30_days = timezone.now() - timedelta(days=30)
        recent_users = User.objects.filter(date_joined__gte=last_30_days).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'staff_users': staff_users,
            'recent_users': recent_users,
        }