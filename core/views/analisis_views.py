from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
import requests
from defusedxml.ElementTree import fromstring
import re
import validators
from .analizadores import analizar_formularios, analizar_analytics
from urllib.parse import urljoin


# --- Mejoras ---
def buscar_sitemap(dominio):
    posibles_rutas = [
        f"https://{dominio}/sitemap.xml",
        f"https://{dominio}/sitemap_index.xml",
        f"https://{dominio}/sitemap.php",
        f"https://{dominio}/sitemap.txt",
        f"https://{dominio}/sitemap/",
    ]
    robots_url = f"https://{dominio}/robots.txt"
    try:
        resp = requests.get(robots_url, timeout=5, headers={"User-Agent": "PrestaLab"})
        if resp.status_code == 200:
            lines = resp.text.split("\n")
            for line in lines:
                if line.strip().lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    if sitemap_url:
                        posibles_rutas.insert(0, sitemap_url)
    except Exception as e:
        print(f"⚠️ Error robots.txt {dominio}: {e}")
    for url in posibles_rutas:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "PrestaLab"})
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "").lower()
                content = resp.content.decode("utf-8", errors="ignore")
                is_xml = "xml" in content_type or url.endswith(".xml")
                has_sitemap_tags = (
                    "<urlset" in content
                    or "<sitemapindex" in content
                    or 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in content
                )
                if is_xml and has_sitemap_tags:
                    return url, resp.content
                elif "<html" not in content[:500].lower() and (
                    "http://" in content or "https://" in content
                ):
                    return url, resp.content
        except (requests.RequestException, ValueError, TypeError) as e:
            print(f"Error procesando URL: {e}")
            continue
    return None, None


def procesar_sitemap(content, url_base, max_urls=100, profundidad=0, max_profundidad=3):
    if profundidad > max_profundidad:
        return []
    urls = []
    try:
        tree = fromstring(content)
        namespaces = {
            "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "ns0": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "default": "http://www.sitemaps.org/schemas/sitemap/0.9",
        }
        sitemap_locs = []
        for ns_prefix, ns_url in namespaces.items():
            sitemap_elements = tree.findall(f".//{{{ns_url}}}sitemap")
            if sitemap_elements:
                for sitemap in sitemap_elements:
                    loc = sitemap.find(f"{{{ns_url}}}loc")
                    if loc is not None and loc.text:
                        sitemap_locs.append(loc.text)
        if sitemap_locs:
            for sitemap_url in sitemap_locs[:5]:
                try:
                    print(f"URL: {sitemap_url}")
                    resp = requests.get(
                        sitemap_url, timeout=15, headers={"User-Agent": "PrestaLab"}
                    )
                    if resp.status_code == 200:
                        urls_hijo = procesar_sitemap(
                            resp.content,
                            url_base,
                            max_urls - len(urls),
                            profundidad + 1,
                            max_profundidad,
                        )
                        urls.extend(urls_hijo)
                except Exception as e:
                    print(f"Error procesando sitemap hijo: {e}")
                if len(urls) >= max_urls:
                    return urls[:max_urls]
            return urls[:max_urls]
        url_candidates = []
        for ns_prefix, ns_url in namespaces.items():
            url_elements = tree.findall(f".//{{{ns_url}}}url")
            for url_elem in url_elements:
                loc = url_elem.find(f"{{{ns_url}}}loc")
                if loc is not None and loc.text:
                    url_candidates.append(loc.text)
        if not url_candidates:
            url_elements = tree.findall(".//url")
            for url_elem in url_elements:
                loc = url_elem.find("loc")
                if loc is not None and loc.text:
                    url_candidates.append(loc.text)
        if not url_candidates:
            for loc in tree.findall(".//loc"):
                if loc.text:
                    url_candidates.append(loc.text)
        if not url_candidates:
            content_str = content.decode("utf-8", errors="ignore")
            url_pattern = r'https?://[^\s<>"]+'
            found_urls = re.findall(url_pattern, content_str)
            url_candidates.extend(found_urls[:50])
        for url in url_candidates:
            if len(urls) >= max_urls:
                break
            if url.startswith("http"):
                urls.append(url)
            elif url.startswith("/"):
                absolute_url = urljoin(url_base, url)
                urls.append(absolute_url)
    except Exception as e:
        print(f"⚠️ Error procesando sitemap: {e}")
        try:
            content_str = content.decode("utf-8", errors="ignore")
            lines = content_str.split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and len(urls) < max_urls:
                    if line.startswith("http"):
                        urls.append(line)
                    elif "://" in line:
                        urls.append(line)
        except Exception as e:
            print(f"Error al procesar línea: {e}")
            pass
    return urls[:max_urls]


