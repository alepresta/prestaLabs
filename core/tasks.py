from celery import shared_task


@shared_task(bind=True)
def tarea_analisis_dominio(self, dominio):
    from core.views.analisis_views import buscar_sitemap, procesar_sitemap
    from django.utils import timezone
    from core.utils.task_progress import set_task_progress

    resultados = []
    sitemap_url, sitemap_content = buscar_sitemap(dominio)
    progreso = {
        "dominio": dominio,
        "status": "IN_PROGRESS",
        "urls": [],
        "total": 0,
        "error": None,
        "timestamp": str(timezone.now()),
    }
    set_task_progress(self.request.id, progreso)
    if sitemap_url and sitemap_content:
        try:
            urls = procesar_sitemap(sitemap_content, f"https://{dominio}", max_urls=100)
            if urls:
                for url in urls:
                    resultados.append(
                        {
                            "url": url,
                            "estado": "OK",
                            "detalles": f"Encontrado en sitemap: {url}",
                        }
                    )
                    # Actualizar progreso parcial
                    progreso["urls"].append(url)
                    progreso["total"] = len(progreso["urls"])
                    set_task_progress(self.request.id, progreso)
                total_encontradas = len(urls)
                progreso["status"] = "SUCCESS"
                set_task_progress(self.request.id, progreso)
                return {
                    "tipo": "dominio",
                    "dominio": dominio,
                    "sitemap_url": sitemap_url,
                    "resultados": resultados,
                    "total_urls": total_encontradas,
                    "timestamp": str(timezone.now()),
                }
            else:
                progreso["status"] = "FAILURE"
                progreso["error"] = "Sitemap encontrado pero no contiene URLs válidas"
                set_task_progress(self.request.id, progreso)
                return {"error": "Sitemap encontrado pero no contiene URLs válidas"}
        except Exception as e:
            progreso["status"] = "FAILURE"
            progreso["error"] = str(e)
            set_task_progress(self.request.id, progreso)
            return {"error": f"Error procesando sitemap: {str(e)}"}
    else:
        resultados.append(
            {
                "url": f"https://{dominio}",
                "estado": "SIN SITEMAP",
                "detalles": "Analizando solo página principal (no se encontró sitemap)",
            }
        )
        progreso["status"] = "FAILURE"
        progreso["error"] = "No se encontró sitemap para el dominio."
        set_task_progress(self.request.id, progreso)
        return {
            "tipo": "dominio",
            "dominio": dominio,
            "sitemap_url": None,
            "resultados": resultados,
            "total_urls": 1,
            "timestamp": str(timezone.now()),
        }
