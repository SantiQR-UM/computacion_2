"""
Script para generar un video de prueba simple para el sistema.

Genera un video corto con formas geométricas en movimiento que es útil
para probar los diferentes filtros de procesamiento.
"""

import cv2
import numpy as np
import argparse
from pathlib import Path


def generate_test_video(output_path: str, duration_seconds: int = 5, fps: int = 30, width: int = 640, height: int = 480):
    """
    Genera un video de prueba con formas geométricas en movimiento.

    Args:
        output_path: Ruta donde guardar el video
        duration_seconds: Duración del video en segundos
        fps: Frames por segundo
        width: Ancho del video
        height: Alto del video
    """
    # Crear VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = duration_seconds * fps

    print(f"Generando video de prueba: {total_frames} frames a {fps} FPS")

    for frame_num in range(total_frames):
        # Crear frame blanco
        frame = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Calcular posiciones basadas en el frame
        t = frame_num / fps  # Tiempo en segundos

        # Círculo rojo que se mueve horizontalmente
        circle_x = int((width / 2) + (width / 4) * np.sin(2 * np.pi * t / 2))
        circle_y = height // 4
        cv2.circle(frame, (circle_x, circle_y), 50, (0, 0, 255), -1)

        # Rectángulo azul que se mueve verticalmente
        rect_x = width // 4
        rect_y = int((height / 2) + (height / 4) * np.cos(2 * np.pi * t / 3))
        cv2.rectangle(frame, (rect_x - 40, rect_y - 40), (rect_x + 40, rect_y + 40), (255, 0, 0), -1)

        # Triángulo verde que rota
        triangle_center_x = 3 * width // 4
        triangle_center_y = height // 2
        angle = 2 * np.pi * t
        triangle_size = 50
        pts = []
        for i in range(3):
            a = angle + i * 2 * np.pi / 3
            x = int(triangle_center_x + triangle_size * np.cos(a))
            y = int(triangle_center_y + triangle_size * np.sin(a))
            pts.append([x, y])
        pts = np.array(pts, dtype=np.int32)
        cv2.fillPoly(frame, [pts], (0, 255, 0))

        # Texto con número de frame
        cv2.putText(frame, f"Frame {frame_num}/{total_frames}", (10, height - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

        # Línea amarilla que crece
        line_length = int((width - 40) * (frame_num % fps) / fps)
        cv2.line(frame, (20, 3 * height // 4), (20 + line_length, 3 * height // 4), (0, 255, 255), 5)

        # Escribir frame
        out.write(frame)

        # Progress
        if (frame_num + 1) % 30 == 0:
            print(f"  Progreso: {frame_num + 1}/{total_frames} frames ({(frame_num + 1) / total_frames * 100:.1f}%)")

    out.release()
    print(f"Video generado: {output_path}")
    print(f"  Tamaño: {Path(output_path).stat().st_size / 1024:.2f} KB")
    print(f"  Resolución: {width}x{height}")
    print(f"  FPS: {fps}")
    print(f"  Duración: {duration_seconds}s")


def main():
    parser = argparse.ArgumentParser(description='Genera un video de prueba para el sistema')
    parser.add_argument('--output', default='test_video.mp4', help='Ruta del video de salida (default: test_video.mp4)')
    parser.add_argument('--duration', type=int, default=5, help='Duración en segundos (default: 5)')
    parser.add_argument('--fps', type=int, default=30, help='Frames por segundo (default: 30)')
    parser.add_argument('--width', type=int, default=640, help='Ancho (default: 640)')
    parser.add_argument('--height', type=int, default=480, help='Alto (default: 480)')

    args = parser.parse_args()

    generate_test_video(args.output, args.duration, args.fps, args.width, args.height)


if __name__ == '__main__':
    main()
