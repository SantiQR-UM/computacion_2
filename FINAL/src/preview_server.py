"""
Servidor HTTP de Preview para monitorear procesamiento de videos.

Expone endpoints para ver el progreso en tiempo real y previews de videos.
Usa Flask + Server-Sent Events + Redis para updates en tiempo real.
"""

import os
import sys
import time
import glob
import json
import redis
from flask import Flask, Response, render_template_string, send_file, jsonify
from PIL import Image
from pathlib import Path
import argparse

app = Flask(__name__)

# Configuración de Redis
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Directorios
FRAMES_DIR = '/app/data/frames'
GIFS_DIR = '/app/data/gifs'
os.makedirs(GIFS_DIR, exist_ok=True)


def get_active_sessions():
    """Obtiene lista de sesiones activas/recientes desde Redis."""
    sessions = []

    # Buscar todas las keys de sesiones
    session_keys = redis_client.keys('session:*:total_frames')

    for key in session_keys:
        session_id = key.split(':')[1]

        try:
            total_frames = int(redis_client.get(f'session:{session_id}:total_frames') or 0)
            status = redis_client.get(f'session:{session_id}:status') or 'unknown'
            processing_type = redis_client.get(f'session:{session_id}:processing_type') or 'unknown'
            video_name = redis_client.get(f'session:{session_id}:video_name') or 'unknown'
            start_time = redis_client.get(f'session:{session_id}:start_time')

            sessions.append({
                'session_id': session_id,
                'total_frames': total_frames,
                'status': status,
                'processing_type': processing_type,
                'video_name': video_name,
                'start_time': start_time
            })
        except:
            continue

    # Ordenar por tiempo de inicio (más recientes primero)
    sessions.sort(key=lambda x: x.get('start_time', ''), reverse=True)

    return sessions


