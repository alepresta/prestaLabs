import re
from django.urls import reverse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import DominioForm
from django.core.paginator import Paginator


def api_status(request):
    return JsonResponse({"status": "ok"})


def index(request):
    return render(request, "dashboard/index.html")


def normalizar_dominio(dominio_raw):
    dominio_raw = dominio_raw.strip().lower()
    # Quitar protocolo
    dominio = re.sub(r"^https?://", "", dominio_raw)
    # Quitar path y query
    dominio = dominio.split("/")[0].split("?")[0]
    # Quitar puerto
    dominio = dominio.split(":")[0]
    # Quitar www. solo si es el único subdominio (no www1, www2, etc)
    partes = dominio.split(".")
    if len(partes) >= 3 and partes[0] == "www":
        dominio = ".".join(partes[1:])
    # Quitar punto final y puntos dobles
    dominio = dominio.rstrip(".")
    dominio = re.sub(r"\.{2,}", ".", dominio)
    return dominio


def analisis_dominio(request):
    """
    Vista para ingresar dominio y mostrar historial de dominios buscados
    """
    from .models import BusquedaDominio

    form = DominioForm()
    mensaje = ""

    mensaje = ""
    # Validación estricta: solo letras, números, guiones, puntos, mínimo 3, no termina en punto, no puntos dobles
    regex_part1 = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?"
    regex_part2 = r"(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*"
    regex_part3 = r"$"
    regex = regex_part1 + regex_part2 + regex_part3
    if request.method == "POST":
        form = DominioForm(request.POST)
        if form.is_valid():
            dominio_raw = form.cleaned_data["dominio"]
            dominio = normalizar_dominio(dominio_raw)
            if not re.match(regex, dominio):
                mensaje = "Dominio inválido."
                return render(
                    request,
                    "analisis_dominio.html",
                    {
                        "form": form,
                        "dominios_tabla": [],
                        "mensaje": mensaje,
                        "error": None,
                        "page_obj": None,
                    },
                )
            elif not dominio:
                mensaje = "Dominio vacío."
                return render(
                    request,
                    "analisis_dominio.html",
                    {
                        "form": form,
                        "dominios_tabla": [],
                        "mensaje": mensaje,
                        "error": None,
                        "page_obj": None,
                    },
                )
            else:
                # Guardar en sesión para historial rápido
                if "dominios_buscados" not in request.session:
                    request.session["dominios_buscados"] = []
                if dominio not in request.session["dominios_buscados"]:
                    request.session["dominios_buscados"].append(dominio)
                    request.session.modified = True
                    mensaje = f"Dominio '{dominio}' agregado al historial."
                else:
                    mensaje = "El dominio ya fue ingresado."
                url = reverse("analisis_detalle") + f"?dominio={dominio}"
                return redirect(url)
    # Solución temporal: traer últimos 1000 registros, agrupar por dominio normalizado en Python, paginar
    busquedas_qs = BusquedaDominio.objects.order_by("-fecha")[:1000]
    dominios_vistos = set()
    dominios_tabla = []
    for b in busquedas_qs:
        dom_norm = normalizar_dominio(b.dominio)
        if dom_norm not in dominios_vistos:
            dominios_vistos.add(dom_norm)
            dominios_tabla.append(
                {
                    "dominio": dom_norm,
                    "id": b.id,
                    "fecha": b.fecha,
                    "usuario": b.usuario.username if b.usuario else "-",
                    "urls": b.urls,
                }
            )
    # Ordenar por fecha descendente (ya lo están, pero por si acaso)
    dominios_tabla.sort(key=lambda x: x["fecha"], reverse=True)
    paginator = Paginator(dominios_tabla, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    total_registros = BusquedaDominio.objects.count()
    print(f"Total registros en BD: {total_registros}")
    print(f"Registros únicos mostrados (página): {len(page_obj)}")
    for b in page_obj:
        urls_count = len(b["urls"].splitlines()) if b["urls"] else 0
        print(f"  - {b['dominio']} | {b['fecha']} | URLs: {urls_count}")
    return render(
        request,
        "analisis_dominio.html",
        {
            "form": form,
            "dominios_tabla": list(page_obj),
            "mensaje": mensaje,
            "error": None,
            "page_obj": page_obj,
        },
    )


def analisis_detalle(request):
    """
    Vista para mostrar las URLs del sitemap de un dominio
    """
    form = DominioForm()
    mensaje = ""
    page_obj = []
    return render(
        request,
        "analisis_dominio.html",
        {
            "form": form,
            "dominios_tabla": page_obj,
            "mensaje": mensaje,
            "error": None,
            "page_obj": page_obj,
        },
    )
