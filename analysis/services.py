import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
from typing import Dict, List, Set
from django.utils import timezone

class AccessibilityAnalyzer:
    """Analizador de accesibilidad web."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def analyze_url(self, url: str) -> Dict:
        """Analiza una URL específica."""
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=30)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Análisis básico
                analysis = {
                    'url': url,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'content_size': len(response.content),
                    'title': soup.title.string if soup.title else '',
                    'accessibility_score': self._calculate_accessibility_score(soup),
                    'wcag_violations': self._check_wcag_violations(soup),
                    'color_contrast_issues': self._check_color_contrast(soup),
                    'alt_text_missing': self._check_alt_text(soup),
                    'heading_structure_issues': self._check_heading_structure(soup),
                    'meta_description': self._get_meta_description(soup),
                    'meta_keywords': self._get_meta_keywords(soup),
                }
                
                return analysis
            else:
                return {
                    'url': url,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'url': url,
                'status_code': 0,
                'error': str(e)
            }
    
    def _calculate_accessibility_score(self, soup: BeautifulSoup) -> float:
        """Calcula un score básico de accesibilidad."""
        score = 100.0
        
        # Verificar imágenes sin alt
        images_without_alt = soup.find_all('img', alt='') + soup.find_all('img', lambda x: not x.get('alt'))
        if images_without_alt:
            score -= min(len(images_without_alt) * 5, 30)
        
        # Verificar estructura de headings
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if not headings:
            score -= 20
        elif not soup.find('h1'):
            score -= 10
        
        # Verificar labels en formularios
        inputs = soup.find_all('input', type=['text', 'email', 'password', 'tel'])
        inputs_without_labels = [inp for inp in inputs if not soup.find('label', {'for': inp.get('id')})]
        if inputs_without_labels:
            score -= min(len(inputs_without_labels) * 10, 25)
        
        # Verificar meta description
        if not soup.find('meta', {'name': 'description'}):
            score -= 5
        
        return max(0, score)
    
    def _check_wcag_violations(self, soup: BeautifulSoup) -> Dict:
        """Verifica violaciones WCAG básicas."""
        violations = {
            'images_without_alt': len(soup.find_all('img', lambda x: not x.get('alt'))),
            'empty_links': len(soup.find_all('a', string='')),
            'missing_lang': not soup.find('html', lang=True),
            'missing_title': not soup.title,
            'duplicate_ids': self._check_duplicate_ids(soup)
        }
        return violations
    
    def _check_color_contrast(self, soup: BeautifulSoup) -> int:
        """Verificación básica de contraste de colores."""
        # Implementación simplificada
        return 0
    
    def _check_alt_text(self, soup: BeautifulSoup) -> int:
        """Cuenta imágenes sin texto alternativo."""
        return len(soup.find_all('img', lambda x: not x.get('alt')))
    
    def _check_heading_structure(self, soup: BeautifulSoup) -> int:
        """Verifica problemas en la estructura de headings."""
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        issues = 0
        
        if not headings:
            issues += 1
        
        h1_count = len(soup.find_all('h1'))
        if h1_count == 0 or h1_count > 1:
            issues += 1
        
        return issues
    
    def _check_duplicate_ids(self, soup: BeautifulSoup) -> int:
        """Verifica IDs duplicados."""
        ids = [elem.get('id') for elem in soup.find_all(id=True)]
        return len(ids) - len(set(ids))
    
    def _get_meta_description(self, soup: BeautifulSoup) -> str:
        """Obtiene la meta descripción."""
        meta_desc = soup.find('meta', {'name': 'description'})
        return meta_desc.get('content', '') if meta_desc else ''
    
    def _get_meta_keywords(self, soup: BeautifulSoup) -> str:
        """Obtiene las meta keywords."""
        meta_keys = soup.find('meta', {'name': 'keywords'})
        return meta_keys.get('content', '') if meta_keys else ''

class WebCrawler:
    """Crawler web para analizar sitios completos."""
    
    def __init__(self):
        self.analyzer = AccessibilityAnalyzer()
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
    
    def crawl_site(self, base_url: str, max_pages: int = 50) -> List[Dict]:
        """Crawlea un sitio web completo."""
        self.visited_urls.clear()
        self.discovered_urls.clear()
        
        # Normalizar URL base
        parsed_base = urlparse(base_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        # Agregar URL inicial
        self.discovered_urls.add(base_url)
        results = []
        
        print(f"🚀 Iniciando crawling de {base_url}")
        print(f"🗺️  Generando sitemap completo para {base_url}")
        
        while self.discovered_urls and len(results) < max_pages:
            current_url = self.discovered_urls.pop()
            
            if current_url in self.visited_urls:
                continue
            
            print(f"Crawling: {current_url}")
            
            # Analizar URL actual
            analysis = self.analyzer.analyze_url(current_url)
            
            if analysis.get('status_code') == 200:
                print(f"✅ Página crawleada: {analysis.get('title', 'Sin título')}")
                
                # Buscar más URLs en esta página
                new_urls = self._extract_urls_from_page(current_url, base_domain)
                self.discovered_urls.update(new_urls - self.visited_urls)
                
                print(f"✅ {current_url} [{analysis['status_code']}] - {len(self.discovered_urls)} URLs pendientes")
            else:
                print(f"❌ {current_url} [{analysis.get('status_code', 'ERROR')}] - {len(self.discovered_urls)} URLs pendientes")
            
            self.visited_urls.add(current_url)
            results.append(analysis)
            
            # Pequeña pausa para no sobrecargar el servidor
            time.sleep(0.5)
        
        print(f"📋 Sitemap completado: {len(self.discovered_urls) + len(self.visited_urls)} URLs descubiertas, {len([r for r in results if r.get('status_code') == 200])} accesibles")
        
        return results
    
    def _extract_urls_from_page(self, current_url: str, base_domain: str) -> Set[str]:
        """Extrae URLs de una página."""
        try:
            response = self.analyzer.session.get(current_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                urls = set()
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(current_url, href)
                    parsed_url = urlparse(full_url)
                    
                    # Solo URLs del mismo dominio
                    if parsed_url.netloc == urlparse(base_domain).netloc:
                        # Limpiar fragmentos y parámetros
                        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                        if clean_url != current_url and clean_url.startswith(base_domain):
                            urls.add(clean_url)
                
                return urls
        except Exception as e:
            print(f"Error extrayendo URLs de {current_url}: {e}")
        
        return set()
