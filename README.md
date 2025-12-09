| todo            | Ejecuta todos los pasos de instalación            |
#### Instalación completa con un solo comando

```bash
./install.sh todo
```
# PrestaLabs

## Descripción
Proyecto Django para laboratorio de desarrollo.

## Instalación

1. Clona el repositorio:

## Instalación rápida con script

Puedes usar el script `install.sh` para automatizar la instalación y gestión del proyecto en Linux:

```bash
chmod +x install.sh
./install.sh ayuda
```

### Comandos disponibles en install.sh


| Comando         | Descripción                                      |
|-----------------|--------------------------------------------------|
| entorno         | Crear y activar entorno virtual                   |
| dependencias    | Instalar dependencias del proyecto                |
| env             | Copiar archivo .env de ejemplo                    |
| migrar          | Ejecutar migraciones de la base de datos          |
| superusuario    | Crear superusuario de Django                      |
| servidor        | Iniciar servidor de desarrollo Django             |
| celery          | Iniciar worker de Celery                          |
| cerrar          | Desactivar entorno virtual                        |
| redis           | Instalar y ejecutar Redis                         |
| estaticos       | Recolectar archivos estáticos para producción     |
| borrar_cache    | Eliminar caché (__pycache__) de Python            |
| actualizar      | Actualizar código con git pull origin main        |
| ayuda           | Mostrar ayuda y comandos disponibles              |

#### Ejemplos de uso de comandos

```bash
# Crear y activar entorno virtual
./install.sh entorno

# Instalar dependencias
./install.sh dependencias

# Copiar archivo .env de ejemplo
./install.sh env

# Ejecutar migraciones
./install.sh migrar

# Crear superusuario
./install.sh superusuario

# Iniciar servidor de desarrollo
./install.sh servidor

# Iniciar worker de Celery
./install.sh celery

# Desactivar entorno virtual
./install.sh cerrar

# Instalar y ejecutar Redis
./install.sh redis

# Recolectar archivos estáticos
./install.sh estaticos

# Eliminar caché (__pycache__)
./install.sh borrar_cache

# Actualizar código desde origin/main
./install.sh actualizar

# Mostrar ayuda
./install.sh ayuda
```


Instalación completa con un solo comando:
```bash
./install.sh todo
```

Para tareas en segundo plano:
```bash
./install.sh redis
./install.sh celery
```

---

### 1. Clonar el repositorio
```bash
git clone https://github.com/alepresta/prestaLabs.git
cd prestaLabs
```

### 2. Crear y activar entorno virtual
#### Linux/MacOS:
```bash
python3 -m venv venv
source venv/bin/activate
```
#### Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
cp .env.example .env
# Edita el archivo .env con tus configuraciones
```
En Windows:
```powershell
copy .env.example .env
```

#### Ejemplo de archivo .env
```env
SECRET_KEY=tu-clave-secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
REDIS_URL=redis://localhost:6379/0
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
```

### 5. Ejecutar migraciones de la base de datos
```bash
python manage.py migrate
```

### 6. Crear superusuario (opcional)
```bash
python manage.py createsuperuser
```

### 7. Iniciar el servidor de desarrollo
```bash
python manage.py runserver
```

### 8. Probar la API y vistas
- Accede a `http://localhost:8000/` para la vista principal.
- Accede a `http://localhost:8000/status/` para el estado de la API.
- Accede a `http://localhost:8000/admin/` para el panel de administración.

### 9. Ejecutar pruebas automáticas
```bash
python manage.py test
```

### 10. Uso de Celery (tareas en segundo plano)
Para usar Celery necesitas tener Redis corriendo:
```bash
sudo apt install redis-server   # Linux
sudo service redis-server start # Linux
# En Windows, instala Redis desde https://github.com/microsoftarchive/redis/releases
```
Luego, inicia el worker de Celery:
```bash
celery -A prestaLabs worker --loglevel=info
```

### 11. Recolección de archivos estáticos para producción
```bash
python manage.py collectstatic
```

---

## Notas importantes
- El proyecto requiere Python 3.8 o superior.
- Celery y Redis son necesarios para tareas en segundo plano.
- Si usas Linux, todos los comandos funcionan tal cual están escritos.
- En Windows, usa PowerShell para activar el entorno y copiar archivos.
- Para producción, configura correctamente las variables de entorno y desactiva DEBUG.

## Estructura del proyecto
```
prestaLabs/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
├── core/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── views.py
│   └── urls.py
├── prestaLabs/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── static/
├── media/
├── templates/
│   └── base.html
└── ...
```

## Contribución
1. Haz fork del proyecto
2. Crea una nueva rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request