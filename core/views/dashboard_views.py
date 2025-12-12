"""
Vistas para el dashboard y análisis de resultados.

Contiene todas las vistas relacionadas con:
- Dashboard principal
- Análisis detallado
- URLs guardadas
- Análisis de URLs individuales
"""

import json
import csv
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from ..models import BusquedaDominio, UrlGuardada, AnalisisUrlIndividual
from ..utils.web_utils import normalizar_url_individual
from ..forms import DominioForm


@login_required
def index(request):
    """Vista principal del dashboard"""

    # Estadísticas generales del usuario
    total_dominios = BusquedaDominio.objects.filter(usuario=request.user).count()
    dominios_guardados = BusquedaDominio.objects.filter(
        usuario=request.user, guardado=True
    ).count()
    urls_guardadas = UrlGuardada.objects.filter(usuario=request.user).count()
    analisis_urls = AnalisisUrlIndividual.objects.filter(usuario=request.user).count()

    # Análisis recientes
    analisis_recientes = BusquedaDominio.objects.filter(usuario=request.user).order_by(
        "-fecha"
    )[:5]

    # URLs guardadas recientes
    urls_recientes = UrlGuardada.objects.filter(usuario=request.user).order_by(
        "-fecha_guardado"
    )[:5]

    context = {
        "total_dominios": total_dominios,
        "dominios_guardados": dominios_guardados,
        "urls_guardadas": urls_guardadas,
        "analisis_urls": analisis_urls,
        "analisis_recientes": analisis_recientes,
        "urls_recientes": urls_recientes,
    }

    return render(request, "dashboard/index.html", context)


@login_required
def analisis_detalle(request):
    """Vista para ver análisis detallados de dominios guardados"""

    # Obtener query de búsqueda
    query = request.GET.get("q", "").strip()

    # Filtrar dominios guardados
    dominios_guardados = BusquedaDominio.objects.filter(
        usuario=request.user, guardado=True
    ).order_by("-fecha")

    if query:
        dominios_guardados = dominios_guardados.filter(Q(dominio__icontains=query))

    # Paginación
    paginator = Paginator(dominios_guardados, 10)
    page = request.GET.get("page", 1)
    dominios = paginator.get_page(page)

    # Procesamiento POST para eliminar dominios
    mensaje = None
    if request.method == "POST" and "eliminar_dominio" in request.POST:
        dominio_id = request.POST.get("eliminar_dominio")
        try:
            dominio_obj = BusquedaDominio.objects.get(
                id=dominio_id, usuario=request.user
            )
            dominio_nombre = dominio_obj.dominio
            dominio_obj.delete()
            mensaje = f"Dominio '{dominio_nombre}' eliminado correctamente."
        except BusquedaDominio.DoesNotExist:
            mensaje = "No se encontró el dominio seleccionado."

    context = {
        "dominios": dominios,
        "query": query,
        "mensaje": mensaje,
    }

    return render(request, "analisis/detalle.html", context)


@login_required
def urls_guardadas_view(request):
    """Vista para gestionar URLs guardadas individualmente"""

    mensaje = None

    # Procesar formulario POST
    if request.method == "POST":
        mensaje = _procesar_formulario_urls(request)

    # Obtener URLs con filtro
    query = request.GET.get("q", "").strip()
    urls_list = UrlGuardada.objects.filter(usuario=request.user).order_by(
        "-fecha_guardado"
    )

    if query:
        urls_list = urls_list.filter(
            Q(url__icontains=query)
            | Q(titulo__icontains=query)
            | Q(descripcion__icontains=query)
        )

    # Paginación
    paginator = Paginator(urls_list, 15)
    page = request.GET.get("page", 1)
    urls = paginator.get_page(page)

    context = {
        "urls": urls,
        "query": query,
        "mensaje": mensaje,
    }

    return render(request, "urls_guardadas.html", context)


def _procesar_formulario_urls(request):
    """Procesa los formularios de URLs guardadas"""

    if "agregar_url" in request.POST:
        return _agregar_url_guardada(request)
    elif "eliminar_url" in request.POST:
        return _eliminar_url_guardada(request)
    elif "eliminar_seleccionadas" in request.POST:
        return _eliminar_urls_seleccionadas(request)

    return None


def _agregar_url_guardada(request):
    """Agrega una nueva URL guardada"""

    url_raw = request.POST.get("url", "").strip()

    if not url_raw:
        return "Por favor ingresa una URL."

    # Normalizar URL
    url_normalizada = normalizar_url_individual(url_raw)

    if not url_normalizada:
        return "La URL ingresada no es válida."

    # Verificar duplicados
    if UrlGuardada.objects.filter(usuario=request.user, url=url_normalizada).exists():
        return "Esta URL ya está guardada."

    # Crear URL guardada
    url_guardada = UrlGuardada.objects.create(
        usuario=request.user,
        url=url_normalizada,
        titulo=f"URL guardada - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
        descripcion="URL agregada manualmente",
    )

    return f"URL guardada correctamente: {url_normalizada}"


