#!/usr/bin/env python
"""
Script para probar el endpoint de analisis_estado mejorado
"""
import os
import sys
import json

# Configurar Django
sys.path.append('/workspaces/prestaLabs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prestaLabs.settings')

import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from core.views.analisis_estado import analisis_estado


def test_analisis_estado():
    # Crear factory para requests
    factory = RequestFactory()

    # Crear request con parámetros y header AJAX - probar un dominio que sabemos tiene resultados
    request = factory.get(
        "/analisis/estado/",
        {"dominio": "https://metas.argentina.gob.ar/"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    # Agregar sesión al request
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    # Asignar usuario
    try:
        request.user = User.objects.first()
        print(f"✅ Usuario asignado: {request.user.username}")
    except Exception:
        request.user = None
        print("⚠️  Sin usuario")

    # Llamar a la función
    try:
        response = analisis_estado(request)
        print(f"✅ Status Code: {response.status_code}")

        if response.status_code == 200:
            print(f"📊 Response content raw: {response.content}")
            if response.content:
                data = json.loads(response.content)
                print("📊 Response JSON:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print("❌ Response content está vacío")

            # Verificar campos clave para recuperación de sesión
            if "progreso" in data and data["progreso"]:
                progreso = data["progreso"]
                print("\n🔍 VERIFICACIÓN DE CAMPOS PARA RECUPERACIÓN DE SESIÓN:")
                campos_requeridos = [
                    "porcentaje",
                    "count",
                    "urls",
                    "hora_inicio",
                    "hora_fin",
                    "duracion",
                ]

                for campo in campos_requeridos:
                    if campo in progreso:
                        print(f"  ✅ {campo}: {progreso[campo]}")
                    else:
                        print(f"  ❌ {campo}: NO ENCONTRADO")

                # Verificar URLs
                if "urls" in progreso and progreso["urls"]:
                    urls_count = len(progreso["urls"])
                    print(f"  ✅ URLs disponibles: {urls_count}")
                    print(f'     Primeras 3: {progreso["urls"][:3]}')
                else:
                    print("  ❌ URLs: NO HAY URLs DISPONIBLES")

        else:
            print(f"❌ Error Response ({response.status_code}):")
            print(response.content.decode())

    except Exception as e:
        print(f"❌ Error ejecutando función: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 PROBANDO ENDPOINT DE ANÁLISIS DE ESTADO MEJORADO")
    print("=" * 60)
    test_analisis_estado()
