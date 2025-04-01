import os

pid = os.fork()

if pid == 0:
    print(f"Soy el hijo y mi pid es: {os.getpid()}, y el de mi padre es: {os.getppid()}")

else:
    print(f"Soy el padre y mi pid es: {os.getpid()}, y el de mi hijo es: {pid}")