def _eliminar_url_guardada(request):
    """Elimina una URL guardada individual"""

    url_id = request.POST.get("eliminar_url")

    try:
        url_obj = UrlGuardada.objects.get(id=url_id, usuario=request.user)
        url_eliminada = url_obj.url
        url_obj.delete()
        return f"URL eliminada correctamente: {url_eliminada}"
    except UrlGuardada.DoesNotExist:
        return "No se encontró la URL seleccionada."


def _eliminar_urls_seleccionadas(request):
    """Elimina múltiples URLs seleccionadas"""

    url_ids = request.POST.getlist("url_ids")

    if not url_ids:
        return "No se seleccionaron URLs para eliminar."

    eliminadas = UrlGuardada.objects.filter(
        id__in=url_ids, usuario=request.user
    ).delete()

    return f"{eliminadas[0]} URLs eliminadas correctamente."


@login_required
def analisis_url_view(request):
    """Vista para análisis de URLs individuales"""

    mensaje = None

    if request.method == "POST":
        mensaje = _procesar_analisis_url(request)

    # Obtener análisis con filtro
    query = request.GET.get("q", "").strip()
    analisis_list = AnalisisUrlIndividual.objects.filter(usuario=request.user).order_by(
        "-created_at"
    )

    if query:
        analisis_list = analisis_list.filter(Q(url__icontains=query))

    # Paginación
    paginator = Paginator(analisis_list, 10)
    page = request.GET.get("page", 1)
    analisis = paginator.get_page(page)

    context = {
        "analisis": analisis,
        "query": query,
        "mensaje": mensaje,
    }

    return render(request, "analisis/url_especifica.html", context)


def _procesar_analisis_url(request):
    """Procesa el formulario de análisis de URL"""

    if "analizar_url" in request.POST:
        return _crear_analisis_url(request)
    elif "eliminar_analisis" in request.POST:
        return _eliminar_analisis_url(request)
    elif "eliminar_seleccionados" in request.POST:
        return _eliminar_analisis_seleccionados(request)

    return None


def _crear_analisis_url(request):
    """Crea un nuevo análisis de URL"""

    url_raw = request.POST.get("url", "").strip()
    alcance = request.POST.get("alcance_analisis", "1")

    if not url_raw:
        return "Por favor ingresa una URL para analizar."

    # Normalizar URL
    url_normalizada = normalizar_url_individual(url_raw)

    if not url_normalizada:
        return "La URL ingresada no es válida."

    # Crear análisis
    analisis = AnalisisUrlIndividual.objects.create(
        usuario=request.user,
        url=url_normalizada,
        alcance_analisis=alcance,
        tipo_analisis="todas",
        estado="en_progreso",
    )

    return f"Análisis iniciado para: {url_normalizada} (ID: {analisis.id})"


def _eliminar_analisis_url(request):
    """Elimina un análisis de URL individual"""

    analisis_id = request.POST.get("eliminar_analisis")

    try:
        analisis_obj = AnalisisUrlIndividual.objects.get(
            id=analisis_id, usuario=request.user
        )
        url_eliminada = analisis_obj.url
        analisis_obj.delete()
        return f"Análisis eliminado correctamente: {url_eliminada}"
    except AnalisisUrlIndividual.DoesNotExist:
        return "No se encontró el análisis seleccionado."


def _eliminar_analisis_seleccionados(request):
    """Elimina múltiples análisis seleccionados"""

    analisis_ids = request.POST.getlist("analisis_ids")

    if not analisis_ids:
        return "No se seleccionaron análisis para eliminar."

    eliminados = AnalisisUrlIndividual.objects.filter(
        id__in=analisis_ids, usuario=request.user
    ).delete()

    return f"{eliminados[0]} análisis eliminados correctamente."


@login_required
def exportar_urls_csv(request):
    """Exporta URLs guardadas a CSV"""

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="urls_guardadas.csv"'

    writer = csv.writer(response)
    writer.writerow(["URL", "Título", "Descripción", "Fecha"])

    urls = UrlGuardada.objects.filter(usuario=request.user).order_by("-fecha_guardado")

    for url in urls:
        writer.writerow(
            [
                url.url,
                url.titulo,
                url.descripcion,
                url.fecha_guardado.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )

    return response
