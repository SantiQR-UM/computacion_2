import os
import signal
import time
import sys

def sigusr1_handler(signum, frame):
    """
    Manejador de la señal SIGUSR1.
    """
    print(f"\n[PID: {os.getpid()}] ¡Señal SIGUSR1 ({signum}) recibida!")
    print("Manejador de señal ejecutado. Terminando el proceso.")
    sys.exit(0) # Terminar el proceso después de manejar la señal

def main_signal_handler():
    pid = os.getpid()
    print(f"--- Ejercicio 11: Manejo de Señales ---")
    print(f"Proceso (PID: {pid}) listo para recibir SIGUSR1.")
    print("Para enviar la señal desde Bash, usa: kill -SIGUSR1 {pid}")
    print("Presiona Ctrl+C para salir (si no envías la señal).")

    # Instalar el manejador para SIGUSR1
    signal.signal(signal.SIGUSR1, sigusr1_handler)

    # Entrar en espera pasiva
    # La forma más robusta y de bajo consumo es usar signal.pause()
    # Si quieres un bucle infinito para otras acciones, puedes usar:
    # while True:
    #     time.sleep(1) # Dormir para no consumir CPU
    #     pass

    try:
        # pause() pone el proceso en un estado de espera hasta que reciba una señal.
        # Es ideal para este tipo de escenarios de manejadores de señal.
        signal.pause() 
    except KeyboardInterrupt:
        print("\n[PID: {pid}] Proceso terminado por KeyboardInterrupt (Ctrl+C).")
    except Exception as e:
        print(f"\n[PID: {pid}] Ocurrió un error: {e}")

if __name__ == "__main__":
    main_signal_handler()