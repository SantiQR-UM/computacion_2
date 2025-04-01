import os

# Num de hijos
n = 2

for i in range(n):
    pid = os.fork()
    if pid == 0:
        print(f"Soy el hijo {i} y mi pid es: {os.getpid()}, y el de mi padre es: {os.getppid()}")
        os._exit(0)
        break

for i in range(n):
    os.wait()

print(f"Soy el padre y mi pid es: {os.getpid()}")