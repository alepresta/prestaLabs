
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

function cerrar_procesos() {
    echo -e "\n========== CERRANDO PROCESOS ACTIVOS =========="
    
    # 1. Cerrar procesos Django en puerto 5001
    echo "[STOP] Buscando procesos en puerto 5001..."
    PID=$(lsof -ti:5001 2>/dev/null || true)
    if [ ! -z "$PID" ] && [ "$PID" != "true" ]; then
        echo "[STOP] Matando proceso Django en puerto 5001 (PID: $PID)"
        kill -TERM $PID 2>/dev/null || true
        sleep 3
        # Si aún existe, forzar
        if kill -0 $PID 2>/dev/null; then
            echo "[STOP] Forzando cierre del proceso $PID"
            kill -9 $PID 2>/dev/null || true
        fi
    else
        echo "[INFO] No hay procesos activos en puerto 5001"
    fi
    
    # 2. Cerrar procesos Django por nombre
    echo "[STOP] Cerrando procesos Django (manage.py runserver)..."
    pkill -f "manage.py runserver" 2>/dev/null || true
    
    # 3. Cerrar procesos Celery si existen
    echo "[STOP] Cerrando procesos Celery..."
    pkill -f "celery worker" 2>/dev/null || true
    pkill -f "celery beat" 2>/dev/null || true
    
    # 4. Cerrar procesos Python relacionados con PrestaLabs
    echo "[STOP] Cerrando otros procesos Python del proyecto..."
    pkill -f "prestaLabs" 2>/dev/null || true
    
    # 5. Limpiar archivos temporales
    echo "[CLEAN] Limpiando archivos temporales..."
    if [ -f nohup.out ]; then
        rm nohup.out
        echo "[CLEAN] Eliminado nohup.out"
    fi
    
    if [ -f celery.pid ]; then
        rm celery.pid
        echo "[CLEAN] Eliminado celery.pid"
    fi
    
    # 6. Verificar que los procesos se cerraron
    sleep 2
    REMAINING=$(ps aux | grep -E "(manage.py|celery)" | grep -v grep | wc -l)
    if [ "$REMAINING" -gt 0 ]; then
        echo "[WARN] Aún quedan $REMAINING procesos relacionados activos"
        ps aux | grep -E "(manage.py|celery)" | grep -v grep
    else
        echo "[OK] Todos los procesos fueron cerrados exitosamente"
    fi
    
    echo "========== PROCESOS CERRADOS =========="
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
    
    # PASO 1: Cerrar todos los procesos activos antes del deploy
    echo "[PRE-DEPLOY] Limpiando procesos activos..."
    cerrar_procesos
    
    # PASO 2: Actualizar código
    echo "[DEPLOY] Actualizando código desde origin/main..."
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
    echo "  cerrar_procesos    - Cerrar todos los procesos activos (Django, Celery, etc.)"
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
    echo "[MIGRATE] Verificando estado de migraciones..."
    
    # Mostrar migraciones pendientes
    python manage.py showmigrations --plan | grep -E '\[ \]' && echo "[INFO] Hay migraciones pendientes" || echo "[INFO] No hay migraciones pendientes"
    
    echo "[MIGRATE] Ejecutando makemigrations..."
    if python manage.py makemigrations; then
        echo "[OK] Makemigrations completado"
    else
        echo "[ERROR] Falló makemigrations"
        exit 1
    fi
    
    echo "[MIGRATE] Ejecutando migrate..."
    if python manage.py migrate; then
        echo "[OK] Migraciones aplicadas correctamente"
        
        # Verificar que las tablas críticas existen
        echo "[VERIFY] Verificando integridad de la base de datos..."
        python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
try:
    cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'core_%';\")
    tables = [row[0] for row in cursor.fetchall()]
    print(f'[OK] Tablas core encontradas: {len(tables)}')
    for table in sorted(tables):
        print(f'  - {table}')
    
    # Verificar tabla específica que causaba problemas
    if 'core_analisisurlindividual' in tables:
        print('[OK] Tabla core_analisisurlindividual existe correctamente')
    else:
        print('[WARN] Tabla core_analisisurlindividual no encontrada')
        
except Exception as e:
    print(f'[ERROR] Error verificando tablas: {e}')
    exit(1)
" || echo "[WARN] No se pudo verificar integridad de tablas"
        
    else
        echo "[ERROR] Falló migrate"
        exit 1
    fi
}

function recolectar_estaticos() {
    activar_entorno
    python manage.py collectstatic --noinput
    echo "Archivos estáticos recolectados."
}

function reiniciar_servidor() {
    echo -e "\n========== REINICIANDO SERVIDOR =========="
    # Usar la función de cerrar procesos para una limpieza más completa
    cerrar_procesos
    
    echo "[START] Iniciando servidor Django en puerto 5001..."
    activar_entorno
    nohup python manage.py runserver 0.0.0.0:5001 > nohup.out 2>&1 &
    
    # Verificar que el servidor inició correctamente
    sleep 3
    PID=$(lsof -ti:5001 2>/dev/null || true)
    if [ ! -z "$PID" ] && [ "$PID" != "true" ]; then
        echo "[OK] Servidor Django iniciado correctamente (PID: $PID)"
        echo "[INFO] Accesible en http://localhost:5001"
        echo "[INFO] Logs en nohup.out"
    else
        echo "[ERROR] No se pudo iniciar el servidor Django"
        echo "[DEBUG] Verificar logs en nohup.out para más información"
    fi
    echo "========== SERVIDOR CONFIGURADO =========="
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
    cerrar_procesos)
        cerrar_procesos
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