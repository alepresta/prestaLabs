#!/usr/bin/env python3
"""
Script mejorado para analizar por qué no se pueden crawlear ciertos dominios
"""

import os
import django
import requests
import time
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prestaLabs.settings')
django.setup()


def diagnose_domain(domain):
    """Diagnostica por qué un dominio no se puede crawlear"""
    print(f"\n{'='*60}")
    print(f"🔍 DIAGNÓSTICO COMPLETO DE: {domain}")
    print(f"{'='*60}")
    
    results = {
        'domain': domain,
        'accessible': False,
        'issues': [],
        'recommendations': [],
        'sitemap_found': False,
        'robots_txt': None,
        'response_times': [],
        'status_codes': []
    }
    
    # 1. Probar conectividad básica
    print("\n1️⃣ PRUEBAS DE CONECTIVIDAD")
    protocols = ['https', 'http']
    
    for protocol in protocols:
        url = f"{protocol}://{domain}"
        try:
            start_time = time.time()
            response = requests.get(
                url, 
                timeout=15,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            end_time = time.time()
            response_time = end_time - start_time
            
            results['response_times'].append(response_time)
            results['status_codes'].append(response.status_code)
            
            print(f"   {protocol.upper()}: ✅ {response.status_code} (tiempo: {response_time:.2f}s)")
            
            if response.status_code == 200:
                results['accessible'] = True
                print(f"      Content-Type: {response.headers.get('Content-Type', 'No especificado')}")
                print(f"      Server: {response.headers.get('Server', 'No especificado')}")
                break
            elif response.status_code == 403:
                results['issues'].append('HTTP 403: Acceso denegado - posible protección anti-bot')
            elif response.status_code in [301, 302]:
                redirect_url = response.headers.get('Location', 'No especificado')
                print(f"      Redirección a: {redirect_url}")
            
        except requests.exceptions.Timeout:
            results['issues'].append(f'{protocol.upper()}: Timeout - servidor muy lento o bloqueando conexiones')
            print(f"   {protocol.upper()}: ⏰ TIMEOUT")
        except requests.exceptions.ConnectionError as e:
            results['issues'].append(f'{protocol.upper()}: Error de conexión - {str(e)[:100]}')
            print(f"   {protocol.upper()}: ❌ ERROR CONEXIÓN - {str(e)[:50]}")
        except Exception as e:
            results['issues'].append(f'{protocol.upper()}: Error inesperado - {str(e)[:100]}')
            print(f"   {protocol.upper()}: ❌ ERROR - {str(e)[:50]}")
    
    # 2. Revisar robots.txt
    print("\n2️⃣ ANÁLISIS DE ROBOTS.TXT")
    robots_url = f"https://{domain}/robots.txt"
    try:
        response = requests.get(robots_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; PrestaLab/1.0; +https://example.com/bot)'
        })
        if response.status_code == 200:
            results['robots_txt'] = response.text
            print(f"   ✅ robots.txt encontrado ({len(response.text)} caracteres)")
            
            # Analizar contenido de robots.txt
            lines = response.text.lower().split('\n')
            disallow_all = False
            crawl_delay = None
            sitemap_urls = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('disallow:') and ('/' == line.split(':')[1].strip() or '*' in line):
                    disallow_all = True
                elif line.startswith('crawl-delay:'):
                    try:
                        crawl_delay = int(line.split(':')[1].strip())
                    except:
                        pass
                elif line.startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    sitemap_urls.append(sitemap_url)
            
            if disallow_all:
                results['issues'].append('robots.txt bloquea el crawling con Disallow: /')
                print("   ⚠️  BLOQUEO COMPLETO: Disallow: /")
            
            if crawl_delay:
                results['recommendations'].append(f'Usar delay de {crawl_delay} segundos entre requests')
                print(f"   ⏱️  Crawl-delay recomendado: {crawl_delay}s")
            
            if sitemap_urls:
                print(f"   📋 Sitemaps encontrados: {len(sitemap_urls)}")
                for sitemap_url in sitemap_urls:
                    print(f"      - {sitemap_url}")
                    
        else:
            print(f"   ❌ robots.txt no accesible: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error accediendo robots.txt: {str(e)[:50]}")
    
    # 3. Buscar sitemap
    print("\n3️⃣ BÚSQUEDA DE SITEMAP")
    sitemap_urls = [
        f"https://{domain}/sitemap.xml",
        f"https://www.{domain}/sitemap.xml",
        f"https://{domain}/sitemap_index.xml",
        f"https://{domain}/sitemaps.xml",
        f"https://{domain}/sitemap.php",
        f"https://{domain}/sitemap.txt"
    ]
    
    # Agregar sitemaps de robots.txt si los hay
    if results['robots_txt']:
        lines = results['robots_txt'].split('\n')
        for line in lines:
            if line.lower().strip().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                if sitemap_url not in sitemap_urls:
                    sitemap_urls.insert(0, sitemap_url)  # Priorizar sitemaps de robots.txt
    
    for sitemap_url in sitemap_urls:
        try:
            response = requests.get(sitemap_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; PrestaLab/1.0; +https://example.com/bot)'
            })
            if response.status_code == 200:
                results['sitemap_found'] = True
                print(f"   ✅ SITEMAP ENCONTRADO: {sitemap_url}")
                
                # Intentar parsear el sitemap
                try:
                    if 'xml' in response.headers.get('content-type', '').lower() or sitemap_url.endswith('.xml'):
                        root = ET.fromstring(response.content)
                        
                        # Contar URLs
                        url_count = 0
                        namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                        
                        # Buscar URLs en sitemap normal
                        urls = root.findall('.//sm:url', namespaces)
                        if not urls:
                            # Buscar sin namespace
                            urls = root.findall('.//url')
                        url_count += len(urls)
                        
                        # Buscar sitemaps anidados
                        sitemaps = root.findall('.//sm:sitemap', namespaces)
                        if not sitemaps:
                            sitemaps = root.findall('.//sitemap')
                        
                        print(f"      📊 URLs encontradas: {url_count}")
                        print(f"      📁 Sitemaps anidados: {len(sitemaps)}")
                        
                        if url_count > 0:
                            results['recommendations'].append(f'Usar sitemap: {sitemap_url} ({url_count} URLs)')
                        
                except Exception as e:
                    print(f"      ⚠️ Error parseando XML: {str(e)[:50]}")
                break
                
        except Exception as e:
            continue
    
    if not results['sitemap_found']:
        print("   ❌ No se encontraron sitemaps accesibles")
    
    # 4. Prueba de crawling básico
    print("\n4️⃣ PRUEBA DE CRAWLING")
    if results['accessible']:
        try:
            url = f"https://{domain}"
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                internal_links = 0
                
                for link in links[:20]:  # Solo revisar primeros 20 links
                    href = link['href']
                    if href.startswith('/') or domain in href:
                        internal_links += 1
                
                print(f"   ✅ Página principal accesible")
                print(f"   🔗 Enlaces internos encontrados: {internal_links}")
                
                if internal_links == 0:
                    results['issues'].append('No se encontraron enlaces internos para crawlear')
                else:
                    results['recommendations'].append(f'Crawling posible: {internal_links} enlaces internos detectados')
                    
        except Exception as e:
            results['issues'].append(f'Error en crawling básico: {str(e)[:100]}')
            print(f"   ❌ Error en crawling: {str(e)[:50]}")
    
    # 5. Recomendaciones finales
    print("\n5️⃣ RECOMENDACIONES Y SOLUCIONES")
    
    if not results['accessible']:
        print("   🚨 DOMINIO NO ACCESIBLE")
        print("   💡 Posibles soluciones:")
        print("      - Usar VPN para cambiar ubicación")
        print("      - Probar en diferentes momentos del día") 
        print("      - Verificar que el dominio esté activo")
        results['recommendations'].extend([
            'Dominio inaccesible - verificar conectividad',
            'Considerar usar VPN o proxy',
            'Probar crawling en diferentes horarios'
        ])
    
    elif 403 in results['status_codes']:
        print("   🚨 BLOQUEADO POR PROTECCIÓN ANTI-BOT")
        print("   💡 Posibles soluciones:")
        print("      - Implementar delays más largos entre requests")
        print("      - Rotar User-Agents") 
        print("      - Usar proxies/VPN")
        print("      - Implementar cookies/sesiones")
        print("      - Crawlear con JavaScript (Selenium)")
        results['recommendations'].extend([
            'Implementar delays de 3-5 segundos entre requests',
            'Rotar User-Agents aleatoriamente',
            'Considerar usar Selenium para JavaScript',
            'Implementar manejo de cookies y sesiones'
        ])
    
    elif results['sitemap_found']:
        print("   ✅ USAR SITEMAP PARA OBTENER URLs")
        print("   💡 Estrategia recomendada:")
        print("      - Extraer URLs del sitemap XML")
        print("      - No hacer crawling tradicional")
        print("      - Validar URLs del sitemap individualmente")
    
    else:
        print("   ⚠️ CRAWLING LIMITADO POSIBLE")
        print("   💡 Estrategia recomendada:")
        print("      - Crawling muy lento (5+ segundos entre requests)")
        print("      - Limitar profundidad de crawling")
        print("      - Monitorear respuestas del servidor")
    
    return results


