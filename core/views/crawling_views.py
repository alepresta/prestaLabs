"""
Vistas para funcionalidades de crawling.

Contiene todas las vistas relacionadas con:
- Análisis de dominios
- Crawling de sitios
- Progreso de crawling
- APIs de estado
"""

import json
import threading
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q

from ..models import BusquedaDominio, CrawlingProgress
from ..services.crawling_service import CrawlingService, AnalysisService
from ..utils.web_utils import normalizar_dominio
from ..forms import DominioForm


@login_required
def analisis_dominio_view(request):
    """Vista principal para análisis de dominios"""

    # Limpiar procesos colgados al cargar la página
    CrawlingService.limpiar_procesos_colgados()
    CrawlingService.sincronizar_estados_crawling()

    form = DominioForm()
    mensaje = None

    # Procesar formularios POST
    if request.method == "POST":
        mensaje = _procesar_formulario_dominio(request)

    # Obtener búsquedas con filtro de búsqueda
    query = request.GET.get("q", "").strip()
    busquedas_list = _obtener_busquedas_filtradas(query, request.user)

    # Paginación
    paginator = Paginator(busquedas_list, 10)
    page = request.GET.get("page", 1)
    busquedas = paginator.get_page(page)

    # Obtener progreso de crawling activo
    progreso_activo = {}
    for busqueda in busquedas:
        progreso = CrawlingProgress.objects.filter(
            busqueda_id=busqueda.id, is_done=False
        ).first()
        if progreso:
            progreso_activo[busqueda.id] = {
                "urls_encontradas": progreso.urls_encontradas,
                "urls_procesadas": progreso.urls_procesadas,
                "errores": progreso.errores,
                "mensaje": progreso.mensaje_estado,
            }

    context = {
        "form": form,
        "busquedas": busquedas,
        "mensaje": mensaje,
        "query": query,
        "progreso_activo": progreso_activo,
    }

    return render(request, "analisis_dominio.html", context)


def _procesar_formulario_dominio(request):
    """Procesa los diferentes tipos de formularios en la vista de dominio"""

    if "eliminar_individual" in request.POST:
        return _eliminar_busqueda_individual(request)
    elif "guardar_individual" in request.POST:
        return _guardar_busqueda_individual(request)
    elif "desmarcar_guardado" in request.POST:
        return _desmarcar_busqueda_guardada(request)
    elif "eliminar_seleccionados" in request.POST or "eliminar_ids" in request.POST:
        return _eliminar_busquedas_seleccionadas(request)
    else:
        return _crear_nueva_busqueda(request)


def _eliminar_busqueda_individual(request):
    """Elimina una búsqueda individual"""

    eliminar_id = request.POST.get("eliminar_individual")

    try:
        busqueda_obj = BusquedaDominio.objects.get(id=eliminar_id)
        dominio_eliminado = busqueda_obj.dominio

        # Verificar si hay crawling activo
        if CrawlingService.verificar_crawling_activo(eliminar_id):
            return "No se puede eliminar el análisis porque hay un proceso de crawling activo. Por favor espera a que termine."

        # Eliminar registros relacionados
        CrawlingProgress.objects.filter(busqueda_id=eliminar_id).delete()
        BusquedaDominio.objects.filter(id=eliminar_id).delete()

        return f"Búsqueda del dominio '{dominio_eliminado}' eliminada correctamente."

    except BusquedaDominio.DoesNotExist:
        return "No se encontró el análisis seleccionado."


def _guardar_busqueda_individual(request):
    """Marca una búsqueda como guardada"""

    guardar_id = request.POST.get("guardar_individual")

    try:
        busqueda_obj = BusquedaDominio.objects.get(id=guardar_id)
        busqueda_obj.guardado = True
        busqueda_obj.save()
        return f"Dominio '{busqueda_obj.dominio}' marcado como guardado."
    except BusquedaDominio.DoesNotExist:
        return "No se encontró el análisis seleccionado."


def _desmarcar_busqueda_guardada(request):
    """Desmarca una búsqueda guardada"""

    desmarcar_id = request.POST.get("desmarcar_guardado")

    try:
        busqueda_obj = BusquedaDominio.objects.get(id=desmarcar_id)
        busqueda_obj.guardado = False
        busqueda_obj.save()
        return f"Dominio '{busqueda_obj.dominio}' desmarcado como guardado."
    except BusquedaDominio.DoesNotExist:
        return "No se encontró el análisis seleccionado."


def _eliminar_busquedas_seleccionadas(request):
    """Elimina múltiples búsquedas seleccionadas"""

    ids = request.POST.getlist("eliminar_ids")

    if not ids:
        return "No se seleccionaron elementos para eliminar."

    # Verificar crawling activo
    crawling_activo = CrawlingProgress.objects.filter(
        busqueda_id__in=ids, is_done=False
    ).exists()

    if crawling_activo:
        return "No se pueden eliminar los análisis seleccionados porque hay procesos de crawling activos. Por favor espera a que terminen o detén los procesos antes de eliminar."

    # Eliminar registros
    CrawlingProgress.objects.filter(busqueda_id__in=ids).delete()
    BusquedaDominio.objects.filter(id__in=ids).delete()

    return f"{len(ids)} búsquedas eliminadas correctamente."


