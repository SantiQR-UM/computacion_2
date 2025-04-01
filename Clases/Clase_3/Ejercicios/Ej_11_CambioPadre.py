import os
import time

def crear_hijo(espera, msg):
    pid = os.fork()
    if pid == 0:
        print(msg)
        time.sleep(espera)
        print(f"{msg} mi pid es: {os.getpid()}, el pid de mi padre es: {os.getppid()}") 
        os._exit(0)

if __name__ == "__main__":
    crear_hijo(2, "Soy el hijo 1")
    crear_hijo(4, "Soy el hijo 2 que quedara huerfano")

    ## Si quiero que el padre espere a los hijos, debo esperarlos:

    # Solo espera un tiempo dado
    #time.sleep(1)
    # Solo espera 1 el os.wait(), con 2 espera a los 2 hijos
    #os.wait()
    #os.wait()
    # Wait pid con -1 espera a todos los hijos, pero hay q hacer un while True, es lo mismo...
    while True:
        try:
            os.waitpid(-1, 0)
        except ChildProcessError:
            break  # No hay más hijos

    print(f"Soy el padre, mi pid es: {os.getpid()}, el del abuelo es {os.getppid()}")