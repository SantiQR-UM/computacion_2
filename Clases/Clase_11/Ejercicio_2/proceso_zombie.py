import os
import time

def create_zombie_process():
    pid = os.fork()

    if pid == 0:  # Proceso Hijo
        print(f"Soy el proceso hijo (PID: {os.getpid()}). Terminando inmediatamente.")
        os._exit(0)  # El hijo termina inmediatamente
    else:  # Proceso Padre
        print(f"Soy el proceso padre (PID: {os.getpid()}). Mi hijo tiene PID: {pid}")
        print("El padre esperará 10 segundos antes de recolectar el estado del hijo.")
        time.sleep(10)  # El padre espera 10 segundos
        print("El padre ha esperado 10 segundos. Ahora recolectará el estado del hijo.")
        # Opcional: Para demostrar que el estado zombi desaparece al recolectar
        # os.wait()
        # print("El estado del hijo ha sido recolectado.")
        # time.sleep(5) # Para dar tiempo a verificar que ya no está en Z

if __name__ == "__main__":
    create_zombie_process()