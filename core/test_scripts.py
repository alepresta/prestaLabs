import subprocess  # nosec
import os
from django.test import TestCase


class ScriptTestCase(TestCase):
    def test_verificar_integridad_script(self):
        """
        Testea que el script verificar_integridad.sh se ejecuta correctamente
        (solo verifica que ejecuta sin error)
        """
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "verificar_integridad.sh",
        )
        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,  # nosec
        )
        self.assertEqual(result.returncode, 0)

    def test_install_sh_ayuda(self):
        """Testea que el script install.sh ejecuta la ayuda sin error"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "install.sh",
        )
        result = subprocess.run(
            ["bash", script_path, "ayuda"],
            capture_output=True,
            text=True,  # nosec
        )
        self.assertEqual(result.returncode, 0)
