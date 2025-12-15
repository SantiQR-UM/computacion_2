"""
Filtros de detección de bordes usando OpenCV.
"""

import cv2
import numpy as np
from typing import Dict, Any


def canny_edges(
    frame: np.ndarray,
    threshold1: int = 50,
    threshold2: int = 150,
    aperture_size: int = 3
) -> np.ndarray:
    """
    Aplica Canny edge detection.

    Args:
        frame: Frame de entrada
        threshold1: Primer threshold para histéresis
        threshold2: Segundo threshold para histéresis
        aperture_size: Tamaño de apertura para Sobel

    Returns:
        Frame con bordes detectados (imagen binaria)
    """
    # Convertir a escala de grises si es color
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    edges = cv2.Canny(gray, threshold1, threshold2, apertureSize=aperture_size)

    # Convertir de vuelta a BGR para mantener consistencia
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


def sobel_edges(frame: np.ndarray, ksize: int = 3) -> np.ndarray:
    """
    Aplica Sobel edge detection (gradiente).

    Args:
        frame: Frame de entrada
        ksize: Tamaño del kernel Sobel

    Returns:
        Frame con bordes detectados
    """
    # Convertir a escala de grises
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    # Calcular gradientes en X e Y
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)

    # Magnitud del gradiente
    abs_grad_x = cv2.convertScaleAbs(grad_x)
    abs_grad_y = cv2.convertScaleAbs(grad_y)
    grad = cv2.addWeighted(abs_grad_x, 0.5, abs_grad_y, 0.5, 0)

    # Convertir a BGR
    return cv2.cvtColor(grad, cv2.COLOR_GRAY2BGR)


def laplacian_edges(frame: np.ndarray, ksize: int = 3) -> np.ndarray:
    """
    Aplica Laplacian edge detection.

    Args:
        frame: Frame de entrada
        ksize: Tamaño del kernel

    Returns:
        Frame con bordes detectados
    """
    # Convertir a escala de grises
    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    # Aplicar Laplacian
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
    laplacian = cv2.convertScaleAbs(laplacian)

    # Convertir a BGR
    return cv2.cvtColor(laplacian, cv2.COLOR_GRAY2BGR)


def apply_edge_detection(
    frame: np.ndarray,
    edge_type: str = "canny",
    params: Dict[str, Any] = None
) -> np.ndarray:
    """
    Aplica el tipo de detección de bordes especificado.

    Args:
        frame: Frame de entrada
        edge_type: Tipo de detección ("canny", "sobel", "laplacian")
        params: Parámetros adicionales según el tipo

    Returns:
        Frame con bordes detectados
    """
    params = params or {}

    if edge_type == "canny":
        t1 = params.get("threshold1", 50)
        t2 = params.get("threshold2", 150)
        aperture = params.get("aperture_size", 3)
        return canny_edges(frame, t1, t2, aperture)

    elif edge_type == "sobel":
        ksize = params.get("ksize", 3)
        return sobel_edges(frame, ksize)

    elif edge_type == "laplacian":
        ksize = params.get("ksize", 3)
        return laplacian_edges(frame, ksize)

    else:
        raise ValueError(f"Tipo de edge detection desconocido: {edge_type}")
