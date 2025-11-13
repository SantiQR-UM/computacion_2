"""
Cliente HTTP asíncrono.

Este módulo proporciona funcionalidades para realizar requests HTTP
de forma asíncrona usando aiohttp.
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuración por defecto
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


class HTTPError(Exception):
    """Excepción para errores HTTP."""
    pass


class AsyncHTTPClient:
    """
    Cliente HTTP asíncrono basado en aiohttp.

    Maneja requests HTTP de forma asíncrona con soporte para timeouts,
    headers personalizados, y manejo de errores.
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_redirects: int = 10,
        user_agent: Optional[str] = None
    ):
        """
        Inicializa el cliente HTTP asíncrono.

        Args:
            timeout: Timeout por defecto en segundos
            max_redirects: Número máximo de redirects a seguir
            user_agent: User-Agent a usar (None para el default)
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_redirects = max_redirects
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Inicia la sesión HTTP."""
        if self.session is None:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent}
            )
            logger.info("Sesión HTTP iniciada")

    async def close(self) -> None:
        """Cierra la sesión HTTP."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Sesión HTTP cerrada")

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Tuple[str, int, Dict[str, str]]:
        """
        Realiza un GET HTTP asíncrono.

        Args:
            url: URL a solicitar
            headers: Headers adicionales (opcional)
            timeout: Timeout específico para este request (opcional)

        Returns:
            Tupla (contenido_html, status_code, headers_response)

        Raises:
            HTTPError: Si hay un error en el request
        """
        if not self.session:
            raise HTTPError("Sesión HTTP no iniciada. Usar como context manager o llamar start()")

        try:
            custom_timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None

            logger.debug(f"GET {url}")
            start_time = datetime.now()

            async with self.session.get(
                url,
                headers=headers,
                timeout=custom_timeout,
                max_redirects=self.max_redirects,
                allow_redirects=True
            ) as response:
                content = await response.text()
                elapsed = (datetime.now() - start_time).total_seconds()

                logger.info(f"GET {url} - Status: {response.status} - Time: {elapsed:.2f}s - Size: {len(content)} bytes")

                return content, response.status, dict(response.headers)

        except asyncio.TimeoutError:
            raise HTTPError(f"Timeout al solicitar {url}")
        except aiohttp.ClientError as e:
            raise HTTPError(f"Error HTTP al solicitar {url}: {e}")
        except Exception as e:
            raise HTTPError(f"Error inesperado al solicitar {url}: {e}")

    async def get_binary(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Tuple[bytes, int, Dict[str, str]]:
        """
        Realiza un GET HTTP asíncrono y retorna contenido binario.

        Args:
            url: URL a solicitar
            headers: Headers adicionales (opcional)
            timeout: Timeout específico para este request (opcional)

        Returns:
            Tupla (contenido_binario, status_code, headers_response)

        Raises:
            HTTPError: Si hay un error en el request
        """
        if not self.session:
            raise HTTPError("Sesión HTTP no iniciada")

        try:
            custom_timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None

            logger.debug(f"GET (binary) {url}")
            start_time = datetime.now()

            async with self.session.get(
                url,
                headers=headers,
                timeout=custom_timeout,
                max_redirects=self.max_redirects,
                allow_redirects=True
            ) as response:
                content = await response.read()
                elapsed = (datetime.now() - start_time).total_seconds()

                logger.info(f"GET (binary) {url} - Status: {response.status} - Time: {elapsed:.2f}s - Size: {len(content)} bytes")

                return content, response.status, dict(response.headers)

        except asyncio.TimeoutError:
            raise HTTPError(f"Timeout al solicitar {url}")
        except aiohttp.ClientError as e:
            raise HTTPError(f"Error HTTP al solicitar {url}: {e}")
        except Exception as e:
            raise HTTPError(f"Error inesperado al solicitar {url}: {e}")

    async def head(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Tuple[int, Dict[str, str]]:
        """
        Realiza un HEAD HTTP asíncrono.

        Args:
            url: URL a solicitar
            headers: Headers adicionales (opcional)
            timeout: Timeout específico para este request (opcional)

        Returns:
            Tupla (status_code, headers_response)

        Raises:
            HTTPError: Si hay un error en el request
        """
        if not self.session:
            raise HTTPError("Sesión HTTP no iniciada")

        try:
            custom_timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None

            logger.debug(f"HEAD {url}")

            async with self.session.head(
                url,
                headers=headers,
                timeout=custom_timeout,
                max_redirects=self.max_redirects,
                allow_redirects=True
            ) as response:
                logger.info(f"HEAD {url} - Status: {response.status}")
                return response.status, dict(response.headers)

        except asyncio.TimeoutError:
            raise HTTPError(f"Timeout al solicitar {url}")
        except aiohttp.ClientError as e:
            raise HTTPError(f"Error HTTP al solicitar {url}: {e}")
        except Exception as e:
            raise HTTPError(f"Error inesperado al solicitar {url}: {e}")


async def fetch_url(url: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """
    Función de conveniencia para hacer un GET HTTP simple.

    Args:
        url: URL a solicitar
        timeout: Timeout en segundos

    Returns:
        Contenido HTML de la página

    Raises:
        HTTPError: Si hay un error en el request
    """
    async with AsyncHTTPClient(timeout=timeout) as client:
        content, status, _ = await client.get(url)

        if status != 200:
            raise HTTPError(f"HTTP {status} al solicitar {url}")

        return content


async def fetch_url_with_stats(url: str, timeout: float = DEFAULT_TIMEOUT) -> Dict:
    """
    Fetch URL y retorna estadísticas de la request.

    Args:
        url: URL a solicitar
        timeout: Timeout en segundos

    Returns:
        Diccionario con contenido y estadísticas

    Raises:
        HTTPError: Si hay un error en el request
    """
    start_time = datetime.now()

    async with AsyncHTTPClient(timeout=timeout) as client:
        content, status, headers = await client.get(url)

    load_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    return {
        'content': content,
        'status': status,
        'headers': headers,
        'load_time_ms': load_time_ms,
        'size_bytes': len(content.encode('utf-8'))
    }
