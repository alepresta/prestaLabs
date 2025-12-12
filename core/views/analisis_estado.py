from django.shortcuts import render
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from celery.result import AsyncResult
from django.conf import settings


@csrf_exempt
@login_required
def analisis_estado(request):
    from core.models import BusquedaDominio

    task_id = request.session.get("analisis_task_id") or request.GET.get("task_id")
    result = None
    status = None
    data = None
    error = None
    if task_id:
        result = AsyncResult(task_id)
        status = result.status
        if result.successful():
            data = result.result
        elif result.failed():
            error = str(result.result)
    # Si no hay task_id o no hay resultado, buscar el último BusquedaDominio
    if not task_id or (
        status is not None and status in ["PENDING", "REVOKED", "FAILURE"]
    ):
        # Buscar el último análisis EN PROGRESO del usuario autenticado (sin fecha_fin)
        busqueda = None
        if request.user.is_authenticated:
            busqueda = (
                BusquedaDominio.objects.filter(
                    usuario=request.user,
                    fecha_fin__isnull=True,  # Solo búsquedas EN PROGRESO (sin finalizar)
                )
                .order_by("-fecha")  # Ordenar por fecha de inicio más reciente
                .first()
            )
        if not busqueda:
            # Si no hay del usuario, buscar cualquier crawling activo
            busqueda = (
                BusquedaDominio.objects.filter(fecha_fin__isnull=True)
                .order_by("-fecha")
                .first()
            )
        if busqueda:
            import pytz
            from core.models import CrawlingProgress

            tz = pytz.timezone(settings.TIME_ZONE)
            fecha_inicio = busqueda.fecha.astimezone(tz)

            # Buscar progreso activo asociado a esta búsqueda
            progreso = None
            try:
                progreso = CrawlingProgress.objects.get(
                    busqueda_id=busqueda.id, is_done=False
                )
            except CrawlingProgress.DoesNotExist:
                pass

            # Si tenemos progreso activo, usar esos datos. Si no, usar los de BusquedaDominio
            if progreso:
                urls_list = progreso.get_urls_list()
                total_urls = progreso.count
                resultados = urls_list
            else:
                urls_list = busqueda.get_urls()
                total_urls = len(urls_list)
                resultados = urls_list

            data = {
                "tipo": "dominio",
                "dominio": busqueda.dominio,
                "resultados": resultados,
                "total_urls": total_urls,
                "timestamp": fecha_inicio.strftime("%Y-%m-%d %H:%M"),
                "usuario": busqueda.usuario.username if busqueda.usuario else None,
                "hora_inicio": fecha_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                "hora_fin": None,  # Siempre None para crawlings en progreso
                "duracion": None,
            }
            # Para crawlings en progreso, calcular duración desde el inicio hasta ahora
            from django.utils import timezone

            ahora = timezone.now().astimezone(tz)
            dur = ahora - fecha_inicio
            total_seconds = int(dur.total_seconds())
            if total_seconds < 0:
                data["duracion"] = "00:00:00"
            else:
                h = total_seconds // 3600
                m = (total_seconds % 3600) // 60
                s = total_seconds % 60
                data["duracion"] = f"{h:02}:{m:02}:{s:02}"

            # Status para crawling en progreso
            status = "PROGRESS" if total_urls > 0 else "PENDING"
            error = None
            task_id = None
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "status": status or "UNKNOWN",
                "result": data,
                "error": error,
                "task_id": task_id,
                "progreso": (
                    {
                        "dominio": data["dominio"] if data else None,
                        "total": data["total_urls"] if data else 0,
                        "count": data["total_urls"] if data else 0,
                        "urls": data["resultados"] if data else [],
                        "timestamp": data["timestamp"] if data else None,
                        "porcentaje": (
                            min(99, data["total_urls"])
                            if (data and data["total_urls"] > 0)
                            else 0
                        ),  # Nunca 100% para progreso activo
                        "hora_inicio": data["hora_inicio"] if data else None,
                        "hora_fin": None,  # Siempre None para progreso activo
                        "duracion": data["duracion"] if data else None,
                        "last_url": (
                            data["resultados"][-1]
                            if (data and data["resultados"])
                            else None
                        ),
                    }
                    if data
                    else {}
                ),
            }
        )
    return render(
        request,
        "analisis/estado.html",
        {"task_id": task_id, "status": status, "result": data, "error": error},
    )