@login_required
def analisis_dominio(request):
    error = None
    resultados = []
    if request.method == "POST":
        dominio = request.POST.get("dominio", "").strip().lower()
        if not dominio:
            messages.error(request, "Por favor, ingresa un dominio válido")
            return redirect("analisis_dominio")
        if dominio.startswith("http://"):
            dominio = dominio[7:]
        elif dominio.startswith("https://"):
            dominio = dominio[8:]
        if dominio.startswith("www."):
            dominio = dominio[4:]
        if "/" in dominio:
            dominio = dominio.split("/")[0]
        sitemap_url, sitemap_content = buscar_sitemap(dominio)
        if sitemap_url and sitemap_content:
            try:
                urls = procesar_sitemap(
                    sitemap_content, f"https://{dominio}", max_urls=100
                )
                if urls:
                    for url in urls:
                        resultados.append(
                            {
                                "url": url,
                                "estado": "OK",
                                "detalles": f"Encontrado en sitemap: {url}",
                            }
                        )
                    total_encontradas = len(urls)
                    request.session["ultimo_analisis"] = {
                        "tipo": "dominio",
                        "dominio": dominio,
                        "sitemap_url": sitemap_url,
                        "resultados": resultados,
                        "total_urls": total_encontradas,
                        "timestamp": str(timezone.now()),
                    }
                    messages.success(
                        request,
                        f"✅ Encontradas {total_encontradas} URLs en el sitemap",
                    )
                    return redirect("analisis_resultados")
                else:
                    error = "Sitemap encontrado pero no contiene URLs válidas"
            except Exception as e:
                error = f"Error procesando sitemap: {str(e)}"
        else:
            error = "No se encontró sitemap para el dominio."
            resultados.append(
                {
                    "url": f"https://{dominio}",
                    "estado": "SIN SITEMAP",
                    "detalles": "Analizando solo página principal (no se encontró sitemap)",
                }
            )
            request.session["ultimo_analisis"] = {
                "tipo": "dominio",
                "dominio": dominio,
                "sitemap_url": None,
                "resultados": resultados,
                "total_urls": 1,
                "timestamp": str(timezone.now()),
            }
            return redirect("analisis_resultados")
    return render(request, "analisis/dominio.html", {"error": error})


@login_required
def analisis_url_especifica(request):
    error = None
    resultados = []
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        tipo_analisis = request.POST.get("tipo_analisis", "todas")
        if validators.url(url):
            detalles = {}
            analizadores = {
                "formulario": analizar_formularios,
                "analytics": analizar_analytics,
                # ...agregar más analizadores aquí...
            }
            if tipo_analisis == "todas":
                for nombre, func in analizadores.items():
                    detalles[nombre] = func(url)
            elif tipo_analisis in analizadores:
                detalles[tipo_analisis] = analizadores[tipo_analisis](url)
            resultados.append({"url": url, "estado": "Analizado", "detalles": detalles})
            request.session["ultimo_analisis"] = {
                "tipo": "url",
                "url": url,
                "tipo_analisis": tipo_analisis,
                "resultados": resultados,
                "timestamp": str(timezone.now()),
            }
            return redirect("analisis_resultados")
        else:
            error = "URL no válida."
    return render(request, "analisis/url_especifica.html", {"error": error})


@login_required
def analisis_resultados(request):
    datos = request.session.get("ultimo_analisis", {})
    resultados = datos.get("resultados", [])
    error = None
    return render(
        request, "analisis/resultados.html", {"resultados": resultados, "error": error}
    )
