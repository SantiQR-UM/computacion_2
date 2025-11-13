"""
Tests para el módulo de parsing HTML.

Prueba las funcionalidades de extracción de información de HTML.
"""

import unittest
from scraper.html_parser import HTMLParser, extract_all_info


class TestHTMLParser(unittest.TestCase):
    """Tests para el parser HTML."""

    def setUp(self):
        """Configura HTML de ejemplo para tests."""
        self.html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="Test description">
            <meta name="keywords" content="test, page">
            <meta property="og:title" content="OG Title">
        </head>
        <body>
            <h1>Header 1</h1>
            <h2>Header 2</h2>
            <h2>Another H2</h2>
            <h3>Header 3</h3>
            <p>Some text content</p>
            <a href="https://example.com">Link 1</a>
            <a href="/relative">Link 2</a>
            <img src="image1.jpg" alt="Image 1">
            <img src="image2.jpg" alt="Image 2">
        </body>
        </html>
        """

        self.base_url = "https://example.com"

    def test_get_title(self):
        """Test de extracción de título."""
        parser = HTMLParser(self.html)
        title = parser.get_title()

        self.assertEqual(title, "Test Page")

    def test_get_links(self):
        """Test de extracción de links."""
        parser = HTMLParser(self.html, base_url=self.base_url)
        links = parser.get_links(absolute=True)

        self.assertEqual(len(links), 2)
        self.assertIn("https://example.com", links)
        self.assertIn("https://example.com/relative", links)

    def test_get_images(self):
        """Test de extracción de imágenes."""
        parser = HTMLParser(self.html, base_url=self.base_url)
        images = parser.get_images(absolute=True)

        self.assertEqual(len(images), 2)
        self.assertIn("https://example.com/image1.jpg", [img['src'] for img in images])
        self.assertEqual(images[0]['alt'], "Image 1")

    def test_get_meta_tags(self):
        """Test de extracción de meta tags."""
        parser = HTMLParser(self.html)
        meta_tags = parser.get_meta_tags()

        self.assertIn('description', meta_tags)
        self.assertEqual(meta_tags['description'], "Test description")
        self.assertIn('keywords', meta_tags)
        self.assertIn('og:title', meta_tags)

    def test_get_headers_structure(self):
        """Test de extracción de estructura de headers."""
        parser = HTMLParser(self.html)
        structure = parser.get_headers_structure()

        self.assertEqual(structure['h1'], 1)
        self.assertEqual(structure['h2'], 2)
        self.assertEqual(structure['h3'], 1)
        self.assertEqual(structure['h4'], 0)

    def test_count_elements(self):
        """Test de conteo de elementos."""
        parser = HTMLParser(self.html)

        self.assertEqual(parser.count_elements('img'), 2)
        self.assertEqual(parser.count_elements('a'), 2)
        self.assertEqual(parser.count_elements('p'), 1)

    def test_extract_all_info(self):
        """Test de extracción completa de información."""
        info = extract_all_info(self.html, base_url=self.base_url)

        self.assertEqual(info['title'], "Test Page")
        self.assertEqual(len(info['links']), 2)
        self.assertEqual(info['images_count'], 2)
        self.assertIn('description', info['meta_tags'])
        self.assertEqual(info['structure']['h1'], 1)


if __name__ == '__main__':
    unittest.main()
