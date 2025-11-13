"""
Análisis de rendimiento de páginas web.

Este módulo analiza el rendimiento de páginas web:
tiempo de carga, tamaño de recursos, número de requests, etc.
"""

import logging
import time
from typing import Dict, List, Tuple
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PerformanceError(Exception):
    """Excepción para errores de análisis de rendimiento."""
    pass


def analyze_page_performance(url: str, timeout: int = 30) -> Dict:
    """
    Analiza el rendimiento de una página web.

    Args:
        url: URL de la página a analizar
        timeout: Timeout en segundos

    Returns:
        Diccionario con métricas de rendimiento

    Raises:
        PerformanceError: Si hay un error al analizar
    """
    try:
        logger.debug(f"Analizando rendimiento de {url}")

        # Medir tiempo de carga de la página principal
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        load_time_ms = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            raise PerformanceError(f"HTTP {response.status_code}")

        html = response.text
        html_size = len(html.encode('utf-8'))

        # Parsear HTML para encontrar recursos
        soup = BeautifulSoup(html, 'html.parser')

        # Encontrar todos los recursos
        resources = _extract_resources(soup, url)

        # Calcular estadísticas
        total_size_kb = html_size / 1024
        num_requests = 1  # La página HTML principal

        resource_details = []

        for resource_url, resource_type in resources[:20]:  # Limitar a 20 recursos para no tardar mucho
            try:
                res_start = time.time()
                res_response = requests.head(resource_url, timeout=5, allow_redirects=True)
                res_time = int((time.time() - res_start) * 1000)

                if res_response.status_code == 200:
                    content_length = int(res_response.headers.get('Content-Length', 0))
                    total_size_kb += content_length / 1024
                    num_requests += 1

                    resource_details.append({
                        'url': resource_url,
                        'type': resource_type,
                        'size_kb': round(content_length / 1024, 2),
                        'load_time_ms': res_time
                    })
            except Exception as e:
                logger.debug(f"No se pudo obtener info de {resource_url}: {e}")
                continue

        logger.info(f"Análisis de rendimiento completado: {num_requests} requests, {total_size_kb:.2f} KB")

        return {
            'success': True,
            'load_time_ms': load_time_ms,
            'total_size_kb': round(total_size_kb, 2),
            'num_requests': num_requests,
            'html_size_kb': round(html_size / 1024, 2),
            'resources': resource_details[:10]  # Primeros 10 recursos
        }

    except requests.Timeout:
        raise PerformanceError(f"Timeout al analizar {url}")
    except requests.RequestException as e:
        raise PerformanceError(f"Error de request: {e}")
    except Exception as e:
        raise PerformanceError(f"Error inesperado: {e}")


def _extract_resources(soup: BeautifulSoup, base_url: str) -> List[Tuple[str, str]]:
    """
    Extrae URLs de recursos de un HTML.

    Args:
        soup: BeautifulSoup object
        base_url: URL base para resolver URLs relativas

    Returns:
        Lista de tuplas (url, tipo)
    """
    resources = []

    # CSS
    for link in soup.find_all('link', rel='stylesheet'):
        href = link.get('href')
        if href:
            resources.append((urljoin(base_url, href), 'css'))

    # JavaScript
    for script in soup.find_all('script', src=True):
        src = script.get('src')
        if src:
            resources.append((urljoin(base_url, src), 'js'))

    # Imágenes
    for img in soup.find_all('img', src=True):
        src = img.get('src')
        if src:
            resources.append((urljoin(base_url, src), 'image'))

    logger.debug(f"Encontrados {len(resources)} recursos")
    return resources


def calculate_performance_score(metrics: Dict) -> int:
    """
    Calcula un score de rendimiento basado en las métricas.

    Args:
        metrics: Diccionario con métricas de rendimiento

    Returns:
        Score de 0 a 100
    """
    score = 100

    # Penalizar por tiempo de carga
    load_time = metrics.get('load_time_ms', 0)
    if load_time > 3000:
        score -= 30
    elif load_time > 1500:
        score -= 15
    elif load_time > 1000:
        score -= 5

    # Penalizar por tamaño total
    total_size = metrics.get('total_size_kb', 0)
    if total_size > 5000:
        score -= 20
    elif total_size > 2000:
        score -= 10
    elif total_size > 1000:
        score -= 5

    # Penalizar por número de requests
    num_requests = metrics.get('num_requests', 0)
    if num_requests > 100:
        score -= 20
    elif num_requests > 50:
        score -= 10
    elif num_requests > 30:
        score -= 5

    return max(0, score)


def analyze_performance_simple(url: str, html: str) -> Dict:
    """
    Análisis de rendimiento simplificado (sin hacer requests adicionales).

    Args:
        url: URL de la página
        html: Contenido HTML

    Returns:
        Diccionario con métricas básicas
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        resources = _extract_resources(soup, url)

        html_size_kb = len(html.encode('utf-8')) / 1024

        # Estimaciones
        estimated_size_kb = html_size_kb

        # Estimar tamaño de recursos
        num_css = sum(1 for _, t in resources if t == 'css')
        num_js = sum(1 for _, t in resources if t == 'js')
        num_images = sum(1 for _, t in resources if t == 'image')

        # Estimaciones aproximadas
        estimated_size_kb += num_css * 50  # ~50 KB por CSS
        estimated_size_kb += num_js * 100  # ~100 KB por JS
        estimated_size_kb += num_images * 150  # ~150 KB por imagen

        return {
            'success': True,
            'html_size_kb': round(html_size_kb, 2),
            'estimated_total_size_kb': round(estimated_size_kb, 2),
            'estimated_num_requests': 1 + len(resources),
            'resources_breakdown': {
                'css': num_css,
                'js': num_js,
                'images': num_images,
                'total': len(resources)
            }
        }

    except Exception as e:
        logger.error(f"Error en análisis simple: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Función principal que se ejecutará en un proceso separado
def process_performance(url: str, html: str = None) -> Dict:
    """
    Función principal para análisis de rendimiento.

    Esta función está diseñada para ejecutarse en un proceso separado
    del pool de multiprocessing.

    Args:
        url: URL de la página a analizar
        html: HTML ya descargado (opcional, si no se provee se descarga)

    Returns:
        Diccionario con métricas de rendimiento
    """
    try:
        if html:
            # Usar análisis simple si ya tenemos el HTML
            result = analyze_performance_simple(url, html)
        else:
            # Hacer análisis completo
            result = analyze_page_performance(url, timeout=30)

        # Calcular score si el análisis fue exitoso
        if result.get('success'):
            if 'load_time_ms' in result:
                result['performance_score'] = calculate_performance_score(result)

        return result

    except Exception as e:
        logger.error(f"Error al procesar rendimiento de {url}: {e}")
        return {
            'success': False,
            'error': str(e)
        }
