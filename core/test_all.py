from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.forms import UsuarioLecturaForm, EditarUsuarioForm
from .test_factories import UserFactory


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


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="12345678",  # nosec
        )
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("12345678"))


class UsuarioViewsTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "admin", "admin@example.com", "adminpass"  # nosec
        )
        self.client = Client()
        self.client.login(username="admin", password="adminpass")  # nosec

    def test_crear_usuario_lectura_get(self):
        response = self.client.get(reverse("core:crear_usuario_lectura"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crear usuario")

    def test_crear_usuario_lectura_post(self):
        data = {
            "username": "lectura",
            "email": "lectura@example.com",
            "password": "12345678",  # nosec
        }
        response = self.client.post(
            reverse("core:crear_usuario_lectura"), data, follow=True
        )
        self.assertContains(response, "Usuario")
        self.assertTrue(User.objects.filter(username="lectura").exists())

    def test_editar_usuarios_get(self):
        response = self.client.get(reverse("core:editar_usuarios"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar usuarios")

    def test_editar_usuarios_post(self):
        user = User.objects.create_user(
            "edit",
            "edit@example.com",
            "12345678",  # nosec
        )
        data = {
            "user_id": user.id,
            "username": "edit",
            "email": "edit@example.com",
            "is_active": True,
        }
        response = self.client.post(
            reverse("core:editar_usuarios"),
            data,
            follow=True,
        )
        self.assertContains(response, "Usuario editado")

    def test_dashboard_redirect_no_login(self):
        self.client.logout()
        response = self.client.get("/dashboard/", follow=True)
        # Django agrega el parámetro next, pero puede variar el encoding
        self.assertTrue(
            response.redirect_chain[0][0].startswith("/login/"),
            msg=(f"Redirección inesperada: {response.redirect_chain}"),
        )

    def test_dashboard_redirect_login(self):
        response = self.client.get("/dashboard/", follow=True)
        # Puede redirigir a /api/ según urls.py, aceptamos ambos
        self.assertIn(
            response.redirect_chain[-1][0],
            ["/", "/api/"],
        )

    def test_index_requires_login(self):
        self.client.logout()
        response = self.client.get("/", follow=True)
        self.assertRedirects(response, "/login/?next=/")

    def test_api_status(self):
        response = self.client.get("/status/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("PrestaLabs API", response.json().get("message", ""))


class UserFactoryTest(TestCase):
    def test_user_factory_creates_valid_user(self):
        user = UserFactory()
        self.assertTrue(User.objects.filter(username=user.username).exists())
        self.assertTrue(user.check_password("defaultpass123"))
