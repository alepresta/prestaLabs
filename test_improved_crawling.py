#!/usr/bin/env python3
"""
Script para probar las mejoras del sistema de crawling
"""

import os
import django
import time

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prestaLabs.settings')
django.setup()

from core.views_app import crawl_urls


def test_improved_crawling():
    """Prueba el sistema mejorado con los dominios problemáticos"""
    dominios_test = [
        {'domain': 'jw.org', 'max_urls': 10, 'expected': 'blocked_fallback_sitemap'},
        {'domain': 'udemy.com', 'max_urls': 5, 'expected': 'blocked'},
        {'domain': 'example.com', 'max_urls': 5, 'expected': 'success'},  # Control
    ]
    
    print("🚀 PROBANDO SISTEMA DE CRAWLING MEJORADO")
    print("="*60)
    
    for test in dominios_test:
        domain = test['domain']
        max_urls = test['max_urls']
        
        print(f"\n🔍 Probando: {domain} (máximo {max_urls} URLs)")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            resultado = crawl_urls(f"https://{domain}", max_urls=max_urls)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if isinstance(resultado, dict):
                urls = resultado['urls']
                status = resultado['status']
                message = resultado['message']
                blocked_count = resultado.get('blocked_count', 0)
                
                print(f"✅ RESULTADO:")
                print(f"   Estado: {status}")
                print(f"   URLs encontradas: {len(urls)}")
                print(f"   Bloqueos detectados: {blocked_count}")
                print(f"   Tiempo total: {duration:.2f}s")
                print(f"   Mensaje: {message}")
                
                if len(urls) > 0:
                    print(f"   Primeras URLs:")
                    for i, url in enumerate(urls[:3]):
                        print(f"      {i+1}. {url}")
                
                # Verificar si cumple expectativas
                expected = test['expected']
                if expected == 'blocked_fallback_sitemap' and 'sitemap' in status:
                    print(f"   ✅ EXPECTATIVA CUMPLIDA: Usó sitemap como alternativa")
                elif expected == 'blocked' and blocked_count > 0:
                    print(f"   ✅ EXPECTATIVA CUMPLIDA: Detectó bloqueos correctamente")
                elif expected == 'success' and status == 'success':
                    print(f"   ✅ EXPECTATIVA CUMPLIDA: Crawling exitoso")
                else:
                    print(f"   ⚠️ RESULTADO INESPERADO: esperaba {expected}, obtuvo {status}")
                    
            else:
                # Formato legacy
                print(f"✅ RESULTADO (formato legacy):")
                print(f"   URLs encontradas: {len(resultado)}")
                print(f"   Tiempo total: {duration:.2f}s")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
        
        # Pausa entre tests para no sobrecargar servidores
        if domain != dominios_test[-1]['domain']:
            print(f"\n⏰ Pausa de 3 segundos antes del siguiente test...")
            time.sleep(3)
    
    print(f"\n{'='*60}")
    print("🏁 PRUEBAS COMPLETADAS")
    print("\n💡 ANÁLISIS:")
    print("- El sistema debería detectar bloqueos en jw.org y udemy.com")
    print("- Para jw.org debería intentar usar sitemap como alternativa")
    print("- Para example.com debería funcionar normalmente")
    print("- Los delays y User-Agents aleatorios deberían estar activos")


def test_user_agent_rotation():
    """Prueba la rotación de User-Agents"""
    print(f"\n🔄 PROBANDO ROTACIÓN DE USER-AGENTS")
    print("-" * 40)
    
    from core.views_app import get_random_headers
    
    headers_used = set()
    
    for i in range(10):
        headers = get_random_headers()
        user_agent = headers['User-Agent']
        headers_used.add(user_agent)
        print(f"   {i+1}. {user_agent[:50]}...")
    
    print(f"\n   ✅ Se usaron {len(headers_used)} User-Agents diferentes de 10 requests")
    if len(headers_used) > 5:
        print(f"   ✅ Buena variación en User-Agents")
    else:
        print(f"   ⚠️ Poca variación en User-Agents")


def test_blocking_detection():
    """Prueba el sistema de detección de bloqueos"""
    print(f"\n🛡️ PROBANDO DETECCIÓN DE BLOQUEOS")
    print("-" * 40)
    
    from core.views_app import detect_blocking
    import requests
    
    # Crear respuestas simuladas para probar
    class MockResponse:
        def __init__(self, status_code, text=""):
            self.status_code = status_code
            self.text = text
    
    test_cases = [
        (MockResponse(403, ""), "HTTP 403"),
        (MockResponse(429, ""), "HTTP 429"),
        (MockResponse(200, "blocked by cloudflare"), "Contenido de bloqueo"),
        (MockResponse(200, "captcha required"), "CAPTCHA"),
        (MockResponse(200, "a" * 50), "Respuesta pequeña"),
        (MockResponse(200, "a" * 500), "Respuesta normal"),
    ]
    
    for response, description in test_cases:
        is_blocked, reason = detect_blocking(response, "test_url")
        status = "🚨 BLOQUEADO" if is_blocked else "✅ OK"
        print(f"   {description}: {status}")
        if is_blocked:
            print(f"      Razón: {reason}")


if __name__ == "__main__":
    print("🤖 SISTEMA DE PRUEBAS PARA CRAWLING MEJORADO")
    print("Este script probará todas las mejoras implementadas\n")
    
    # Ejecutar todas las pruebas
    test_user_agent_rotation()
    test_blocking_detection()
    test_improved_crawling()
    
    print(f"\n🎉 PRUEBAS FINALIZADAS")
    print("El sistema mejorado está listo para manejar dominios problemáticos!")