def main():
    """Función principal"""
    dominios_problema = ['jw.org', 'hb.redlink.com.ar', 'udemy.com']
    
    print("🤖 SISTEMA DE DIAGNÓSTICO DE CRAWLING")
    print("Analizando por qué algunos dominios no se pueden crawlear...")
    
    all_results = []
    
    for dominio in dominios_problema:
        result = diagnose_domain(dominio)
        all_results.append(result)
        time.sleep(2)  # Pausa entre análisis
    
    # Resumen final
    print(f"\n{'='*60}")
    print("📋 RESUMEN FINAL")
    print(f"{'='*60}")
    
    for result in all_results:
        print(f"\n🌐 {result['domain']}:")
        print(f"   Accesible: {'✅' if result['accessible'] else '❌'}")
        print(f"   Sitemap: {'✅' if result['sitemap_found'] else '❌'}")
        print(f"   Problemas: {len(result['issues'])}")
        print(f"   Soluciones: {len(result['recommendations'])}")
        
        if result['issues']:
            print("   🚨 Principales problemas:")
            for issue in result['issues'][:3]:
                print(f"      • {issue}")
        
        if result['recommendations']:
            print("   💡 Mejores soluciones:")
            for rec in result['recommendations'][:3]:
                print(f"      • {rec}")


if __name__ == "__main__":
    main()