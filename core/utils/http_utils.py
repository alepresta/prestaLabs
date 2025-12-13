"""
Utilidades para manejo de HTTP y requests.

Contiene funciones para generar headers, manejar requests y utilidades HTTP.
"""

import random


# User-Agents rotativos para evitar detección
USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Edge/119.0.0.0"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
]


def get_random_headers():
    """
    Genera headers aleatorios para simular navegador real.
    
    Returns:
        dict: Headers HTTP aleatorios
    """
    return {
        "User-Agent": random.choice(USER_AGENTS),  # nosec B311 - Not cryptographic use
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }


def get_specialized_headers(domain):
    """
    Genera headers especializados para dominios específicos.
    
    Args:
        domain (str): Dominio para el cual generar headers
        
    Returns:
        dict: Headers especializados para el dominio
    """
    headers = get_random_headers()
    
    # Headers específicos para ciertos sitios
    if "udemy" in domain.lower():
        headers.update({
            "Accept": "application/xml,text/xml,*/*;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
        })
    
    return headers


def is_valid_http_status(status_code):
    """
    Verifica si un código de estado HTTP indica éxito.
    
    Args:
        status_code (int): Código de estado HTTP
        
    Returns:
        bool: True si es exitoso, False en caso contrario
    """
    return 200 <= status_code < 300


def is_blocking_status(status_code):
    """
    Verifica si un código de estado indica bloqueo.
    
    Args:
        status_code (int): Código de estado HTTP
        
    Returns:
        bool: True si indica bloqueo, False en caso contrario
    """
    return status_code in [403, 429, 503]


def get_content_safely(response, max_length=None):
    """
    Obtiene el contenido de una respuesta HTTP de forma segura.
    
    Args:
        response: Objeto response de requests
        max_length (int, optional): Longitud máxima del contenido
        
    Returns:
        str: Contenido de la respuesta o cadena vacía
    """
    try:
        content = response.text if hasattr(response, "text") else ""
        if max_length and len(content) > max_length:
            content = content[:max_length]
        return content
    except Exception:
        return ""