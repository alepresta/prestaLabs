function crear_usuario_lectura() {
    activar_entorno
    echo "Ingrese el nombre de usuario de solo vista:"
    read USERNAME
    echo "Ingrese el email del usuario de solo vista:"
    read EMAIL
    echo "Ingrese la contraseña para $USERNAME:"
    read -s PASSWORD
    python manage.py shell <<EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='$USERNAME').exists():
    user = User.objects.create_user('$USERNAME', email='$EMAIL', password='$PASSWORD')
    user.is_staff = False
    user.save()
    print('Usuario de solo vista creado: $USERNAME')
else:
    print('El usuario "$USERNAME" ya existe.')
EOF
}

function crear_superusuario() {
    activar_entorno
    USERNAME="usuario_demo"
    EMAIL="demo@ejemplo.com"
    EXISTE=$(python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.filter(username='$USERNAME').exists())")
    if [ "$EXISTE" = "False" ]; then
        echo "Ingrese la contraseña para el superusuario ($USERNAME):"
        read -s PASSWORD
        python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_superuser('$USERNAME', '$EMAIL', '$PASSWORD')
print('Superusuario creado: $USERNAME')
EOF
        echo "Superusuario creado: $USERNAME"
    else
        echo "El superusuario '$USERNAME' ya existe."
    fi
}

function borrar_cache() {
    activar_entorno
    echo "Borrando caché de Django, archivos __pycache__ y estáticos..."
    python manage.py shell -c "from django.core.cache import cache; cache.clear()"
    find . -type d -name '__pycache__' -exec rm -rf {} +
    if [ -d staticfiles ]; then
        rm -rf staticfiles/*
        echo "Carpeta staticfiles/ limpiada."
    fi
    git checkout static/
    python manage.py collectstatic --noinput
    echo "Caché de Django y archivos estáticos eliminados y regenerados."
    pkill -f "manage.py runserver" || true
    nohup python manage.py runserver 0.0.0.0:5001 &
    echo "Servidor Django reiniciado."
    echo "Recuerda hacer un hard refresh (Ctrl+F5) en tu navegador para limpiar la caché local."
}

function ayuda() {
    echo "Opciones disponibles:"
    echo "  calidad            - Instalar herramientas de calidad y seguridad (pytest, bandit, pre-commit, coverage)"
    echo "  entorno            - Crear entorno virtual"
    echo "  dependencias       - Instalar dependencias"
    echo "  env                - Copiar archivo .env"
    echo "  migrar             - Ejecutar migraciones"
    echo "  superusuario       - Crear superusuario"
    echo "  servidor           - Iniciar servidor Django"
    echo "  reiniciar_servidor - Reiniciar el servidor Django en segundo plano"
    echo "  celery             - Iniciar worker Celery"
    echo "  cerrar             - Desactivar entorno virtual"
    echo "  redis              - Instalar y ejecutar Redis"
    echo "  estaticos          - Recolectar archivos estáticos"
    echo "  borrar_cache       - Limpiar caché de Django, archivos __pycache__ y estáticos"
    echo "  actualizar         - Actualizar código con git pull origin main"
    echo "  usuario_lectura    - Crear usuario de solo vista (lectura, sin acceso admin)"
    echo "  integridad         - Verificar integridad de la base de datos"
    echo "  todo               - Ejecutar todos los pasos de instalación (incluye limpieza de caché)"
    echo "  ayuda              - Mostrar esta ayuda"
    echo ""
    echo "Ejemplo: ./install.sh entorno"
}