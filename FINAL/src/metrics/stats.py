"""
Módulo para recolección y cálculo de métricas.
"""

import time
import threading
from typing import List, Dict, Any
from collections import defaultdict
import statistics


class MetricsCollector:
    """Recolector de métricas para procesamiento de video."""

    def __init__(self):
        """Inicializa el recolector de métricas."""
        self.lock = threading.Lock()
        self.start_time = time.time()

        # Contadores
        self.frames_processed = 0
        self.frames_total = 0
        self.frames_failed = 0
        self.retries_count = 0

        # Latencias (ms)
        self.latencies: List[float] = []

        # Estadísticas por worker
        self.worker_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "frames_processed": 0,
                "total_time_ms": 0,
                "total_memory_mb": 0
            }
        )

        # Filtros aplicados
        self.filters_count: Dict[str, int] = defaultdict(int)

    def record_frame(
        self,
        frame_number: int,
        processing_time_ms: float,
        worker_id: str = None,
        filter_applied: str = None,
        memory_mb: float = 0,
        failed: bool = False
    ) -> None:
        """
        Registra procesamiento de un frame.

        Args:
            frame_number: Número del frame
            processing_time_ms: Tiempo de procesamiento en ms
            worker_id: ID del worker que procesó
            filter_applied: Nombre del filtro aplicado
            memory_mb: Memoria usada en MB
            failed: Si el procesamiento falló
        """
        with self.lock:
            self.frames_processed += 1

            if failed:
                self.frames_failed += 1
            else:
                self.latencies.append(processing_time_ms)

            if worker_id:
                self.worker_stats[worker_id]["frames_processed"] += 1
                self.worker_stats[worker_id]["total_time_ms"] += processing_time_ms
                self.worker_stats[worker_id]["total_memory_mb"] += memory_mb

            if filter_applied:
                self.filters_count[filter_applied] += 1

    def record_retry(self) -> None:
        """Registra un reintento."""
        with self.lock:
            self.retries_count += 1

    def set_total_frames(self, total: int) -> None:
        """Establece el total de frames a procesar."""
        with self.lock:
            self.frames_total = total

    def get_percentile(self, percentile: float) -> float:
        """
        Calcula un percentil de las latencias.

        Args:
            percentile: Percentil a calcular (0-100)

        Returns:
            Valor del percentil en ms
        """
        with self.lock:
            if not self.latencies:
                return 0.0

            sorted_latencies = sorted(self.latencies)
            k = (len(sorted_latencies) - 1) * percentile / 100
            f = int(k)
            c = f + 1

            if c >= len(sorted_latencies):
                return sorted_latencies[-1]

            d0 = sorted_latencies[f] * (c - k)
            d1 = sorted_latencies[c] * (k - f)
            return d0 + d1

    def get_fps_processing(self) -> float:
        """Calcula FPS de procesamiento actual."""
        with self.lock:
            elapsed = time.time() - self.start_time
            if elapsed == 0:
                return 0.0
            return self.frames_processed / elapsed

    def get_eta_seconds(self) -> float:
        """Calcula tiempo estimado restante en segundos."""
        with self.lock:
            if self.frames_processed == 0 or self.frames_total == 0:
                return 0.0

            elapsed = time.time() - self.start_time
            frames_remaining = self.frames_total - self.frames_processed
            fps = self.frames_processed / elapsed

            if fps == 0:
                return 0.0

            return frames_remaining / fps

    def get_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen completo de métricas.

        Returns:
            Diccionario con todas las métricas
        """
        # NO USAR LOCK - causa deadlock en contexto async/threading mezclado
        # La lectura de primitivos es thread-safe en Python (GIL)
        elapsed = time.time() - self.start_time

        return {
            "total_frames": self.frames_total,
            "frames_processed": self.frames_processed,
            "frames_failed": self.frames_failed,
            "retries": self.retries_count,
            "processing_time_seconds": elapsed,
            "fps_processing": self.get_fps_processing(),
            "latency_p50_ms": self.get_percentile(50),
            "latency_p95_ms": self.get_percentile(95),
            "latency_p99_ms": self.get_percentile(99),
            "latency_avg_ms": statistics.mean(self.latencies) if self.latencies else 0,
            "latency_min_ms": min(self.latencies) if self.latencies else 0,
            "latency_max_ms": max(self.latencies) if self.latencies else 0,
            "worker_count": len(self.worker_stats),
            "filters_applied": dict(self.filters_count)
        }

    def get_progress(self) -> Dict[str, Any]:
        """
        Obtiene progreso actual (para enviar al cliente).

        Returns:
            Diccionario con progreso
        """
        with self.lock:
            return {
                "frames_processed": self.frames_processed,
                "frames_total": self.frames_total,
                "fps": self.get_fps_processing(),
                "eta_seconds": self.get_eta_seconds(),
                "latency_p95_ms": self.get_percentile(95),
                "retries": self.retries_count
            }

    def reset(self) -> None:
        """Resetea todas las métricas."""
        with self.lock:
            self.start_time = time.time()
            self.frames_processed = 0
            self.frames_total = 0
            self.frames_failed = 0
            self.retries_count = 0
            self.latencies.clear()
            self.worker_stats.clear()
            self.filters_count.clear()
