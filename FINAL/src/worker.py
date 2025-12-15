"""
Worker de Celery para procesar frames de video.

Este worker recibe frames individuales y aplica filtros de procesamiento usando OpenCV.
"""

import os
import sys
import time
import cv2
import numpy as np
from celery import Celery
from typing import Dict, Any, Tuple
import psutil
import logging

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE LOGGING
# Temporalmente habilitamos logs completos para debugging
# logging.getLogger('celery.app.trace').setLevel(logging.WARNING)
# -----------------------------------------------------------------------------

# Configuración de Celery
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# No usar result backend - los resultados se escriben directamente a disco
app = Celery('video_processor', broker=REDIS_URL, backend=None)

# Configuración de Celery
app.conf.update(
    task_serializer='pickle',  # Pickle es más eficiente y no tiene problemas de truncamiento
    accept_content=['json', 'pickle'],
    result_serializer='pickle',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=7200,  # 2 horas
    result_backend_transport_options={
        'retry_policy': {
            'timeout': 30.0,
            'max_retries': 5,
        },
        'socket_keepalive': True,
        'socket_timeout': 30.0,
    },
    broker_transport_options={
        'socket_timeout': 30.0,
        'socket_keepalive': True,
    },
)

# Importar filtros
sys.path.insert(0, os.path.dirname(__file__))
from filters import apply_blur, apply_edge_detection, detect_and_draw_faces, detect_motion, FaceDetector, MotionDetector


@app.task(bind=True, max_retries=3, default_retry_delay=5, queue='frames', name='process_frame')
def process_frame(
    self,
    frame_data: bytes,
    frame_number: int,
    processing_type: str,
    metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
    """
    Procesa un frame individual aplicando filtros según el tipo especificado.
    """
    start_time = time.time()
    process = psutil.Process(os.getpid())
    memory_start = process.memory_info().rss / 1024 / 1024  # MB

    metadata = metadata or {}

    try:
        # Decodificar frame
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("No se pudo decodificar el frame")

        # Aplicar procesamiento según tipo
        if processing_type == "blur":
            params = metadata.get("blur_params", {"blur_type": "gaussian", "kernel": 31})
            blur_type = params.pop("blur_type", "gaussian")
            processed_frame = apply_blur(
                frame,
                blur_type=blur_type,
                **params
            )
            filter_name = f"blur_{blur_type}"

        elif processing_type == "edges":
            params = metadata.get("edge_params", {"edge_type": "canny"})
            # Esta función no tiene estado, se puede llamar directamente
            processed_frame = apply_edge_detection(
                frame,
                edge_type=params.get("edge_type", "canny"),
                params=params
            )
            filter_name = f"edges_{params.get('edge_type', 'canny')}"

        elif processing_type == "faces":
            # Inicializar detector compartido (FaceDetector no tiene estado por frame)
            if not hasattr(self, 'face_detector'):
                self.face_detector = FaceDetector()

            params = metadata.get("face_params", {})
            processed_frame = detect_and_draw_faces(frame, self.face_detector, params)
            filter_name = "face_detection"

        elif processing_type == "motion":
            # Usar detector por sesión para evitar mezclar estado entre videos
            if not hasattr(self, 'motion_detectors'):
                self.motion_detectors = {}

            session_id = metadata.get('session_id', 'default')
            if session_id not in self.motion_detectors:
                self.motion_detectors[session_id] = MotionDetector()

            params = metadata.get("motion_params", {"motion_type": "diff"})
            processed_frame = detect_motion(
                frame,
                self.motion_detectors[session_id],
                motion_type=params.get("motion_type", "diff"),
                params=params
            )
            filter_name = f"motion_{params.get('motion_type', 'diff')}"

        elif processing_type == "custom":
            # Pipeline personalizado
            filters_list = metadata.get("filters", [])
            processed_frame = frame
            filter_name = "custom_"

            for filter_spec in filters_list:
                filter_type = filter_spec[0]
                filter_params = filter_spec[1] if len(filter_spec) > 1 else {}

                if filter_type == "blur":
                    processed_frame = apply_blur(processed_frame, **filter_params)
                elif filter_type == "edges":
                    processed_frame = apply_edge_detection(processed_frame, params=filter_params)
                elif filter_type == "faces":
                    if not hasattr(self, 'face_detector'):
                        self.face_detector = FaceDetector()
                    processed_frame = detect_and_draw_faces(processed_frame, self.face_detector, filter_params)

                filter_name += filter_type + "_"

        else:
            # Sin procesamiento, devolver frame original
            processed_frame = frame
            filter_name = "none"

        # Guardar frame procesado en volumen compartido
        # En lugar de retornar el frame completo, guardarlo en disco y retornar la ruta
        # Usar directorio específico de la sesión para soportar múltiples clientes concurrentes
        session_id = metadata.get('session_id', 'default')
        frames_dir = f'/app/data/frames/{session_id}'
        os.makedirs(frames_dir, exist_ok=True)

        frame_path = os.path.join(frames_dir, f'frame_{frame_number:06d}.png')
        success = cv2.imwrite(frame_path, processed_frame)
        if not success:
            raise ValueError("No se pudo guardar el frame procesado")

        # Calcular estadísticas
        end_time = time.time()
        memory_end = process.memory_info().rss / 1024 / 1024  # MB
        processing_time_ms = (end_time - start_time) * 1000

        stats = {
            "processing_time_ms": processing_time_ms,
            "memory_mb": memory_end,
            "memory_delta_mb": memory_end - memory_start,
            "filter_applied": filter_name,
            "worker_id": self.request.id,
            "hostname": self.request.hostname
        }

        # Guardar stats en archivo JSON para que el servidor las pueda leer
        import json
        stats_path = os.path.join(frames_dir, f'frame_{frame_number:06d}.json')
        with open(stats_path, 'w') as f:
            json.dump(stats, f)

        result = {
            "frame_path": frame_path,
            "frame_number": frame_number,
            "stats": stats
        }

        return result

    except Exception as e:
        # Reintentar en caso de error
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        else:
            # Registrar error y guardar frame original
            print(f"Error procesando frame {frame_number} después de {self.max_retries} reintentos: {e}")

            # Guardar frame original en caso de error
            session_id = metadata.get('session_id', 'default')
            frames_dir = f'/app/data/frames/{session_id}'
            os.makedirs(frames_dir, exist_ok=True)
            frame_path = os.path.join(frames_dir, f'frame_{frame_number:06d}.png')

            # Decodificar y guardar frame original
            try:
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    cv2.imwrite(frame_path, frame)
            except:
                pass

            return {
                "frame_path": frame_path,
                "frame_number": frame_number,
                "stats": {
                    "processing_time_ms": 0,
                    "memory_mb": 0,
                    "memory_delta_mb": 0,
                    "filter_applied": "error",
                    "worker_id": self.request.id,
                    "error": str(e)
                }
            }


if __name__ == '__main__':
    # Ejecutar worker
    # celery -A worker.app worker --loglevel=INFO -Q frames
    app.start()
