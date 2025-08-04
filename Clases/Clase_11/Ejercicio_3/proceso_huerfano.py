import os
import time

def create_orphan_process():
    pid = os.fork()

    if pid == 0:  # Proceso Hijo
        print(f"Soy el proceso hijo (PID: {os.getpid()}). Mi PPID inicial es: {os.getppid()}")
        print("El hijo esperará 15 segundos para dar tiempo al padre a terminar.")
        time.sleep(15)  # El hijo espera
        print(f"Soy el proceso hijo (PID: {os.getpid()}). Mi PPID actual es: {os.getppid()}")
        print("El hijo terminará ahora.")
    else:  # Proceso Padre
        print(f"Soy el proceso padre (PID: {os.getpid()}). Mi hijo tiene PID: {pid}")
        print("El padre terminará inmediatamente.")
        # El padre no espera al hijo, por lo que el hijo se convertirá en huérfano.
        os._exit(0) # El padre termina
        # time.sleep(5) # Esto no se ejecutará, el padre ya terminó

if __name__ == "__main__":
    create_orphan_process()