| todo            | Ejecuta todos los pasos de instalación            |
#### Instalación completa con un solo comando

```bash
./install.sh todo
```
# PrestaLabs

## Descripción
Proyecto Django para laboratorio de desarrollo.

## Instalación rápida

```bash
chmod +x install.sh
./install.sh todo
```

## Comandos disponibles en install.sh

| Comando         | Descripción                                      |
|-----------------|--------------------------------------------------|
| entorno         | Crear y activar entorno virtual                   |
| dependencias    | Instalar dependencias del proyecto                |
| env             | Copiar archivo .env de ejemplo                    |
| migrar          | Ejecutar migraciones de la base de datos          |
| superusuario    | Crear superusuario de Django                      |
| servidor        | Iniciar servidor de desarrollo Django             |
| reiniciar_servidor | Reiniciar el servidor Django en segundo plano  |
| celery          | Iniciar worker de Celery                          |
| cerrar          | Desactivar entorno virtual                        |
| redis           | Instalar y ejecutar Redis                         |
| estaticos       | Recolectar archivos estáticos                     |
| borrar_cache    | Eliminar caché (__pycache__)                      |
| actualizar      | Actualizar código con git pull origin main        |
| usuario_lectura | Crear usuario de solo vista (lectura, sin admin)  |
| integridad      | Verificar integridad de la base de datos          |
| todo            | Ejecuta todos los pasos de instalación            |
| ayuda           | Mostrar esta ayuda                                |

## Estructura de tests y cobertura

- Todos los tests automáticos están en la raíz de la app `core/` y siguen el patrón `test_*.py`.
- Cobertura:
  - Formularios (`test_all.py`)
  - Modelos (`test_all.py`)
  - Vistas y redirecciones (`test_all.py`)
  - API (`test_all.py`)
  - Scripts (`test_scripts.py`)
- Para ejecutar todos los tests:

```bash
source venv/bin/activate
python manage.py test core
```

## Buenas prácticas

- Mantén los tests en archivos separados o unificados en la raíz de la app.
- No uses carpetas `tests/` con `__init__.py` para evitar conflictos de importación.
- Limpia caché con `find core -name '__pycache__' -type d -exec rm -rf {} +` si hay problemas de importación.

## Proceso de refactorización y automatización

1. Limpieza y refactorización de código: imports, docstrings, separación de formularios.
2. Reorganización de apps y estructura: formularios y utilidades en archivos dedicados.
3. Conversión de vistas a CBV.
4. Mejoras de seguridad y validaciones: mensajes de Django, permisos.
5. Automatización y scripts: gestión centralizada y chequeos de integridad.
6. Tests automáticos: cobertura completa y estructura estándar.

## Comandos útiles para calidad y seguridad

### Testing y cobertura
```bash
source venv/bin/activate
pytest                # Ejecuta todos los tests con pytest
coverage run --source=core manage.py test core  # Ejecuta tests y mide cobertura
coverage report -m   # Muestra reporte de cobertura
```

### Seguridad
```bash
bandit -r core       # Analiza seguridad del código Python
```

### Formato y lint automático
```bash
pre-commit run --all-files   # Ejecuta Black, Flake8 y Bandit en todo el repo
```

### Buenas prácticas finales
- Mantén los tests en la raíz de cada app, sin carpetas `tests/` con `__init__.py`.
- Usa Factory Boy para datos de prueba complejos.
- No uses contraseñas hardcodeadas fuera de tests.
- Usa subprocess solo en tests y nunca con datos no controlados.
- Integra estos comandos en tu CI/CD para máxima calidad.

---

¡Proyecto listo para desarrollo profesional, testing avanzado y despliegue seguro!

---

¿Dudas? Consulta los comandos de ayuda o revisa los tests para ejemplos de uso.