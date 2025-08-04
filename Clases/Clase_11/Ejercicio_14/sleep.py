import os
import time
import sys

def main_sleep_script():
    pid = os.getpid()
    print(f"[{pid}] Script de sueño iniciado. Dormiré por 10 segundos...", flush=True)
    
    # Manejar SIGTERM para un mensaje de salida limpio
    def sigterm_handler(signum, frame):
        print(f"\n[{pid}] ¡Señal SIGTERM ({signum}) recibida! Terminando prematuramente.", flush=True)
        sys.exit(0)

    import signal
    signal.signal(signal.SIGTERM, sigterm_handler)

    try:
        time.sleep(10)
        print(f"[{pid}] Desperté después de 10 segundos. Terminando normalmente.", flush=True)
    except KeyboardInterrupt:
        print(f"\n[{pid}] Interrumpido por Ctrl+C.", flush=True)
    except Exception as e:
        print(f"\n[{pid}] Ocurrió un error inesperado: {e}", flush=True)
    finally:
        sys.exit(0)

if __name__ == "__main__":
    main_sleep_script()