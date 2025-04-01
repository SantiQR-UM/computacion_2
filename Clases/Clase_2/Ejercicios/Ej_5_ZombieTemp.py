import os, time

pid = os.fork()

if pid == 0:
    print(f"Soy el hijo, voy a morir, mi pid es {os.getpid()}")
    os._exit(0)

else:
    print("Soy el padre: todavia no llamaré a wait(). Observa el zombi con 'ps -el'")
    time.sleep(15)
    os.wait()