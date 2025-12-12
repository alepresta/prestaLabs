#!/usr/bin/env python
"""
Script de prueba para verificar la funcionalidad de recuperación de sesión
"""

import requests
import json
from datetime import datetime


def test_estado_endpoint():
    """Probar el endpoint /analisis/estado/"""

    # Simular una petición AJAX como hace el navegador
    url = "http://localhost:8000/analisis/estado/"
    headers = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Respuesta JSON recibida:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            # Verificar estructura esperada
            if "progreso" in data:
                progreso = data["progreso"]
                print(f"\n📊 Datos del progreso:")
                print(f"  - Dominio: {progreso.get('dominio', 'N/A')}")
                print(f"  - Total URLs: {progreso.get('total', 0)}")
                print(f"  - Porcentaje: {progreso.get('porcentaje', 0)}%")
                print(f"  - URLs disponibles: {len(progreso.get('urls', []))}")
                print(f"  - Hora inicio: {progreso.get('hora_inicio', 'N/A')}")
                print(f"  - Hora fin: {progreso.get('hora_fin', 'N/A')}")
                print(f"  - Duración: {progreso.get('duracion', 'N/A')}")

                if progreso.get("urls"):
                    print(f"\n🔗 Primeras 3 URLs encontradas:")
                    for i, url in enumerate(progreso.get("urls", [])[:3], 1):
                        print(f"  {i}. {url}")
            else:
                print("⚠️  No se encontró información de progreso")

        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(response.text[:500])

    except Exception as e:
        print(f"❌ Error en la petición: {str(e)}")


def test_crawling_activo():
    """Probar el endpoint /crawling/activo/"""

    url = "http://localhost:8000/crawling/activo/"

    try:
        response = requests.get(url, timeout=10)
        print(f"\n🔄 Endpoint crawling activo - Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("Respuesta:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"Error: {response.text[:200]}")

    except Exception as e:
        print(f"Error: {str(e)}")


def main():
    print("🧪 PRUEBA DE RECUPERACIÓN DE SESIÓN")
    print("=" * 50)
    print(f"Hora de prueba: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("1️⃣  Probando endpoint /analisis/estado/")
    print("-" * 30)
    test_estado_endpoint()

    print("\n2️⃣  Probando endpoint /crawling/activo/")
    print("-" * 30)
    test_crawling_activo()

    print("\n✅ Pruebas completadas")
    print("\nINSTRUCCIONES PARA PRUEBA MANUAL:")
    print("1. Abre el navegador en http://localhost:8000")
    print("2. Inicia un crawling de argentina.gob.ar")
    print("3. Espera a que termine (verás 'Finalizado correctamente')")
    print("4. Cierra la pestaña del navegador")
    print("5. Abre una nueva pestaña en http://localhost:8000")
    print("6. Deberías ver todo el progreso completo visible:")
    print("   - Barra de progreso al 100%")
    print("   - Información de tiempo (inicio, fin, duración)")
    print("   - Contador de URLs encontradas")
    print("   - Lista completa de URLs")
    print("   - Estado 'Completado' con ✓ verde")


if __name__ == "__main__":
    main()
