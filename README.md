# PrestaLabs

## Descripción
Proyecto Django para laboratorio de desarrollo.

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/alepresta/prestaLabs.git
cd prestaLabs
```

2. Crea un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. Configura las variables de entorno:
```bash
cp .env.example .env
# Edita el archivo .env con tus configuraciones
```

5. Ejecuta las migraciones:
```bash
python manage.py migrate
```

6. Crea un superusuario (opcional):
```bash
python manage.py createsuperuser
```

7. Inicia el servidor de desarrollo:
```bash
python manage.py runserver
```

## Estructura del proyecto
```
prestaLabs/
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## Contribución
1. Fork el proyecto
2. Crea una nueva rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request