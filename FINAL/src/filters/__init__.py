"""
Modulo de filtros de procesamiento de video.
"""

from .blur import apply_blur
from .edges import apply_edge_detection
from .faces import FaceDetector, detect_and_draw_faces
from .motion import MotionDetector, detect_motion, reset_motion_detector

__all__ = [
    'apply_blur',
    'apply_edge_detection',
    'FaceDetector',
    'detect_and_draw_faces',
    'MotionDetector',
    'detect_motion',
    'reset_motion_detector',
]