from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class BaseModel(models.Model):
    """Modelo base con campos comunes"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True