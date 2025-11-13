"""
Parser de HTML.

Este módulo proporciona funcionalidades para parsear HTML usando BeautifulSoup
y extraer información estructurada.
"""

from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class HTMLParseError(Exception):
    """Excepción para errores de parsing HTML."""
    pass


class HTMLParser:
    """
    Parser de HTML basado en BeautifulSoup.

    Extrae información estructurada de documentos HTML.
    """

    def __init__(self, html: str, base_url: Optional[str] = None):
        """
        Inicializa el parser con HTML.

        Args:
            html: Contenido HTML a parsear
            base_url: URL base para resolver URLs relativas (opcional)

        Raises:
            HTMLParseError: Si el HTML no puede ser parseado
        """
        try:
            self.soup = BeautifulSoup(html, 'html.parser')
            self.base_url = base_url
            logger.debug(f"HTML parseado exitosamente ({len(html)} bytes)")
        except Exception as e:
            raise HTMLParseError(f"Error al parsear HTML: {e}")

    def get_title(self) -> Optional[str]:
        """
        Obtiene el título de la página.

        Returns:
            Título de la página o None si no existe
        """
        title_tag = self.soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        return None

    def get_links(self, absolute: bool = True) -> List[str]:
        """
        Obtiene todos los enlaces de la página.

        Args:
            absolute: Si es True, convierte URLs relativas a absolutas

        Returns:
            Lista de URLs encontradas
        """
        links = []
        for a_tag in self.soup.find_all('a', href=True):
            href = a_tag['href'].strip()

            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue

            if absolute and self.base_url:
                href = urljoin(self.base_url, href)

            links.append(href)

        logger.debug(f"Encontrados {len(links)} enlaces")
        return links

    def get_images(self, absolute: bool = True) -> List[Dict[str, str]]:
        """
        Obtiene todas las imágenes de la página.

        Args:
            absolute: Si es True, convierte URLs relativas a absolutas

        Returns:
            Lista de diccionarios con información de cada imagen
        """
        images = []
        for img_tag in self.soup.find_all('img'):
            src = img_tag.get('src', '').strip()

            if not src:
                continue

            if absolute and self.base_url:
                src = urljoin(self.base_url, src)

            images.append({
                'src': src,
                'alt': img_tag.get('alt', ''),
                'title': img_tag.get('title', '')
            })

        logger.debug(f"Encontradas {len(images)} imágenes")
        return images

    def get_meta_tags(self) -> Dict[str, str]:
        """
        Obtiene todos los meta tags de la página.

        Returns:
            Diccionario con los meta tags (name/property -> content)
        """
        meta_tags = {}

        for meta_tag in self.soup.find_all('meta'):
            # Meta tags con atributo 'name'
            name = meta_tag.get('name', '').strip()
            if name:
                content = meta_tag.get('content', '').strip()
                if content:
                    meta_tags[name] = content

            # Meta tags con atributo 'property' (Open Graph, etc.)
            prop = meta_tag.get('property', '').strip()
            if prop:
                content = meta_tag.get('content', '').strip()
                if content:
                    meta_tags[prop] = content

        logger.debug(f"Encontrados {len(meta_tags)} meta tags")
        return meta_tags

    def get_headers_structure(self) -> Dict[str, int]:
        """
        Obtiene la estructura de headers (H1-H6) de la página.

        Returns:
            Diccionario con el conteo de cada tipo de header
        """
        structure = {
            'h1': len(self.soup.find_all('h1')),
            'h2': len(self.soup.find_all('h2')),
            'h3': len(self.soup.find_all('h3')),
            'h4': len(self.soup.find_all('h4')),
            'h5': len(self.soup.find_all('h5')),
            'h6': len(self.soup.find_all('h6'))
        }

        total = sum(structure.values())
        logger.debug(f"Estructura de headers: {total} headers totales")

        return structure

    def get_text(self, separator: str = ' ') -> str:
        """
        Obtiene todo el texto visible de la página.

        Args:
            separator: Separador entre elementos de texto

        Returns:
            Texto extraído
        """
        # Remover scripts y styles
        for script in self.soup(['script', 'style']):
            script.decompose()

        text = self.soup.get_text(separator=separator)
        # Limpiar espacios múltiples
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text

    def count_elements(self, tag: str) -> int:
        """
        Cuenta el número de elementos de un tag específico.

        Args:
            tag: Nombre del tag HTML

        Returns:
            Número de elementos encontrados
        """
        return len(self.soup.find_all(tag))

    def find_schema_org(self) -> List[Dict]:
        """
        Busca y extrae schema.org JSON-LD.

        Returns:
            Lista de diccionarios con los schemas encontrados
        """
        import json

        schemas = []
        for script in self.soup.find_all('script', type='application/ld+json'):
            try:
                schema = json.loads(script.string)
                schemas.append(schema)
            except (json.JSONDecodeError, AttributeError):
                continue

        logger.debug(f"Encontrados {len(schemas)} schemas JSON-LD")
        return schemas

    def get_forms(self) -> List[Dict[str, any]]:
        """
        Obtiene información sobre los formularios de la página.

        Returns:
            Lista de diccionarios con información de cada formulario
        """
        forms = []
        for form_tag in self.soup.find_all('form'):
            form_info = {
                'action': form_tag.get('action', ''),
                'method': form_tag.get('method', 'get').upper(),
                'inputs': []
            }

            # Contar inputs
            for input_tag in form_tag.find_all('input'):
                input_type = input_tag.get('type', 'text')
                input_name = input_tag.get('name', '')
                form_info['inputs'].append({
                    'type': input_type,
                    'name': input_name
                })

            forms.append(form_info)

        logger.debug(f"Encontrados {len(forms)} formularios")
        return forms


def parse_html(html: str, base_url: Optional[str] = None) -> HTMLParser:
    """
    Función de conveniencia para crear un parser.

    Args:
        html: Contenido HTML
        base_url: URL base (opcional)

    Returns:
        Instancia de HTMLParser

    Raises:
        HTMLParseError: Si el HTML no puede ser parseado
    """
    return HTMLParser(html, base_url)


def extract_all_info(html: str, base_url: Optional[str] = None) -> Dict:
    """
    Extrae toda la información relevante de un HTML.

    Args:
        html: Contenido HTML
        base_url: URL base (opcional)

    Returns:
        Diccionario con toda la información extraída

    Raises:
        HTMLParseError: Si el HTML no puede ser parseado
    """
    parser = HTMLParser(html, base_url)

    return {
        'title': parser.get_title(),
        'links': parser.get_links(),
        'images': parser.get_images(),
        'images_count': len(parser.get_images()),
        'meta_tags': parser.get_meta_tags(),
        'structure': parser.get_headers_structure(),
        'forms_count': len(parser.get_forms()),
        'schemas': parser.find_schema_org()
    }
