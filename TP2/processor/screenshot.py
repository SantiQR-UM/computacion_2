"""
Generación de screenshots.

Este módulo proporciona funcionalidades para capturar screenshots
de páginas web usando Selenium WebDriver.
"""

import logging
import base64
from typing import Optional
from io import BytesIO

logger = logging.getLogger(__name__)


class ScreenshotError(Exception):
    """Excepción para errores de screenshot."""
    pass


def capture_screenshot_selenium(url: str, timeout: int = 30) -> bytes:
    """
    Captura un screenshot de una URL usando Selenium.

    Args:
        url: URL de la página a capturar
        timeout: Timeout en segundos

    Returns:
        Bytes de la imagen PNG

    Raises:
        ScreenshotError: Si hay un error al capturar el screenshot
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.common.exceptions import WebDriverException, TimeoutException

        # Configurar Chrome en modo headless
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--log-level=3')

        logger.debug(f"Iniciando Chrome para capturar {url}")

        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(timeout)

            logger.debug(f"Cargando URL: {url}")
            driver.get(url)

            # Esperar a que la página cargue
            import time
            time.sleep(2)

            # Capturar screenshot
            screenshot_png = driver.get_screenshot_as_png()

            logger.info(f"Screenshot capturado: {len(screenshot_png)} bytes")
            return screenshot_png

        finally:
            if driver:
                driver.quit()
                logger.debug("Chrome cerrado")

    except ImportError:
        raise ScreenshotError("Selenium no está instalado. Instalar con: pip install selenium")
    except TimeoutException:
        raise ScreenshotError(f"Timeout al cargar la página: {url}")
    except WebDriverException as e:
        raise ScreenshotError(f"Error de WebDriver: {e}")
    except Exception as e:
        raise ScreenshotError(f"Error inesperado al capturar screenshot: {e}")


def capture_screenshot_playwright(url: str, timeout: int = 30000) -> bytes:
    """
    Captura un screenshot de una URL usando Playwright (alternativa a Selenium).

    Args:
        url: URL de la página a capturar
        timeout: Timeout en milisegundos

    Returns:
        Bytes de la imagen PNG

    Raises:
        ScreenshotError: Si hay un error al capturar el screenshot
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

        logger.debug(f"Iniciando Playwright para capturar {url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={'width': 1920, 'height': 1080})
                page.set_default_timeout(timeout)

                logger.debug(f"Cargando URL: {url}")
                page.goto(url, wait_until='networkidle')

                # Capturar screenshot
                screenshot_bytes = page.screenshot(type='png', full_page=False)

                logger.info(f"Screenshot capturado (Playwright): {len(screenshot_bytes)} bytes")
                return screenshot_bytes

            finally:
                browser.close()
                logger.debug("Playwright cerrado")

    except ImportError:
        raise ScreenshotError("Playwright no está instalado. Instalar con: pip install playwright && playwright install")
    except PlaywrightTimeout:
        raise ScreenshotError(f"Timeout al cargar la página: {url}")
    except Exception as e:
        raise ScreenshotError(f"Error inesperado al capturar screenshot (Playwright): {e}")


def capture_screenshot(url: str, timeout: int = 30, use_playwright: bool = False) -> bytes:
    """
    Captura un screenshot de una URL.

    Intenta usar el método especificado, o hace fallback al alternativo.

    Args:
        url: URL de la página a capturar
        timeout: Timeout en segundos
        use_playwright: Si es True, usa Playwright; sino usa Selenium

    Returns:
        Bytes de la imagen PNG

    Raises:
        ScreenshotError: Si no puede capturar el screenshot con ningún método
    """
    if use_playwright:
        try:
            return capture_screenshot_playwright(url, timeout * 1000)
        except ScreenshotError as e:
            logger.warning(f"Playwright falló: {e}, intentando con Selenium")
            return capture_screenshot_selenium(url, timeout)
    else:
        try:
            return capture_screenshot_selenium(url, timeout)
        except ScreenshotError as e:
            logger.warning(f"Selenium falló: {e}, intentando con Playwright")
            return capture_screenshot_playwright(url, timeout * 1000)


def screenshot_to_base64(screenshot_bytes: bytes) -> str:
    """
    Convierte bytes de screenshot a string base64.

    Args:
        screenshot_bytes: Bytes de la imagen PNG

    Returns:
        String base64 de la imagen
    """
    return base64.b64encode(screenshot_bytes).decode('ascii')


def resize_screenshot(screenshot_bytes: bytes, max_width: int = 1280, max_height: int = 720) -> bytes:
    """
    Redimensiona un screenshot para reducir su tamaño.

    Args:
        screenshot_bytes: Bytes de la imagen PNG original
        max_width: Ancho máximo
        max_height: Alto máximo

    Returns:
        Bytes de la imagen redimensionada

    Raises:
        ScreenshotError: Si hay un error al redimensionar
    """
    try:
        from PIL import Image

        # Cargar imagen
        img = Image.open(BytesIO(screenshot_bytes))

        # Calcular nuevo tamaño manteniendo aspect ratio
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Guardar a bytes
        output = BytesIO()
        img.save(output, format='PNG', optimize=True)
        resized_bytes = output.getvalue()

        logger.debug(f"Screenshot redimensionado: {len(screenshot_bytes)} -> {len(resized_bytes)} bytes")
        return resized_bytes

    except ImportError:
        raise ScreenshotError("Pillow no está instalado. Instalar con: pip install Pillow")
    except Exception as e:
        raise ScreenshotError(f"Error al redimensionar screenshot: {e}")


# Función principal que se ejecutará en un proceso separado
def process_screenshot(url: str, max_width: int = 1280, max_height: int = 720) -> dict:
    """
    Función principal para capturar y procesar screenshot.

    Esta función está diseñada para ejecutarse en un proceso separado
    del pool de multiprocessing.

    Args:
        url: URL de la página a capturar
        max_width: Ancho máximo del screenshot
        max_height: Alto máximo del screenshot

    Returns:
        Diccionario con el screenshot en base64 y metadata
    """
    try:
        # Capturar screenshot
        screenshot_bytes = capture_screenshot(url, timeout=30)

        # Redimensionar para reducir tamaño
        if max_width or max_height:
            screenshot_bytes = resize_screenshot(screenshot_bytes, max_width, max_height)

        # Convertir a base64
        screenshot_b64 = screenshot_to_base64(screenshot_bytes)

        return {
            'success': True,
            'screenshot': screenshot_b64,
            'size_bytes': len(screenshot_bytes)
        }

    except Exception as e:
        logger.error(f"Error al procesar screenshot de {url}: {e}")
        return {
            'success': False,
            'error': str(e)
        }
