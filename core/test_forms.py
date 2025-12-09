from django.test import TestCase
from django.contrib.auth.models import User
from core.forms import UsuarioLecturaForm, EditarUsuarioForm


class UsuarioLecturaFormTest(TestCase):
    def test_form_valido(self):
        form = UsuarioLecturaForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "password": "12345678",  # nosec
            }
        )
        self.assertTrue(form.is_valid())

    def test_form_invalido(self):
        form = UsuarioLecturaForm(data={})
        self.assertFalse(form.is_valid())


class EditarUsuarioFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="edituser",
            email="edit@example.com",
            password="12345678",  # nosec
        )

    def test_form_valido(self):
        form = EditarUsuarioForm(
            data={
                "username": "edituser",
                "email": "edit@example.com",
                "is_active": True,
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid())

    def test_form_invalido(self):
        form = EditarUsuarioForm(data={"username": ""}, instance=self.user)
        self.assertFalse(form.is_valid())
