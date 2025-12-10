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


# Formulario para que un admin cambie la contraseña de cualquier usuario
class AdminSetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput,
        strip=False,
        help_text="Ingrese la nueva contraseña.",
    )
    new_password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput,
        strip=False,
        help_text="Repita la nueva contraseña.",
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password1")
        p2 = cleaned_data.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data
