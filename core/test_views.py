from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


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
