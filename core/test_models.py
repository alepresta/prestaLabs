from django.test import TestCase
from django.contrib.auth.models import User
from core.models import BaseModel
from django.utils import timezone


class BaseModelTest(TestCase):
    def test_base_model_fields(self):
        class DummyModel(BaseModel):
            class Meta:
                app_label = "core"

        obj = DummyModel()
        now = timezone.now()
        obj.created_at = now
        obj.updated_at = now
        self.assertEqual(obj.created_at, now)
        self.assertEqual(obj.updated_at, now)


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="12345678",  # nosec
        )
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("12345678"))
