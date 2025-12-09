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
    borrar_cache)
        borrar_cache
        ;;
    actualizar)
        actualizar_codigo
        ;;
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
    python manage.py createsuperuser
}

function iniciar_servidor() {
    activar_entorno
    echo "Iniciando servidor Django..."
    python manage.py runserver
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

function ayuda() {
    echo "\nOpciones disponibles:"
    echo "  entorno        - Crear y activar entorno virtual"
    echo "  dependencias   - Instalar dependencias"
    echo "  env            - Copiar archivo .env"
    echo "  migrar         - Ejecutar migraciones"
    echo "  superusuario   - Crear superusuario"
    echo "  servidor       - Iniciar servidor Django"
    echo "  celery         - Iniciar worker Celery"
    echo "  cerrar         - Desactivar entorno virtual"
    echo "  redis          - Instalar y ejecutar Redis"
    echo "  estaticos      - Recolectar archivos estáticos"
    echo "  ayuda          - Mostrar esta ayuda"
    echo "\nEjemplo: ./install.sh entorno"
}

case "$1" in
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
    ayuda|*)
        ayuda
        ;;
esac
