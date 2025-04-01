import os, time

pid = os.fork()
if pid > 0:
    print(f"[PADRE] Terminando, mi pid es {os.getpid()}")
    os._exit(0)
else:
    print(f"[HIJO] Ahora soy huérfano, mi pid es {os.getpid()}. Mi nuevo padre es systemd con pid: {os.getppid()}")
    time.sleep(5)