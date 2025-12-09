function instalar_herramientas_calidad() {
    echo "Instalando herramientas de calidad y seguridad (pytest, pytest-django, factory-boy, bandit, pre-commit, coverage)..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install pytest pytest-django factory-boy bandit pre-commit coverage
    pre-commit install
    echo "Herramientas instaladas y pre-commit configurado."
}
#!/bin/bash

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
function reiniciar_servidor() {
    # Buscar y matar cualquier proceso en el puerto 5001
    PID=$(lsof -ti:5001)
    if [ ! -z "$PID" ]; then
        echo "Matando proceso en puerto 5001 (PID: $PID)"
        kill -9 $PID
    fi
    pkill -f "manage.py runserver" || true
    echo "Servidor Django detenido. Reiniciando en puerto 5001..."
    activar_entorno
    nohup python manage.py runserver 0.0.0.0:5001 &
    echo "Servidor Django iniciado en segundo plano en puerto 5001."
}

#!/bin/bash
# Script de instalación y gestión para PrestaLabs
# Uso: ./install.sh [opción]

set -e

PROYECTO="prestaLabs"
VENV="venv"


function crear_entorno() {
    echo "Creando entorno virtual..."
    python3 -m venv $VENV
    source $VENV/bin/activate
    echo "Entorno virtual activado."
}

function activar_entorno() {
    source $VENV/bin/activate
    echo "Entorno virtual activado."
}

function instalar_dependencias() {
    activar_entorno
    echo "Instalando dependencias..."
    pip install -r requirements.txt
}

function copiar_env() {
    if [ ! -f .env ]; then
        cp .env.example .env
        echo "Archivo .env copiado. Edita tus configuraciones."
    else
        echo ".env ya existe."
    fi
}

function migrar_db() {
    activar_entorno
    echo "Ejecutando migraciones..."
    python manage.py migrate
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

function iniciar_servidor() {
    activar_entorno
    echo "Iniciando servidor Django en puerto 5001..."
    python manage.py runserver 0.0.0.0:5001
}

function reiniciar_servidor() {
    pkill -f "manage.py runserver" || true
    echo "Servidor Django detenido. Reiniciando en puerto 5001..."
    activar_entorno
    nohup python manage.py runserver 0.0.0.0:5001 &
    echo "Servidor Django iniciado en segundo plano en puerto 5001."
}

function iniciar_celery() {
    activar_entorno
    echo "Iniciando worker de Celery..."
    celery -A $PROYECTO worker --loglevel=info
}

function cerrar_entorno() {
    deactivate
    echo "Entorno virtual desactivado."
}

function instalar_redis() {
    echo "Instalando Redis..."
    sudo apt update && sudo apt install -y redis-server
    sudo service redis-server start
    echo "Redis instalado y ejecutándose."
}

function recolectar_estaticos() {
    activar_entorno
    python manage.py collectstatic
}

function borrar_cache() {
    echo "Borrando caché (__pycache__)..."
    find . -type d -name '__pycache__' -exec rm -rf {} +
    echo "Caché eliminada."
}

function actualizar_codigo() {
    echo "Actualizando código desde origin/main..."
    git pull origin main
    echo "Código actualizado."
}

function instalar_todo() {
    echo "Actualizando código desde origin/main..."
    git pull origin main
    crear_entorno
    instalar_dependencias
    copiar_env
    migrar_db
    crear_superusuario
    recolectar_estaticos
    reiniciar_servidor
    echo "\nInstalación completa y servidor iniciado."
}

function ayuda() {
    echo "\nOpciones disponibles:"
    echo "  entorno        - Crear y activar entorno virtual"
    echo "  dependencias   - Instalar dependencias"
    echo "  env            - Copiar archivo .env"
    echo "  migrar         - Ejecutar migraciones"
    echo "  superusuario   - Crear superusuario"
    echo "  servidor       - Iniciar servidor Django"
    echo "  reiniciar_servidor - Reiniciar el servidor Django en segundo plano"
    echo "  celery         - Iniciar worker Celery"
    echo "  cerrar         - Desactivar entorno virtual"
    echo "  redis          - Instalar y ejecutar Redis"
    echo "  estaticos      - Recolectar archivos estáticos"
    echo "  borrar_cache   - Eliminar caché (__pycache__)"
    echo "  actualizar     - Actualizar código con git pull origin main"
    echo "  usuario_lectura - Crear usuario de solo vista (lectura, sin acceso admin)"
    echo "  integridad     - Verificar integridad de la base de datos"
    echo "  todo           - Ejecutar todos los pasos de instalación"
    echo "  calidad        - Instalar herramientas de calidad y seguridad (pytest, bandit, pre-commit, coverage)"
    echo "  ayuda          - Mostrar esta ayuda"
    echo "\nEjemplo: ./install.sh entorno"
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
