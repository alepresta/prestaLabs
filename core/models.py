from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class BaseModel(models.Model):
    """Modelo base con campos comunes"""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BusquedaDominio(BaseModel):
    dominio = models.CharField(max_length=255)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    urls = models.TextField(
        help_text="Lista de URLs encontradas, separadas por salto de línea"
    )

    def get_urls(self):
        return self.urls.split("\n") if self.urls else []

    def __str__(self):
        return (
            f"{self.dominio} ({self.fecha:%Y-%m-%d %H:%M}) por {self.usuario}"
            if self.usuario
            else f"{self.dominio} ({self.fecha:%Y-%m-%d %H:%M})"
        )
