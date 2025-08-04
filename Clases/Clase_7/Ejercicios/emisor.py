import os
import signal

pid = 8953  # Reemplazá con el PID real del proceso receptor
os.kill(pid, signal.SIGUSR1)  # ¡Aviso enviado!
