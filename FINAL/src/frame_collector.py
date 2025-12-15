"""
Recolector de frames procesados usando concurrent.futures.

Implementa polling paralelo de frames con ThreadPoolExecutor,
permitiendo esperar múltiples frames simultáneamente y procesarlos
en orden a medida que están disponibles.
"""

import os
import json
import time
import asyncio
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


class FrameResult:
    """Resultado de un frame procesado."""

    def __init__(self, frame_number: int, frame_path: str, stats: Dict[str, Any]):
        self.frame_number = frame_number
        self.frame_path = frame_path
        self.stats = stats

    def load_frame(self) -> np.ndarray:
        """Carga el frame desde disco."""
        return cv2.imread(self.frame_path)


class FrameCollector:
    """
    Recolector de frames con polling paralelo usando concurrent.futures.

    Usa ThreadPoolExecutor para hacer polling de múltiples frames en paralelo,
    aprovechando que el polling es I/O-bound (espera + lectura de archivos).
    """

    def __init__(
        self,
        frames_dir: str = '/app/data/frames',
        max_workers: int = 4,
        poll_interval: float = 0.1,
        timeout: float = 300.0
    ):
        """
        Inicializa el recolector.

        Args:
            frames_dir: Directorio donde buscar frames
            max_workers: Cantidad de threads para polling paralelo
            poll_interval: Intervalo entre checks en segundos
            timeout: Timeout máximo por frame en segundos
        """
        self.frames_dir = frames_dir
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self.timeout = timeout

    def _poll_single_frame(self, frame_number: int) -> FrameResult:
        """
        Hace polling de un frame específico (blocking).

        Args:
            frame_number: Número del frame a esperar

        Returns:
            FrameResult con el frame procesado

        Raises:
            TimeoutError: Si el frame no aparece en timeout segundos
        """
        frame_path = os.path.join(self.frames_dir, f'frame_{frame_number:06d}.png')
        stats_path = os.path.join(self.frames_dir, f'frame_{frame_number:06d}.json')

        start_time = time.time()
        elapsed = 0

        while elapsed < self.timeout:
            # Check si ambos archivos existen
            if os.path.exists(frame_path) and os.path.exists(stats_path):
                # Leer stats
                try:
                    with open(stats_path, 'r') as f:
                        stats = json.load(f)

                    return FrameResult(frame_number, frame_path, stats)
                except (json.JSONDecodeError, IOError) as e:
                    # Archivo puede estar siendo escrito, reintentar
                    pass

            # Esperar antes del próximo check
            time.sleep(self.poll_interval)
            elapsed = time.time() - start_time

        raise TimeoutError(
            f"Frame {frame_number} no apareció después de {self.timeout}s"
        )

    def collect_frames_parallel(
        self,
        frame_numbers: List[int],
        callback: Optional[callable] = None
    ) -> List[FrameResult]:
        """
        Recolecta frames en paralelo usando ThreadPoolExecutor.

        Los frames se recolectan en paralelo pero se retornan en orden.

        Args:
            frame_numbers: Lista de números de frames a recolectar
            callback: Función opcional a llamar cuando cada frame está listo
                      Signature: callback(frame_result: FrameResult)

        Returns:
            Lista de FrameResult en orden

        Example:
            >>> collector = FrameCollector(max_workers=8)
            >>> results = collector.collect_frames_parallel(range(300))
            >>> for result in results:
            ...     frame = result.load_frame()
            ...     print(f"Frame {result.frame_number} listo")
        """
        results_dict: Dict[int, FrameResult] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Enviar todas las tareas de polling
            future_to_frame: Dict[Future, int] = {
                executor.submit(self._poll_single_frame, frame_num): frame_num
                for frame_num in frame_numbers
            }

            # Procesar a medida que completan (as_completed no mantiene orden)
            for future in as_completed(future_to_frame):
                frame_num = future_to_frame[future]

                try:
                    result = future.result()
                    results_dict[frame_num] = result

                    # Llamar callback si existe
                    if callback:
                        callback(result)

                except Exception as e:
                    print(f"❌ Error recolectando frame {frame_num}: {e}")
                    # Crear resultado de error
                    results_dict[frame_num] = FrameResult(
                        frame_num,
                        None,
                        {"error": str(e)}
                    )

        # Retornar en orden
        return [results_dict[num] for num in sorted(results_dict.keys())]

    async def collect_frames_async(
        self,
        frame_numbers: List[int],
        callback: Optional[callable] = None
    ) -> List[FrameResult]:
        """
        Versión async de collect_frames_parallel.

        Usa run_in_executor para no bloquear el event loop de asyncio.

        Args:
            frame_numbers: Lista de números de frames a recolectar
            callback: Función opcional llamada cuando frame está listo

        Returns:
            Lista de FrameResult en orden

        Example:
            >>> collector = FrameCollector()
            >>> results = await collector.collect_frames_async(range(300))
        """
        loop = asyncio.get_event_loop()

        # Ejecutar polling paralelo en executor (thread pool)
        results = await loop.run_in_executor(
            None,  # Usa default executor
            self.collect_frames_parallel,
            frame_numbers,
            callback
        )

        return results

    def collect_frames_streaming(
        self,
        total_frames: int,
        batch_size: int = 50
    ):
        """
        Recolecta frames en batches con polling paralelo (streaming).

        Útil para videos largos: procesa primeros N frames mientras
        espera los siguientes, reduciendo latencia inicial.

        Args:
            total_frames: Total de frames a recolectar
            batch_size: Cantidad de frames por batch

        Yields:
            FrameResult a medida que están disponibles (en orden)

        Example:
            >>> collector = FrameCollector()
            >>> for result in collector.collect_frames_streaming(300, batch_size=50):
            ...     frame = result.load_frame()
            ...     writer.write(frame)
        """
        for batch_start in range(0, total_frames, batch_size):
            batch_end = min(batch_start + batch_size, total_frames)
            frame_numbers = range(batch_start, batch_end)

            print(f"Recolectando batch: frames {batch_start}-{batch_end-1}")

            # Recolectar batch en paralelo
            results = self.collect_frames_parallel(list(frame_numbers))

            # Yield en orden
            for result in results:
                yield result


