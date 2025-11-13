"""
Tests de integración.

Prueba el funcionamiento completo del sistema con ambos servidores.
Nota: Estos tests requieren que los servidores estén ejecutándose.
"""

import unittest
import time
import requests
from multiprocessing import Process
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntegration(unittest.TestCase):
    """Tests de integración del sistema completo."""

    @classmethod
    def setUpClass(cls):
        """Configura los servidores para los tests."""
        # Nota: En un entorno de testing real, deberías levantar los servidores aquí
        # Por ahora, asumimos que los servidores están ejecutándose
        cls.scraping_server = "http://127.0.0.1:8000"
        cls.test_url = "https://example.com"

        # Esperar a que los servidores estén listos
        time.sleep(1)

    def test_health_endpoint(self):
        """Test del endpoint de health check."""
        try:
            response = requests.get(f"{self.scraping_server}/health", timeout=5)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertEqual(data['status'], 'healthy')
            self.assertIn('timestamp', data)

        except requests.RequestException as e:
            self.skipTest(f"Servidor no disponible: {e}")

    def test_scrape_endpoint(self):
        """Test del endpoint de scraping."""
        try:
            response = requests.get(
                f"{self.scraping_server}/scrape",
                params={'url': self.test_url},
                timeout=120
            )

            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['url'], self.test_url)
            self.assertIn('scraping_data', data)
            self.assertIn('processing_data', data)
            self.assertIn('timestamp', data)

            # Verificar datos de scraping
            scraping = data['scraping_data']
            self.assertIn('title', scraping)
            self.assertIn('links', scraping)
            self.assertIn('meta_tags', scraping)
            self.assertIn('structure', scraping)
            self.assertIn('images_count', scraping)

            # Verificar datos de procesamiento
            processing = data['processing_data']
            self.assertIn('screenshot', processing)
            self.assertIn('performance', processing)
            self.assertIn('thumbnails', processing)

        except requests.RequestException as e:
            self.skipTest(f"Servidor no disponible: {e}")

    def test_scrape_invalid_url(self):
        """Test de scraping con URL inválida."""
        try:
            response = requests.get(
                f"{self.scraping_server}/scrape",
                params={'url': 'not-a-valid-url'},
                timeout=10
            )

            self.assertEqual(response.status_code, 400)

            data = response.json()
            self.assertEqual(data['status'], 'error')

        except requests.RequestException as e:
            self.skipTest(f"Servidor no disponible: {e}")

    def test_scrape_missing_url(self):
        """Test de scraping sin URL."""
        try:
            response = requests.get(
                f"{self.scraping_server}/scrape",
                timeout=10
            )

            self.assertEqual(response.status_code, 400)

            data = response.json()
            self.assertEqual(data['status'], 'error')

        except requests.RequestException as e:
            self.skipTest(f"Servidor no disponible: {e}")


if __name__ == '__main__':
    print("=" * 80)
    print("TESTS DE INTEGRACIÓN")
    print("=" * 80)
    print()
    print("IMPORTANTE: Estos tests requieren que los servidores estén ejecutándose:")
    print("  1. python server_processing.py -i 127.0.0.1 -p 8001")
    print("  2. python server_scraping.py -i 127.0.0.1 -p 8000")
    print()
    print("Esperando 3 segundos antes de comenzar los tests...")
    print()

    time.sleep(3)

    unittest.main()