def get_session_progress(session_id):
    """Calcula el progreso de una sesión contando frames procesados."""
    try:
        # Obtener metadata de Redis
        total_frames = int(redis_client.get(f'session:{session_id}:total_frames') or 0)
        status = redis_client.get(f'session:{session_id}:status') or 'unknown'
        processing_type = redis_client.get(f'session:{session_id}:processing_type') or 'unknown'
        video_name = redis_client.get(f'session:{session_id}:video_name') or 'unknown'
        start_time_str = redis_client.get(f'session:{session_id}:start_time')

        # Obtener frames procesados de Redis (actualizado en tiempo real por el servidor)
        processed_count_str = redis_client.get(f'session:{session_id}:frames_processed')
        if processed_count_str:
            processed_count = int(processed_count_str)
        else:
            # Fallback: contar frames en el filesystem si Redis no tiene el valor
            frames_dir = os.path.join(FRAMES_DIR, session_id)
            if os.path.exists(frames_dir):
                processed_count = len(glob.glob(os.path.join(frames_dir, 'frame_*.png')))
            else:
                processed_count = 0

        # Calcular progreso
        progress = (processed_count / total_frames * 100) if total_frames > 0 else 0

        # Obtener FPS y ETA directamente de Redis (calculados por el servidor)
        current_fps_str = redis_client.get(f'session:{session_id}:current_fps')
        eta_seconds_str = redis_client.get(f'session:{session_id}:eta_seconds')

        # Usar valores de Redis si existen, sino calcular como fallback
        fps = 0
        eta = None

        if current_fps_str:
            try:
                fps = float(current_fps_str)
            except:
                pass

        if eta_seconds_str:
            try:
                eta = float(eta_seconds_str)
            except:
                pass

        # Fallback: calcular si Redis no tiene los valores
        if fps == 0 and start_time_str:
            try:
                start_time = float(start_time_str)
                elapsed = time.time() - start_time
                if elapsed >= 1.0 and processed_count > 0:
                    fps = processed_count / elapsed
            except:
                pass

        # Si el status es completado, obtener tiempo total de procesamiento
        total_time = None
        if status == 'completed':
            eta = 0
            total_time_str = redis_client.get(f'session:{session_id}:total_time_seconds')
            if total_time_str:
                try:
                    total_time = float(total_time_str)
                except:
                    pass

        return {
            'session_id': session_id,
            'video_name': video_name,
            'processing_type': processing_type,
            'total_frames': total_frames,
            'processed_frames': processed_count,
            'progress': round(progress, 2),
            'status': status,
            'fps': round(fps, 2),
            'eta_seconds': round(eta, 1) if eta is not None else None,
            'total_time_seconds': round(total_time, 1) if total_time is not None else None
        }
    except Exception as e:
        return {
            'session_id': session_id,
            'error': str(e),
            'status': 'error'
        }


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route('/')
def dashboard():
    """Dashboard HTML principal."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Processing Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .sessions {
                display: grid;
                gap: 20px;
                grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            }
            .session {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }
            .session:hover {
                transform: translateY(-5px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.15);
            }
            .session-header {
                margin-bottom: 15px;
            }
            .session-title {
                font-size: 1.2em;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }
            .session-type {
                display: inline-block;
                padding: 4px 12px;
                background: #667eea;
                color: white;
                border-radius: 20px;
                font-size: 0.85em;
                margin-right: 10px;
            }
            .session-id {
                display: inline-block;
                font-size: 0.85em;
                color: #666;
                font-family: monospace;
            }
            .progress-container {
                background: #f0f0f0;
                border-radius: 10px;
                height: 30px;
                margin: 15px 0;
                overflow: hidden;
                position: relative;
            }
            .progress-bar {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                transition: width 0.5s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
            }
            .progress-text {
                position: absolute;
                width: 100%;
                text-align: center;
                line-height: 30px;
                font-weight: bold;
                color: #333;
                mix-blend-mode: difference;
            }
            .session-stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin: 15px 0;
                font-size: 0.9em;
            }
            .stat {
                text-align: center;
                padding: 8px;
                background: #f8f8f8;
                border-radius: 6px;
            }
            .stat-value {
                font-weight: bold;
                color: #667eea;
                font-size: 1.2em;
            }
            .stat-label {
                color: #666;
                font-size: 0.85em;
                margin-top: 3px;
            }
            .preview-container {
                margin-top: 15px;
                text-align: center;
                display: none;
            }
            .preview-container.show {
                display: block;
            }
            .preview-img {
                max-width: 100%;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .status-badge {
                display: inline-block;
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: bold;
                margin-top: 10px;
            }
            .status-processing {
                background: #ffd93d;
                color: #333;
            }
            .status-completed {
                background: #6bcf7f;
                color: white;
            }
            .status-error {
                background: #ff6b6b;
                color: white;
            }
            .no-sessions {
                text-align: center;
                color: white;
                font-size: 1.2em;
                margin-top: 50px;
            }
            .refresh-info {
                text-align: center;
                color: white;
                margin-top: 20px;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 Video Processing Dashboard</h1>
            <div id="sessions" class="sessions"></div>
            <div id="no-sessions" class="no-sessions" style="display:none;">
                No hay sesiones activas en este momento.
            </div>
            <div class="refresh-info">
                Updates automáticos cada segundo
            </div>
        </div>

        <script>
            const sessionsContainer = document.getElementById('sessions');
            const noSessionsMsg = document.getElementById('no-sessions');
            const eventSources = {};

            function updateDashboard() {
                fetch('/sessions')
                    .then(r => r.json())
                    .then(sessions => {
                        if (sessions.length === 0) {
                            sessionsContainer.innerHTML = '';
                            noSessionsMsg.style.display = 'block';
                            return;
                        }

                        noSessionsMsg.style.display = 'none';

                        sessions.forEach(session => {
                            let sessionDiv = document.getElementById('session-' + session.session_id);

                            if (!sessionDiv) {
                                sessionDiv = createSessionCard(session);
                                sessionsContainer.appendChild(sessionDiv);

                                // Conectar SSE para updates en tiempo real
                                connectSSE(session.session_id);
                            }
                        });
                    });
            }

            function createSessionCard(session) {
                const div = document.createElement('div');
                div.id = 'session-' + session.session_id;
                div.className = 'session';
                div.innerHTML = `
                    <div class="session-header">
                        <div class="session-title">${session.video_name || 'Video'}</div>
                        <span class="session-type">${session.processing_type || 'unknown'}</span>
                        <span class="session-id">${session.session_id}</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: 0%">0%</div>
                    </div>
                    <div class="session-stats">
                        <div class="stat">
                            <div class="stat-value" data-frames>0/0</div>
                            <div class="stat-label">Frames</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value" data-fps>0</div>
                            <div class="stat-label">FPS</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value" data-eta>-</div>
                            <div class="stat-label">ETA</div>
                        </div>
                    </div>
                    <div class="status-badge status-processing">Procesando...</div>
                    <div class="preview-container">
                        <img class="preview-img" src="/session/${session.session_id}/preview.gif" alt="Preview">
                    </div>
                `;
                return div;
            }

            function connectSSE(sessionId) {
                if (eventSources[sessionId]) return;

                const source = new EventSource('/session/' + sessionId + '/stream');
                eventSources[sessionId] = source;

                source.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    updateSessionCard(sessionId, data);

                    if (data.status === 'completed') {
                        source.close();
                        delete eventSources[sessionId];
                    }
                };

                source.onerror = () => {
                    source.close();
                    delete eventSources[sessionId];
                };
            }

            function updateSessionCard(sessionId, data) {
                const card = document.getElementById('session-' + sessionId);
                if (!card) return;

                const progressBar = card.querySelector('.progress-bar');
                const framesValue = card.querySelector('[data-frames]');
                const fpsValue = card.querySelector('[data-fps]');
                const etaValue = card.querySelector('[data-eta]');
                const statusBadge = card.querySelector('.status-badge');
                const previewContainer = card.querySelector('.preview-container');

                progressBar.style.width = data.progress + '%';
                progressBar.textContent = data.progress.toFixed(1) + '%';

                framesValue.textContent = `${data.processed_frames}/${data.total_frames}`;
                fpsValue.textContent = data.fps.toFixed(1);

                // Mostrar ETA o tiempo total según el estado
                if (data.status === 'completed' && data.total_time_seconds) {
                    etaValue.textContent = formatTime(data.total_time_seconds);
                    etaValue.parentElement.querySelector('.stat-label').textContent = 'Tiempo Total';
                } else if (data.eta_seconds === null || data.eta_seconds === undefined) {
                    etaValue.textContent = 'Calculando...';
                } else if (data.eta_seconds > 0) {
                    etaValue.textContent = formatTime(data.eta_seconds);
                    etaValue.parentElement.querySelector('.stat-label').textContent = 'ETA';
                } else {
                    etaValue.textContent = '-';
                    etaValue.parentElement.querySelector('.stat-label').textContent = 'ETA';
                }

                // Actualizar status badge
                statusBadge.className = 'status-badge status-' + data.status;
                if (data.status === 'completed') {
                    statusBadge.textContent = 'Completado ✓';
                    previewContainer.classList.add('show');
                } else if (data.status === 'processing') {
                    statusBadge.textContent = 'Procesando...';
                } else if (data.status === 'error') {
                    statusBadge.textContent = 'Error ✗';
                }
            }

            function formatTime(seconds) {
                if (seconds < 60) {
                    return seconds.toFixed(0) + 's';
                }
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                return `${mins}m ${secs}s`;
            }

            // Iniciar updates
            updateDashboard();
            setInterval(updateDashboard, 5000); // Refresh lista cada 5s
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/sessions')
def list_sessions():
    """Retorna lista de sesiones activas en JSON."""
    sessions = get_active_sessions()
    return jsonify(sessions)


@app.route('/session/<session_id>/status')
def session_status(session_id):
    """Retorna el estado de una sesión específica."""
    progress = get_session_progress(session_id)
    return jsonify(progress)


@app.route('/session/<session_id>/stream')
def session_stream(session_id):
    """Stream de progreso en tiempo real usando Server-Sent Events."""
    def generate():
        while True:
            progress = get_session_progress(session_id)
            yield f"data: {json.dumps(progress)}\n\n"

            # Si está completado o con error, terminar stream
            if progress.get('status') in ['completed', 'error']:
                break

            time.sleep(0.5)  # Update cada 500ms

    return Response(generate(), mimetype='text/event-stream')


@app.route('/session/<session_id>/preview.gif')
def preview_gif(session_id):
    """Genera y sirve un GIF preview del video procesado."""
    gif_path = os.path.join(GIFS_DIR, f'{session_id}.gif')

    # Si ya existe el GIF, servirlo
    if os.path.exists(gif_path):
        return send_file(gif_path, mimetype='image/gif')

    # Generar GIF
    frames_dir = os.path.join(FRAMES_DIR, session_id)

    if not os.path.exists(frames_dir):
        return jsonify({'error': 'Sesión no encontrada'}), 404

    frame_files = sorted(glob.glob(os.path.join(frames_dir, 'frame_*.png')))

    if not frame_files:
        return jsonify({'error': 'No hay frames procesados aún'}), 404

    try:
        # Tomar máximo 30 frames para que el GIF no sea muy pesado
        max_frames = 30
        step = max(1, len(frame_files) // max_frames)
        selected_frames = frame_files[::step][:max_frames]

        # Cargar imágenes
        images = [Image.open(f) for f in selected_frames]

        # Redimensionar si son muy grandes (max 480p para el preview)
        max_width = 640
        if images[0].width > max_width:
            ratio = max_width / images[0].width
            new_height = int(images[0].height * ratio)
            images = [img.resize((max_width, new_height), Image.Resampling.LANCZOS) for img in images]

        # Guardar como GIF
        images[0].save(
            gif_path,
            save_all=True,
            append_images=images[1:],
            duration=100,  # 100ms por frame (10 FPS)
            loop=0
        )

        return send_file(gif_path, mimetype='image/gif')

    except Exception as e:
        return jsonify({'error': f'Error generando GIF: {str(e)}'}), 500


@app.route('/session/<session_id>/frame/<int:frame_num>')
def get_frame(session_id, frame_num):
    """Retorna un frame específico como imagen PNG."""
    frame_path = os.path.join(FRAMES_DIR, session_id, f'frame_{frame_num:06d}.png')

    if not os.path.exists(frame_path):
        return jsonify({'error': 'Frame no encontrado'}), 404

    return send_file(frame_path, mimetype='image/png')


def main():
    """Punto de entrada del preview server."""
    parser = argparse.ArgumentParser(description='Servidor HTTP de Preview')
    parser.add_argument('--host', default='0.0.0.0', help='Host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='Puerto (default: 8080)')
    parser.add_argument('--debug', action='store_true', help='Modo debug')

    args = parser.parse_args()

    print(f"Iniciando Preview Server en http://{args.host}:{args.port}")
    print(f"Dashboard: http://{args.host}:{args.port}/")

    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == '__main__':
    main()
