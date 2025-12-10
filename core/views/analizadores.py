import requests
from bs4 import BeautifulSoup
import re


def analizar_formularios(url):
    """Analiza formularios en una URL"""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "PrestaLab"})
        soup = BeautifulSoup(resp.content, "html.parser")
        forms = soup.find_all("form")
        resultados = {
            "tiene_formularios": len(forms) > 0,
            "total_formularios": len(forms),
            "formularios": [],
        }
        for form in forms:
            form_info = {
                "action": form.get("action", ""),
                "method": form.get("method", "GET").upper(),
                "inputs": len(form.find_all("input")),
                "has_password": bool(form.find("input", {"type": "password"})),
            }
            resultados["formularios"].append(form_info)
        return resultados
    except Exception as e:
        return {"error": str(e), "tiene_formularios": False}


def analizar_analytics(url):
    """Busca Google Analytics, GTM, etc."""
    try:
        resp = requests.get(url, timeout=10)
        content = resp.text
        analytics_data = {
            "google_analytics": False,
            "google_tag_manager": False,
            "facebook_pixel": False,
            "detalles": [],
        }
        # Google Analytics (UA- o G-)
        if re.search(r"UA-\d+-\d+", content) or re.search(r"G-[A-Z0-9]+", content):
            analytics_data["google_analytics"] = True
            analytics_data["detalles"].append("Google Analytics encontrado")
        # Google Tag Manager
        if "googletagmanager.com/gtm.js" in content or "GTM-" in content:
            analytics_data["google_tag_manager"] = True
            analytics_data["detalles"].append("Google Tag Manager encontrado")
        # Facebook Pixel
        if "facebook.com/tr" in content or "fbq(" in content:
            analytics_data["facebook_pixel"] = True
            analytics_data["detalles"].append("Facebook Pixel encontrado")
        return analytics_data
    except Exception as e:
        return {"error": str(e)}
