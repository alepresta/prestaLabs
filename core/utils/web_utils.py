"""
Utilidades para manejo de requests web y detección de bloqueos.

Funciones utilitarias para:
- Headers aleatorios
- Detección de bloqueos
- Normalización de URLs
"""

import random
import re
from urllib.parse import urlparse


# Lista de User-Agents para rotar y parecer más humano
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
]


def get_random_headers():
    """Genera headers aleatorios para parecer más humano"""

    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def detect_blocking(response, url):
    """Detecta si estamos siendo bloqueados por el sitio"""

    # Códigos de estado que indican bloqueo
    if response.status_code in [403, 429, 503]:
        return True

    # Contenido que indica bloqueo/captcha
    content_lower = response.text.lower()
    blocking_indicators = [
        "captcha",
        "blocked",
        "access denied",
        "rate limit",
        "too many requests",
        "cloudflare",
        "security check",
    ]

    return any(indicator in content_lower for indicator in blocking_indicators)


def normalizar_dominio(dominio_raw):
    """Normaliza un dominio eliminando protocolo y paths"""

    if not dominio_raw:
        return ""

    dominio = dominio_raw.strip().lower()

    # Quitar protocolo si existe
    if dominio.startswith(("http://", "https://")):
        parsed = urlparse(dominio)
        dominio = parsed.netloc

    # Quitar www. si existe
    if dominio.startswith("www."):
        dominio = dominio[4:]

    # Quitar path, query params, etc
    if "/" in dominio:
        dominio = dominio.split("/")[0]

    # Validación básica
    if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", dominio):
        return ""

    return dominio


def normalizar_url_individual(url):
    """Normaliza una URL individual para evitar duplicados"""

    if not url:
        return ""

    url = url.strip()

    # Agregar protocolo si no lo tiene
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Parsear URL
    try:
        parsed = urlparse(url)

        # Reconstruir URL normalizada
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")  # Quitar slash final

        # Normalizar netloc (quitar www si es redundante)
        if netloc.startswith("www.") and len(netloc.split(".")) > 2:
            netloc_sin_www = netloc[4:]
            # Solo quitar www si el dominio funciona sin él
            netloc = netloc_sin_www

        normalized_url = f"{scheme}://{netloc}{path}"

        # Agregar query params si existen (manteniendo orden)
        if parsed.query:
            normalized_url += f"?{parsed.query}"

        return normalized_url

    except Exception:
        return url  # Retornar original si hay error
