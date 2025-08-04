import os
import signal
import time
import sys

# Contador para SIGUSR1
sigusr1_count = 0

def handle_sigusr1(signum, frame):
    global sigusr1_count
    sigusr1_count += 1
    print(f"\n[PID: {os.getpid()}] Receptor: ¡Señal SIGUSR1 ({signum}) recibida! Conteo: {sigusr1_count}")

def handle_sigusr2(signum, frame):
    print(f"\n[PID: {os.getpid()}] Receptor: ¡Señal SIGUSR2 ({signum}) recibida! Realizando acción especial.")
    # Aquí puedes agregar una lógica diferente para SIGUSR2
    # Por ejemplo, escribir algo en un archivo, cambiar un estado, etc.
    time.sleep(0.5) # Simular una acción
    print(f"[PID: {os.getpid()}] Receptor: Acción especial completada.")

def main_signal_receiver():
    pid = os.getpid()
    print(f"--- Ejercicio 20: Receptor de Señales ---")
    print(f"Receptor (PID: {pid}) listo para recibir señales.")
    print("Para terminar el receptor, envía Ctrl+C o 'kill -SIGTERM {pid}'.")

    # Instalar manejadores para SIGUSR1 y SIGUSR2
    signal.signal(signal.SIGUSR1, handle_sigusr1)
    signal.signal(signal.SIGUSR2, handle_sigusr2)

    try:
        # Poner el proceso en espera pasiva
        print(f"Receptor (PID: {pid}): Entrando en modo de espera (pause())...")
        while True: # Bucle infinito para mantener el proceso vivo
            signal.pause() # Espera por cualquier señal
            # Si una señal es manejada, signal.pause() retorna y el bucle continúa
            # Si una señal no manejada con acción por defecto termina el proceso, el bucle se rompe

    except KeyboardInterrupt:
        print(f"\n[PID: {pid}] Receptor: Proceso terminado por KeyboardInterrupt (Ctrl+C).")
    except Exception as e:
        print(f"\n[PID: {pid}] Receptor: Ocurrió un error: {e}")
    finally:
        print(f"[PID: {os.getpid()}] Receptor: Terminando.")
        sys.exit(0)

if __name__ == "__main__":
    main_signal_receiver()