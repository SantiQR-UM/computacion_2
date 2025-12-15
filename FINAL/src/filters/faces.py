"""
Filtro de detección de rostros usando Haar cascades de OpenCV.
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Any
import os


# Ruta por defecto del cascade (OpenCV incluye estos XML)
DEFAULT_FACE_CASCADE = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
DEFAULT_EYE_CASCADE = cv2.data.haarcascades + 'haarcascade_eye.xml'


class FaceDetector:
    """Detector de rostros con Haar cascades."""

    def __init__(self, face_cascade_path: str = None, eye_cascade_path: str = None):
        """
        Inicializa el detector de rostros.

        Args:
            face_cascade_path: Ruta al XML de Haar cascade para rostros
            eye_cascade_path: Ruta al XML de Haar cascade para ojos (opcional)
        """
        face_path = face_cascade_path or DEFAULT_FACE_CASCADE
        self.face_cascade = cv2.CascadeClassifier(face_path)

        if eye_cascade_path:
            self.eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
        else:
            self.eye_cascade = None

        if self.face_cascade.empty():
            raise ValueError(f"No se pudo cargar face cascade desde {face_path}")

    def detect_faces(
        self,
        frame: np.ndarray,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: Tuple[int, int] = (30, 30)
    ) -> list:
        """
        Detecta rostros en el frame.

        Args:
            frame: Frame de entrada
            scale_factor: Factor de escala para multi-scale detection
            min_neighbors: Mínimo de vecinos para aceptar detección
            min_size: Tamaño mínimo del rostro

        Returns:
            Lista de rectángulos (x, y, w, h) con rostros detectados
        """
        # Convertir a escala de grises
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # Detectar rostros
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=min_size
        )

        return faces

    def draw_faces(
        self,
        frame: np.ndarray,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
        detect_eyes: bool = False
    ) -> np.ndarray:
        """
        Detecta y dibuja rectángulos alrededor de los rostros.

        Args:
            frame: Frame de entrada
            color: Color del rectángulo (BGR)
            thickness: Grosor de la línea
            detect_eyes: Si True, también detecta y dibuja ojos

        Returns:
            Frame con rostros dibujados
        """
        result = frame.copy()
        faces = self.detect_faces(frame)

        # Convertir a escala de grises para detección de ojos
        if detect_eyes and len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = None

        for (x, y, w, h) in faces:
            # Dibujar rectángulo alrededor del rostro
            cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)

            # Opcionalmente, detectar ojos dentro del rostro
            if detect_eyes and self.eye_cascade and gray is not None:
                roi_gray = gray[y:y + h, x:x + w]
                eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 5)
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(
                        result,
                        (x + ex, y + ey),
                        (x + ex + ew, y + ey + eh),
                        (255, 0, 0),  # Azul para ojos
                        thickness
                    )

        return result

    def blur_faces(
        self,
        frame: np.ndarray,
        blur_factor: int = 50
    ) -> np.ndarray:
        """
        Detecta rostros y los desenfoca (para privacidad).

        Args:
            frame: Frame de entrada
            blur_factor: Factor de desenfoque (mayor = más borroso)

        Returns:
            Frame con rostros desenfoados
        """
        result = frame.copy()
        faces = self.detect_faces(frame)

        for (x, y, w, h) in faces:
            # Extraer ROI del rostro
            face_roi = result[y:y + h, x:x + w]

            # Aplicar blur fuerte
            blurred_face = cv2.GaussianBlur(face_roi, (blur_factor | 1, blur_factor | 1), 0)

            # Reemplazar en el frame
            result[y:y + h, x:x + w] = blurred_face

        return result


def detect_and_draw_faces(
    frame: np.ndarray,
    detector: "FaceDetector",
    params: Dict[str, Any] = None
) -> np.ndarray:
    """
    Función de conveniencia para detectar y dibujar rostros.

    Args:
        frame: Frame de entrada
        detector: Instancia de FaceDetector a utilizar
        params: Parámetros (color, thickness, blur_instead, etc.)

    Returns:
        Frame con rostros marcados o desenfoados
    """
    params = params or {}
    blur_instead = params.get("blur_instead", False)

    if blur_instead:
        blur_factor = params.get("blur_factor", 50)
        return detector.blur_faces(frame, blur_factor)
    else:
        color = params.get("color", (0, 255, 0))
        thickness = params.get("thickness", 2)
        detect_eyes = params.get("detect_eyes", False)
        return detector.draw_faces(frame, color, thickness, detect_eyes)
