import os

# Cantidad de hijos
n = 3

for _ in range(n):

    pid = os.fork()
    
    # Los hijos al crearse, hablan y terminan
    if pid == 0:
        print(f"[HIJO] PID: {os.getpid()}  Padre: {os.getppid()}")
        os._exit(0)


for _ in range(n):
    # El padre espera a que los hijos terminen
    os.wait()
    print("[PADRE] Recolectando hijo")

print("[PADRE] Terminando")