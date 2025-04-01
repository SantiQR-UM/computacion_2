import os, time


def atender_cliente(n):

    pid = os.fork()

    if pid == 0:
        print(f"[HIJO {n}] Atendiendo cliente")
        time.sleep(2)
        print(f"[HIJO {n}] Finalizado")
        os._exit(0)


for cliente in range(5):
    
    atender_cliente(cliente)


for _ in range(5):

    os.wait()