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
        # Buscar el último análisis del usuario autenticado, o el más reciente si es admin
        busqueda = None
        if request.user.is_authenticated:
            busqueda = (
                BusquedaDominio.objects.filter(usuario=request.user)
                .order_by("-fecha")
                .first()
            )
        if not busqueda:
            busqueda = BusquedaDominio.objects.order_by("-fecha").first()
        if busqueda:
            import pytz

            tz = pytz.timezone(settings.TIME_ZONE)
            fecha_inicio = busqueda.fecha.astimezone(tz)
            fecha_fin = (
                busqueda.fecha_fin.astimezone(tz) if busqueda.fecha_fin else None
            )
            data = {
                "tipo": "dominio",
                "dominio": busqueda.dominio,
                "resultados": busqueda.get_urls(),
                "total_urls": len(busqueda.get_urls()),
                "timestamp": fecha_inicio.strftime("%Y-%m-%d %H:%M"),
                "usuario": busqueda.usuario.username if busqueda.usuario else None,
                "hora_inicio": fecha_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                "hora_fin": (
                    fecha_fin.strftime("%Y-%m-%d %H:%M:%S") if fecha_fin else None
                ),
                "duracion": None,
            }
            if fecha_fin:
                dur = fecha_fin - fecha_inicio
                total_seconds = int(dur.total_seconds())
                if total_seconds < 0:
                    data["duracion"] = "-"
                else:
                    h = total_seconds // 3600
                    m = (total_seconds % 3600) // 60
                    s = total_seconds % 60
                    data["duracion"] = f"{h:02}:{m:02}:{s:02}"
            status = "SUCCESS"
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
                        "urls": data["resultados"] if data else [],
                        "timestamp": data["timestamp"] if data else None,
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
