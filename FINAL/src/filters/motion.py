"""
Filtros de detección de movimiento usando OpenCV.
"""

import cv2
import numpy as np
from typing import Optional, Dict, Any


class MotionDetector:
    """Detector de movimiento entre frames consecutivos."""

    def __init__(self):
        """Inicializa el detector de movimiento."""
        self.prev_frame = None
        self.prev_gray = None

    def reset(self):
        """Resetea el estado del detector."""
        self.prev_frame = None
        self.prev_gray = None

    def detect_motion_diff(
        self,
        frame: np.ndarray,
        threshold: int = 25
    ) -> np.ndarray:
        """
        Detecta movimiento usando diferencia de frames.

        Args:
            frame: Frame actual
            threshold: Umbral para considerar cambio significativo

        Returns:
            Frame con áreas de movimiento resaltadas
        """
        # Convertir a escala de grises
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # Aplicar blur para reducir ruido
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Si no hay frame previo, guardar y retornar original
        if self.prev_gray is None:
            self.prev_gray = gray
            self.prev_frame = frame.copy()
            return frame

        # Calcular diferencia absoluta
        frame_delta = cv2.absdiff(self.prev_gray, gray)

        # Aplicar threshold
        thresh = cv2.threshold(frame_delta, threshold, 255, cv2.THRESH_BINARY)[1]

        # Dilatar para rellenar huecos
        thresh = cv2.dilate(thresh, None, iterations=2)

        # Encontrar contornos
        contours, _ = cv2.findContours(
            thresh.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Dibujar contornos en el frame original
        result = frame.copy()
        for contour in contours:
            # Ignorar contornos pequeños
            if cv2.contourArea(contour) < 500:
                continue

            # Dibujar rectángulo alrededor del área de movimiento
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Actualizar frame previo
        self.prev_gray = gray
        self.prev_frame = frame.copy()

        return result

    def detect_motion_optical_flow(
        self,
        frame: np.ndarray,
        draw_arrows: bool = True
    ) -> np.ndarray:
        """
        Detecta movimiento usando optical flow (Farneback).

        Args:
            frame: Frame actual
            draw_arrows: Si True, dibuja vectores de flujo

        Returns:
            Frame con flujo óptico visualizado
        """
        # Convertir a escala de grises
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # Si no hay frame previo, guardar y retornar original
        if self.prev_gray is None:
            self.prev_gray = gray
            return frame

        # Calcular optical flow
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray,
            gray,
            None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )

        # Visualizar flujo
        if draw_arrows:
            result = frame.copy()
            step = 16
            h, w = gray.shape
            for y in range(0, h, step):
                for x in range(0, w, step):
                    fx, fy = flow[y, x]
                    # Solo dibujar si hay movimiento significativo
                    if abs(fx) > 1 or abs(fy) > 1:
                        cv2.arrowedLine(
                            result,
                            (x, y),
                            (int(x + fx), int(y + fy)),
                            (0, 255, 0),
                            1,
                            tipLength=0.3
                        )
        else:
            # Convertir flujo a representación HSV
            mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            hsv = np.zeros((gray.shape[0], gray.shape[1], 3), dtype=np.uint8)
            hsv[..., 0] = ang * 180 / np.pi / 2
            hsv[..., 1] = 255
            hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
            result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        # Actualizar frame previo
        self.prev_gray = gray

        return result


def detect_motion(
    frame: np.ndarray,
    detector: "MotionDetector",
    motion_type: str = "diff",
    params: Dict[str, Any] = None
) -> np.ndarray:
    """
    Aplica detección de movimiento.

    Args:
        frame: Frame de entrada
        detector: Instancia de MotionDetector a utilizar
        motion_type: Tipo de detección ("diff", "optical_flow")
        params: Parámetros adicionales

    Returns:
        Frame con movimiento detectado
    """
    params = params or {}

    if motion_type == "diff":
        threshold = params.get("threshold", 25)
        return detector.detect_motion_diff(frame, threshold)

    elif motion_type == "optical_flow":
        draw_arrows = params.get("draw_arrows", True)
        return detector.detect_motion_optical_flow(frame, draw_arrows)

    else:
        raise ValueError(f"Tipo de motion detection desconocido: {motion_type}")


def reset_motion_detector(detector: "MotionDetector"):
    """Resetea el detector de movimiento."""
    detector.reset()
