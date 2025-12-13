"""
Utilidades para manejo de dominios.

Contiene funciones puras para normalización y validación de dominios.
"""

import re


def normalizar_dominio(dominio_raw):
    """
    Normaliza un dominio: quita protocolo, path, puerto, www, etc.
    
    Args:
        dominio_raw (str): Dominio sin procesar
        
    Returns:
        str: Dominio normalizado
        
    Examples:
        >>> normalizar_dominio("https://www.example.com/path")
        "example.com"
        >>> normalizar_dominio("http://subdomain.example.com:8080")
        "subdomain.example.com"
    """
    dominio_raw = dominio_raw.strip().lower()
    dominio = re.sub(r"^https?://", "", dominio_raw)
    dominio = dominio.split("/")[0].split("?")[0]
    dominio = dominio.split(":")[0]
    partes = dominio.split(".")
    if len(partes) >= 3 and partes[0] == "www":
        dominio = ".".join(partes[1:])
    dominio = dominio.rstrip(".")
    dominio = re.sub(r"\.{2,}", ".", dominio)
    return dominio


def limpiar_dominio_para_url(dominio):
    """
    Limpia un dominio para construir una URL válida.
    
    Args:
        dominio (str): Dominio a limpiar
        
    Returns:
        str: Dominio limpio para URL
    """
    d = dominio.strip()
    if d.startswith("http://"):
        d = d[7:]
    elif d.startswith("https://"):
        d = d[8:]
    return d.rstrip("/")


def validar_dominio(dominio):
    """
    Valida si un dominio tiene formato válido.
    
    Args:
        dominio (str): Dominio a validar
        
    Returns:
        bool: True si es válido, False en caso contrario
    """
    regex = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$"
    dominio_normalizado = normalizar_dominio(dominio)
    return bool(re.match(regex, dominio_normalizado))


def get_working_base_url(dominio):
    """
    Obtiene una URL base funcional probando https y http.
    
    Args:
        dominio (str): Dominio a probar
        
    Returns:
        str: URL base que funciona o fallback a https
    """
    import requests
    
    for proto in ["https", "http"]:
        url = f"{proto}://{dominio}"
        try:
            resp = requests.get(url, timeout=6, headers={"User-Agent": "PrestaLab"})
            if resp.status_code == 200:
                return url
        except Exception:
            continue
    return f"https://{dominio}"  # fallback


def normalize_domain_for_comparison(domain):
    """
    Normaliza un dominio para comparaciones (elimina www, convierte a minúsculas).
    
    Args:
        domain (str): Dominio a normalizar
        
    Returns:
        str: Dominio normalizado para comparación
    """
    return domain.lower().replace("www.", "")