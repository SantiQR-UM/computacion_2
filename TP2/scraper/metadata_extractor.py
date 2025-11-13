"""
Extractor de metadatos.

Este módulo proporciona funcionalidades especializadas para extraer
metadatos específicos de páginas web (SEO, Open Graph, Twitter Cards, etc.).
"""

from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    Extractor especializado de metadatos.

    Extrae metadatos comunes de páginas web: SEO, Open Graph, Twitter Cards, etc.
    """

    def __init__(self, html: str):
        """
        Inicializa el extractor con HTML.

        Args:
            html: Contenido HTML
        """
        self.soup = BeautifulSoup(html, 'html.parser')

    def extract_basic_metadata(self) -> Dict[str, Optional[str]]:
        """
        Extrae metadatos básicos de SEO.

        Returns:
            Diccionario con metadatos básicos
        """
        metadata = {
            'description': self._get_meta_content('description'),
            'keywords': self._get_meta_content('keywords'),
            'author': self._get_meta_content('author'),
            'robots': self._get_meta_content('robots'),
            'viewport': self._get_meta_content('viewport'),
            'canonical': self._get_canonical_url()
        }

        return {k: v for k, v in metadata.items() if v is not None}

    def extract_open_graph(self) -> Dict[str, str]:
        """
        Extrae metadatos de Open Graph.

        Returns:
            Diccionario con metadatos de Open Graph
        """
        og_metadata = {}

        for meta_tag in self.soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
            prop = meta_tag.get('property', '')
            content = meta_tag.get('content', '')

            if prop and content:
                og_metadata[prop] = content

        logger.debug(f"Extraídos {len(og_metadata)} metadatos Open Graph")
        return og_metadata

    def extract_twitter_card(self) -> Dict[str, str]:
        """
        Extrae metadatos de Twitter Card.

        Returns:
            Diccionario con metadatos de Twitter Card
        """
        twitter_metadata = {}

        for meta_tag in self.soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')}):
            name = meta_tag.get('name', '')
            content = meta_tag.get('content', '')

            if name and content:
                twitter_metadata[name] = content

        logger.debug(f"Extraídos {len(twitter_metadata)} metadatos Twitter Card")
        return twitter_metadata

    def extract_structured_data(self) -> List[str]:
        """
        Extrae datos estructurados (JSON-LD, Microdata, etc.).

        Returns:
            Lista de strings con los datos estructurados
        """
        structured_data = []

        # JSON-LD
        for script in self.soup.find_all('script', type='application/ld+json'):
            if script.string:
                structured_data.append(script.string.strip())

        logger.debug(f"Extraídos {len(structured_data)} bloques de datos estructurados")
        return structured_data

    def extract_all_metadata(self) -> Dict:
        """
        Extrae todos los metadatos relevantes.

        Returns:
            Diccionario con todos los metadatos organizados por categoría
        """
        return {
            'basic': self.extract_basic_metadata(),
            'open_graph': self.extract_open_graph(),
            'twitter_card': self.extract_twitter_card(),
            'structured_data': self.extract_structured_data()
        }

    def _get_meta_content(self, name: str) -> Optional[str]:
        """
        Obtiene el contenido de un meta tag por nombre.

        Args:
            name: Nombre del meta tag

        Returns:
            Contenido del meta tag o None si no existe
        """
        meta_tag = self.soup.find('meta', attrs={'name': name})
        if meta_tag:
            return meta_tag.get('content', '').strip() or None
        return None

    def _get_canonical_url(self) -> Optional[str]:
        """
        Obtiene la URL canónica de la página.

        Returns:
            URL canónica o None si no existe
        """
        link_tag = self.soup.find('link', rel='canonical')
        if link_tag:
            return link_tag.get('href', '').strip() or None
        return None


def extract_relevant_metadata(html: str) -> Dict[str, str]:
    """
    Función de conveniencia para extraer metadatos relevantes.

    Extrae los metadatos más comunes en un formato simplificado
    para la respuesta del servidor.

    Args:
        html: Contenido HTML

    Returns:
        Diccionario con metadatos relevantes
    """
    extractor = MetadataExtractor(html)

    basic = extractor.extract_basic_metadata()
    og = extractor.extract_open_graph()
    twitter = extractor.extract_twitter_card()

    # Combinar metadatos priorizando Open Graph, luego Twitter, luego básicos
    metadata = {}

    # Description
    metadata['description'] = (
        og.get('og:description') or
        twitter.get('twitter:description') or
        basic.get('description') or
        ''
    )

    # Keywords
    if basic.get('keywords'):
        metadata['keywords'] = basic['keywords']

    # Title
    og_title = og.get('og:title')
    if og_title:
        metadata['og:title'] = og_title

    twitter_title = twitter.get('twitter:title')
    if twitter_title:
        metadata['twitter:title'] = twitter_title

    # Image
    og_image = og.get('og:image')
    if og_image:
        metadata['og:image'] = og_image

    twitter_image = twitter.get('twitter:image')
    if twitter_image:
        metadata['twitter:image'] = twitter_image

    # Type
    og_type = og.get('og:type')
    if og_type:
        metadata['og:type'] = og_type

    # URL
    og_url = og.get('og:url')
    if og_url:
        metadata['og:url'] = og_url

    # Site name
    og_site_name = og.get('og:site_name')
    if og_site_name:
        metadata['og:site_name'] = og_site_name

    # Author
    if basic.get('author'):
        metadata['author'] = basic['author']

    # Canonical
    if basic.get('canonical'):
        metadata['canonical'] = basic['canonical']

    logger.info(f"Metadatos relevantes extraídos: {len(metadata)} campos")
    return metadata
