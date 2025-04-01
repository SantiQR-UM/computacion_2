import os

pid = os.fork()

if pid == 0:
    os.execlp("ls", "ls", "-l")  # Reemplaza el proceso hijo

else:
    os.wait()