def _crear_nueva_busqueda(request):
    """Crea una nueva búsqueda de dominio"""

    form = DominioForm(request.POST)

    if not form.is_valid():
        return "Por favor, ingresa un dominio válido."

    dominio_raw = form.cleaned_data["dominio"]
    dominio = normalizar_dominio(dominio_raw)

    if not dominio:
        return "El dominio ingresado no es válido."

    # Verificar si ya existe
    if BusquedaDominio.objects.filter(dominio=dominio, usuario=request.user).exists():
        return f"El dominio '{dominio}' ya ha sido analizado previamente."

    # Crear nueva búsqueda
    busqueda = AnalysisService.guardar_busqueda_ajax(dominio, [], request.user)
    return (
        f"Análisis del dominio '{dominio}' iniciado correctamente con ID: {busqueda.id}"
    )


def _obtener_busquedas_filtradas(query, user):
    """Obtiene las búsquedas filtradas por query"""

    busquedas_list = BusquedaDominio.objects.filter(usuario=user).order_by("-fecha")

    if query:
        busquedas_list = busquedas_list.filter(Q(dominio__icontains=query))

    return busquedas_list


@login_required
def iniciar_crawling_ajax(request):
    """API para iniciar crawling de un dominio"""

    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
        busqueda_id = data.get("busqueda_id")
        max_urls = data.get("max_urls", 50)

        if not busqueda_id:
            return JsonResponse({"error": "ID de búsqueda requerido"}, status=400)

        # Verificar que existe la búsqueda
        try:
            busqueda = BusquedaDominio.objects.get(id=busqueda_id)
        except BusquedaDominio.DoesNotExist:
            return JsonResponse({"error": "Búsqueda no encontrada"}, status=404)

        # Verificar si ya hay crawling activo
        if CrawlingService.verificar_crawling_activo(busqueda_id):
            return JsonResponse(
                {"error": "Ya hay un crawling activo para este dominio"}, status=409
            )

        # Crear registro de progreso
        progreso = CrawlingProgress.objects.create(
            busqueda_id=busqueda_id,
            urls_encontradas=0,
            urls_procesadas=0,
            errores=0,
            is_done=False,
            mensaje_estado="Iniciando crawling...",
        )

        # Iniciar crawling en hilo separado
        progress_key = f"crawl_{busqueda_id}"
        thread = threading.Thread(
            target=_crawling_worker,
            args=(busqueda.dominio, max_urls, progress_key, busqueda_id),
        )
        thread.daemon = True
        thread.start()

        return JsonResponse(
            {
                "success": True,
                "message": "Crawling iniciado correctamente",
                "progress_key": progress_key,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _crawling_worker(dominio, max_urls, progress_key, busqueda_id):
    """Worker que ejecuta el crawling en segundo plano"""

    try:
        # Ejecutar crawling
        urls = AnalysisService.crawl_urls_progress(dominio, max_urls, progress_key)

        # Guardar resultados
        busqueda = BusquedaDominio.objects.get(id=busqueda_id)
        busqueda.urls = json.dumps(urls)
        busqueda.fecha_fin = timezone.now()
        busqueda.save()

        # Actualizar progreso final
        progreso = CrawlingProgress.objects.filter(busqueda_id=busqueda_id).first()
        if progreso:
            progreso.is_done = True
            progreso.mensaje_estado = f"Completado: {len(urls)} URLs encontradas"
            progreso.save()

    except Exception as e:
        # Manejar errores
        progreso = CrawlingProgress.objects.filter(busqueda_id=busqueda_id).first()
        if progreso:
            progreso.is_done = True
            progreso.mensaje_estado = f"Error: {str(e)}"
            progreso.save()


@login_required
def progreso_crawling_ajax(request):
    """API para obtener el progreso del crawling"""

    busqueda_id = request.GET.get("busqueda_id")

    if not busqueda_id:
        return JsonResponse({"error": "ID de búsqueda requerido"}, status=400)

    try:
        progreso = CrawlingProgress.objects.filter(busqueda_id=busqueda_id).first()

        if not progreso:
            return JsonResponse(
                {"error": "No se encontró progreso para esta búsqueda"}, status=404
            )

        return JsonResponse(
            {
                "urls_encontradas": progreso.urls_encontradas,
                "urls_procesadas": progreso.urls_procesadas,
                "errores": progreso.errores,
                "completed": progreso.is_done,
                "status": progreso.mensaje_estado or "Procesando...",
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def api_status(request):
    """API simple de estado del sistema"""

    return JsonResponse({"status": "ok", "timestamp": timezone.now().isoformat()})
