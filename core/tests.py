from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

# Create your tests here.

class CoreViewsTest(TestCase):
    """Tests para las vistas de core"""
    
    def test_index_view(self):
        """Test de la vista principal"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PrestaLabs')
    
    def test_api_status(self):
        """Test del endpoint de estado"""
        response = self.client.get('/status/')
        self.assertEqual(response.status_code, 200)