"""
Módulo para escribir videos procesados usando OpenCV.
"""

import cv2
import numpy as np
import threading
from typing import Optional, Tuple
from pathlib import Path


class VideoWriter:
    """Escritor de video thread-safe usando OpenCV."""

    def __init__(
        self,
        output_path: str,
        fourcc: str = 'mp4v',
        fps: float = 30.0,
        frame_size: Optional[Tuple[int, int]] = None
    ):
        """
        Inicializa el escritor de video.

        Args:
            output_path: Ruta del archivo de salida
            fourcc: Código de codec (ej: 'mp4v', 'H264', 'XVID')
            fps: Frames por segundo
            frame_size: Tamaño del frame (width, height), None para auto-detectar
        """
        self.output_path = output_path
        self.fourcc_str = fourcc
        self.fps = fps
        self.frame_size = frame_size
        self.writer: Optional[cv2.VideoWriter] = None
        self.lock = threading.RLock()
        self.is_open = False
        self.frame_count = 0

    def open(self, first_frame: np.ndarray = None) -> bool:
        """
        Abre el escritor de video.

        Args:
            first_frame: Primer frame para detectar tamaño si no se especificó

        Returns:
            True si se abrió correctamente
        """
        with self.lock:
            if self.is_open:
                return True

            # Determinar tamaño de frame
            if self.frame_size is None:
                if first_frame is None:
                    raise ValueError("Se necesita frame_size o first_frame para abrir el writer")
                height, width = first_frame.shape[:2]
                self.frame_size = (width, height)

            # Crear directorio si no existe
            Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)

            # Configurar codec
            fourcc = cv2.VideoWriter_fourcc(*self.fourcc_str)

            # Crear writer
            self.writer = cv2.VideoWriter(
                self.output_path,
                fourcc,
                self.fps,
                self.frame_size
            )

            if not self.writer.isOpened():
                return False

            self.is_open = True
            return True

    def write(self, frame: np.ndarray) -> bool:
        """
        Escribe un frame al video.

        Args:
            frame: Frame a escribir (numpy array)

        Returns:
            True si se escribió correctamente
        """
        with self.lock:
            if not self.is_open:
                # Auto-abrir con el primer frame
                if not self.open(frame):
                    return False

            # Validar tamaño del frame
            height, width = frame.shape[:2]
            if (width, height) != self.frame_size:
                # Resize si es necesario
                frame = cv2.resize(frame, self.frame_size)

            try:
                self.writer.write(frame)
                self.frame_count += 1
                return True
            except Exception as e:
                print(f"Error escribiendo frame: {e}")
                return False

    def close(self) -> None:
        """Cierra el escritor de video."""
        with self.lock:
            if self.is_open and self.writer is not None:
                self.writer.release()
                self.is_open = False
                print(f"Video guardado: {self.output_path} ({self.frame_count} frames)")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class VideoFrameBuffer:
    """Buffer para frames desordenados que necesitan ser escritos en orden."""

    def __init__(self, writer: VideoWriter):
        """
        Inicializa el buffer.

        Args:
            writer: VideoWriter donde escribir los frames
        """
        self.writer = writer
        self.buffer: dict = {}
        self.next_frame_number = 0
        self.lock = threading.Lock()

    def add_frame(self, frame_number: int, frame: np.ndarray) -> int:
        """
        Añade un frame al buffer y escribe frames consecutivos.

        Args:
            frame_number: Número de secuencia del frame
            frame: Frame a añadir

        Returns:
            Cantidad de frames escritos
        """
        with self.lock:
            # Añadir al buffer
            self.buffer[frame_number] = frame

            # Escribir frames consecutivos
            written = 0
            while self.next_frame_number in self.buffer:
                frame_to_write = self.buffer.pop(self.next_frame_number)
                self.writer.write(frame_to_write)
                self.next_frame_number += 1
                written += 1

            return written

    def flush_remaining(self, total_frames: int) -> int:
        """
        Escribe frames restantes, rellenando con negro si faltan.

        Args:
            total_frames: Total de frames esperados

        Returns:
            Cantidad de frames escritos
        """
        with self.lock:
            written = 0
            while self.next_frame_number < total_frames:
                if self.next_frame_number in self.buffer:
                    frame = self.buffer.pop(self.next_frame_number)
                else:
                    # Crear frame negro si falta
                    print(f"Advertencia: falta frame {self.next_frame_number}, usando negro")
                    frame = np.zeros(
                        (self.writer.frame_size[1], self.writer.frame_size[0], 3),
                        dtype=np.uint8
                    )

                self.writer.write(frame)
                self.next_frame_number += 1
                written += 1

            return written

    def get_pending_count(self) -> int:
        """Retorna cantidad de frames en buffer pendientes."""
        with self.lock:
            return len(self.buffer)
