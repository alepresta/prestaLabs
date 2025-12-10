"""
Archivo de formularios globales para la app core.
Mover formularios de views.py aquí para mayor claridad y escalabilidad.
"""

from django import forms
from django.contrib.auth.models import User


class DominioForm(forms.Form):
    dominio = forms.CharField(
        label="Dominio", max_length=255, help_text="Ejemplo: ejemplo.com"
    )


class UsuarioLecturaForm(forms.Form):
    """Formulario para crear usuario de solo lectura"""

    username = forms.CharField(label="Usuario", max_length=150)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)


class EditarUsuarioForm(forms.ModelForm):
    """Formulario para editar usuario"""

    class Meta:
        model = User
        fields = ["username", "email", "is_active"]
