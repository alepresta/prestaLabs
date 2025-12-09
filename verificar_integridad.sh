#!/bin/bash
# Script para verificar integridad de la base de datos Django

source venv/bin/activate

# Ejecuta el chequeo de integridad de Django
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check

# Opcional: verifica usuarios duplicados
python manage.py shell <<EOF
from django.contrib.auth.models import User
from django.db.models import Count
repetidos = User.objects.values('username').annotate(c=Count('id')).filter(c__gt=1)
if repetidos:
    print('Usuarios duplicados:')
    for r in repetidos:
        print(r['username'])
else:
    print('No hay usuarios duplicados.')
EOF

echo "Integridad de la base de datos verificada."
