from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class BaseModel(models.Model):
    """Modelo base con campos comunes"""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CrawlingProgress(BaseModel):
    """Modelo para almacenar el progreso del crawling de forma persistente"""

    progress_key = models.CharField(max_length=255, unique=True, db_index=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    dominio = models.CharField(max_length=255)
    count = models.IntegerField(default=0)
    last_url = models.TextField(blank=True)
    is_done = models.BooleanField(default=False)
    urls_found = models.TextField(
        blank=True, help_text="URLs encontradas separadas por |"
    )
    busqueda_id = models.IntegerField(
        null=True, blank=True, help_text="ID de BusquedaDominio relacionado"
    )
    task_id = models.CharField(
        max_length=255, null=True, blank=True, help_text="ID de la tarea Celery"
    )

    def get_urls_list(self):
        return self.urls_found.split("|") if self.urls_found else []

    def add_url(self, url):
        urls = self.get_urls_list()
        urls.append(url)
        self.urls_found = "|".join(urls)
        self.count = len(urls)

    def __str__(self):
        return f"Progreso {self.dominio} - {self.count} URLs ({'✓' if self.is_done else '⏳'})"


class BusquedaDominio(BaseModel):
    dominio = models.CharField(max_length=255)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(
        null=True, blank=True, help_text="Hora de finalización del crawling"
    )
    urls = models.TextField(
        help_text="Lista de URLs encontradas, separadas por salto de línea"
    )
    guardado = models.BooleanField(
        default=False, help_text="Indica si el dominio ha sido marcado como guardado"
    )

    def get_urls(self):
        return self.urls.split("\n") if self.urls else []

    def __str__(self):
        return (
            f"{self.dominio} ({self.fecha:%Y-%m-%d %H:%M}) por {self.usuario}"
            if self.usuario
            else f"{self.dominio} ({self.fecha:%Y-%m-%d %H:%M})"
        )


class UrlGuardada(BaseModel):
    """Modelo para almacenar URLs individuales guardadas por el usuario"""

    url = models.URLField(max_length=2000, help_text="URL individual guardada")
    titulo = models.CharField(
        max_length=500, blank=True, help_text="Título de la página (opcional)"
    )
    dominio = models.CharField(
        max_length=255, help_text="Dominio al que pertenece la URL"
    )
    busqueda_dominio = models.ForeignKey(
        BusquedaDominio,
        on_delete=models.CASCADE,
        help_text="Búsqueda de dominio de la que proviene esta URL",
    )
    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, help_text="Usuario que guardó la URL"
    )
    notas = models.TextField(blank=True, help_text="Notas adicionales del usuario")

    class Meta:
        unique_together = ["url", "usuario"]  # Evitar duplicados por usuario

    def __str__(self):
        return f"{self.url} (guardada por {self.usuario.username})"
