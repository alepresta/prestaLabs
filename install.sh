
#!/bin/bash

# Verificar que estamos en un proyecto Django
if [ ! -f "manage.py" ]; then
    echo "[ERROR] No se encontró manage.py. Asegúrate de estar en el directorio raíz del proyecto Django."
    exit 1
fi

function activar_entorno() {
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo "Entorno virtual activado."
    else
        echo "[ERROR] El entorno virtual no existe. Ejecuta './install.sh entorno' primero."
        exit 1
    fi
}

function crear_usuario_lectura() {
    activar_entorno
    echo "Ingrese el nombre de usuario de solo vista:"
    read -r USERNAME
    echo "Ingrese el email del usuario de solo vista:"
    read -r EMAIL
    echo "Ingrese la contraseña para $USERNAME:"
    read -r -s PASSWORD
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
        read -r -s PASSWORD
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
    git checkout static/ 2>/dev/null || echo "No se pudo restaurar static/, continuando..."
    python manage.py collectstatic --noinput
    echo "Caché de Django y archivos estáticos eliminados y regenerados."
    pkill -f "manage.py runserver" 2>/dev/null || true
    nohup python manage.py runserver 0.0.0.0:5001 >/dev/null 2>&1 &
    echo "Servidor Django reiniciado."
    echo "Recuerda hacer un hard refresh (Ctrl+F5) en tu navegador para limpiar la caché local."
}

function instalar_herramientas_calidad() {
    activar_entorno
    pip install --upgrade pip
    pip install pytest pytest-django factory-boy bandit pre-commit coverage
    pre-commit install
    echo "Herramientas de calidad y seguridad instaladas."
}

function iniciar_servidor() {
    activar_entorno
    echo "Iniciando servidor Django en puerto 5001..."
    python manage.py runserver 0.0.0.0:5001
}

function iniciar_celery() {
    activar_entorno
    echo "Iniciando worker de Celery..."
    if command -v celery >/dev/null 2>&1; then
        celery -A prestaLabs worker --loglevel=info
    else
        echo "Celery no está instalado. Instálalo primero con: pip install celery"
    fi
}

function cerrar_entorno() {
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        deactivate
        echo "Entorno virtual desactivado."
    else
        echo "No hay entorno virtual activo."
    fi
}

function instalar_redis() {
    echo "Instalando Redis..."
    sudo apt update && sudo apt install -y redis-server
    sudo service redis-server start
    echo "Redis instalado y ejecutándose."
}

function actualizar_codigo() {
    if [ -f nohup.out ]; then
        echo "Eliminando nohup.out para evitar conflictos de git..."
        rm nohup.out
    fi
    echo "Actualizando código desde origin/main..."
    git pull origin main
    echo "Código actualizado."
}

function instalar_todo() {
    echo -e "\n========== INICIO INSTALACIÓN COMPLETA =========="
    # Cerrar proceso en puerto 5001 si existe
    PID=$(lsof -ti:5001 2>/dev/null || true)
    if [ ! -z "$PID" ] && [ "$PID" != "true" ]; then
        echo "Matando proceso en puerto 5001 (PID: $PID)"
        kill -9 $PID 2>/dev/null || true
    fi
    # Eliminar logs de nohup antes de la instalación para evitar conflictos de git
    if [ -f nohup.out ]; then
        echo "Eliminando nohup.out para evitar conflictos de git..."
        rm nohup.out
    fi

    echo "Actualizando código desde origin/main..."
    if git pull origin main; then
        echo "Código actualizado correctamente."
    else
        echo "[ERROR] Falló la actualización de código. Verifica tu conexión o permisos de git."
        exit 1
    fi
    echo "[INSTALAR] Creando entorno virtual..."
    crear_entorno
    echo "[INSTALAR] Instalando dependencias..."
    instalar_dependencias
    echo "[INSTALAR] Copiando archivo .env..."
    copiar_env
    echo "[INSTALAR] Ejecutando migraciones..."
    migrar_db
    echo "[INSTALAR] Creando superusuario..."
    crear_superusuario
    echo "[INSTALAR] Recolectando archivos estáticos..."
    recolectar_estaticos
    echo "[INSTALAR] Borrando caché y reiniciando servidor..."
    borrar_cache
    echo -e "\n========== INSTALACIÓN COMPLETA =========="
    echo "Puedes cerrar la terminal, la app PrestaLabs seguirá corriendo en segundo plano."
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



function crear_entorno() {
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "Entorno virtual creado."
    else
        echo "El entorno virtual ya existe."
    fi
}

function instalar_dependencias() {
    activar_entorno
    if [ -f requirements.txt ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
        echo "Dependencias instaladas."
    else
        echo "No se encontró requirements.txt."
    fi
}

function copiar_env() {
    if [ -f .env.example ] && [ ! -f .env ]; then
        cp .env.example .env
        echo "Archivo .env copiado desde .env.example."
    elif [ -f .env ]; then
        echo "El archivo .env ya existe."
    else
        echo "No se encontró .env.example para copiar."
    fi
}

function migrar_db() {
    activar_entorno
    python manage.py makemigrations
    python manage.py migrate
    echo "Migraciones aplicadas."
}

function recolectar_estaticos() {
    activar_entorno
    python manage.py collectstatic --noinput
    echo "Archivos estáticos recolectados."
}

function reiniciar_servidor() {
    pkill -f "manage.py runserver" 2>/dev/null || true
    echo "Servidor Django detenido. Reiniciando en puerto 5001..."
    activar_entorno
    nohup python manage.py runserver 0.0.0.0:5001 > nohup.out 2>&1 &
    echo "Servidor Django iniciado en segundo plano en puerto 5001. Puedes cerrar la terminal y la app seguirá corriendo."
}

case "$1" in
    calidad)
        instalar_herramientas_calidad
        ;;
    entorno)
        crear_entorno
        ;;
    dependencias)
        instalar_dependencias
        ;;
    env)
        copiar_env
        ;;
    migrar)
        migrar_db
        ;;
    superusuario)
        crear_superusuario
        ;;
    servidor)
        iniciar_servidor
        ;;
    reiniciar_servidor)
        reiniciar_servidor
        ;;
    celery)
        iniciar_celery
        ;;
    cerrar)
        cerrar_entorno
        ;;
    redis)
        instalar_redis
        ;;
    estaticos)
        recolectar_estaticos
        ;;
    borrar_cache)
        borrar_cache
        ;;
    actualizar)
        actualizar_codigo
        ;;
    usuario_lectura)
        crear_usuario_lectura
        ;;
    integridad)
        bash verificar_integridad.sh
        ;;
    todo)
        instalar_todo
        ;;
    ayuda|*)
        ayuda
        ;;
esac