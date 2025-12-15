"""
Filtros de desenfoque usando OpenCV.
"""

import cv2
import numpy as np
from typing import Dict, Any


def gaussian_blur(frame: np.ndarray, kernel_size: int = 5, sigma: float = 0) -> np.ndarray:
    """
    Aplica Gaussian blur al frame.

    Args:
        frame: Frame de entrada (numpy array)
        kernel_size: Tamaño del kernel (debe ser impar)
        sigma: Desviación estándar (0 = auto)

    Returns:
        Frame con blur aplicado
    """
    # Asegurar que kernel_size es impar
    if kernel_size % 2 == 0:
        kernel_size += 1

    return cv2.GaussianBlur(frame, (kernel_size, kernel_size), sigma)


def median_blur(frame: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """
    Aplica median blur al frame (bueno para ruido salt-and-pepper).

    Args:
        frame: Frame de entrada
        kernel_size: Tamaño del kernel (debe ser impar)

    Returns:
        Frame con median blur
    """
    # Asegurar que kernel_size es impar
    if kernel_size % 2 == 0:
        kernel_size += 1

    return cv2.medianBlur(frame, kernel_size)


def bilateral_filter(
    frame: np.ndarray,
    d: int = 9,
    sigma_color: float = 75,
    sigma_space: float = 75
) -> np.ndarray:
    """
    Aplica bilateral filter (preserva bordes mientras desenfoca).

    Args:
        frame: Frame de entrada
        d: Diámetro del vecindario
        sigma_color: Filtro sigma en el espacio de color
        sigma_space: Filtro sigma en el espacio de coordenadas

    Returns:
        Frame con bilateral filter
    """
    return cv2.bilateralFilter(frame, d, sigma_color, sigma_space)


def apply_blur(
    frame: np.ndarray,
    blur_type: str = "gaussian",
    **kwargs
) -> np.ndarray:
    """
    Aplica el tipo de blur especificado.

    Args:
        frame: Frame de entrada
        blur_type: Tipo de blur ("gaussian", "median", "bilateral")
        **kwargs: Parámetros adicionales según el tipo (kernel, sigma, etc.)

    Returns:
        Frame con blur aplicado
    """
    if blur_type == "gaussian":
        kernel = kwargs.get("kernel", 5)
        sigma = kwargs.get("sigma", 0)
        return gaussian_blur(frame, kernel, sigma)

    elif blur_type == "median":
        kernel = kwargs.get("kernel", 5)
        return median_blur(frame, kernel)

    elif blur_type == "bilateral":
        d = kwargs.get("d", 9)
        sigma_color = kwargs.get("sigma_color", 75)
        sigma_space = kwargs.get("sigma_space", 75)
        return bilateral_filter(frame, d, sigma_color, sigma_space)

    else:
        raise ValueError(f"Tipo de blur desconocido: {blur_type}")