class FrameCollectorWithFutures:
    """
    Versión alternativa usando Futures explícitamente.

    Permite cancelación de futures y monitoreo de progreso individual.
    """

    def __init__(
        self,
        frames_dir: str = '/app/data/frames',
        max_workers: int = 4
    ):
        self.frames_dir = frames_dir
        self.max_workers = max_workers
        self.executor: Optional[ThreadPoolExecutor] = None
        self.futures: Dict[int, Future] = {}

    def start(self):
        """Inicia el executor."""
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

    def submit_frame(self, frame_number: int) -> Future:
        """
        Envía tarea de polling de un frame y retorna Future.

        Args:
            frame_number: Número del frame

        Returns:
            Future que se resolverá cuando frame esté listo

        Example:
            >>> collector = FrameCollectorWithFutures()
            >>> collector.start()
            >>> future = collector.submit_frame(42)
            >>> result = future.result(timeout=60)  # Espera hasta 60s
        """
        if self.executor is None:
            self.start()

        def poll_frame():
            frame_path = os.path.join(self.frames_dir, f'frame_{frame_number:06d}.png')
            stats_path = os.path.join(self.frames_dir, f'frame_{frame_number:06d}.json')

            max_wait = 300
            waited = 0
            interval = 0.1

            while waited < max_wait:
                if os.path.exists(frame_path) and os.path.exists(stats_path):
                    with open(stats_path, 'r') as f:
                        stats = json.load(f)
                    return FrameResult(frame_number, frame_path, stats)

                time.sleep(interval)
                waited += interval

            raise TimeoutError(f"Frame {frame_number} timeout")

        future = self.executor.submit(poll_frame)
        self.futures[frame_number] = future
        return future

    def submit_all_frames(self, total_frames: int) -> Dict[int, Future]:
        """
        Envía todas las tareas de polling y retorna dict de Futures.

        Args:
            total_frames: Cantidad total de frames

        Returns:
            Dict {frame_number: Future}

        Example:
            >>> collector = FrameCollectorWithFutures()
            >>> futures = collector.submit_all_frames(300)
            >>> # Esperar frame específico
            >>> result = futures[42].result()
            >>> # O procesar en orden a medida que completan
            >>> for frame_num in range(300):
            ...     result = futures[frame_num].result()
        """
        self.start()

        for frame_num in range(total_frames):
            self.submit_frame(frame_num)

        return self.futures

    def get_completed_count(self) -> int:
        """Retorna cantidad de futures completados."""
        return sum(1 for f in self.futures.values() if f.done())

    def cancel_all(self):
        """Cancela todos los futures pendientes."""
        for future in self.futures.values():
            future.cancel()

    def shutdown(self, wait: bool = True):
        """Cierra el executor."""
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.executor = None


# Ejemplo de uso
if __name__ == '__main__':
    import sys

    # Test con frames de ejemplo
    print("=== Test FrameCollector ===\n")

    # Crear directorio de prueba
    test_dir = '/tmp/test_frames'
    os.makedirs(test_dir, exist_ok=True)

    # Crear algunos frames de prueba
    print("Creando frames de prueba...")
    for i in range(10):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        frame_path = os.path.join(test_dir, f'frame_{i:06d}.png')
        cv2.imwrite(frame_path, frame)

        stats = {"processing_time_ms": 25.0, "frame_number": i}
        stats_path = os.path.join(test_dir, f'frame_{i:06d}.json')
        with open(stats_path, 'w') as f:
            json.dump(stats, f)

    print(f"Frames creados en {test_dir}\n")

    # Test 1: Polling paralelo
    print("Test 1: Polling paralelo con ThreadPoolExecutor")
    collector = FrameCollector(frames_dir=test_dir, max_workers=4)

    start = time.time()
    results = collector.collect_frames_parallel(
        range(10),
        callback=lambda r: print(f"  ✓ Frame {r.frame_number} listo")
    )
    elapsed = time.time() - start

    print(f"Recolectados {len(results)} frames en {elapsed:.2f}s\n")

    # Test 2: Con Futures explícitos
    print("Test 2: Con Futures explícitos")
    collector_futures = FrameCollectorWithFutures(frames_dir=test_dir, max_workers=4)
    futures = collector_futures.submit_all_frames(10)

    print(f"Enviadas {len(futures)} tareas")
    print("Esperando resultados...")

    for i in range(10):
        result = futures[i].result(timeout=10)
        print(f"  ✓ Frame {i}: {result.stats['processing_time_ms']}ms")

    collector_futures.shutdown()

    print("\n✅ Tests completados")
