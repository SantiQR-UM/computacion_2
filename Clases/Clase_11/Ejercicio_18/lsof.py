import os
import time

def pipe_lsof_example():
    # Creamos un pipe
    # read_fd: descriptor de archivo para leer
    # write_fd: descriptor de archivo para escribir
    read_fd, write_fd = os.pipe()

    pid = os.fork()

    if pid == 0:  # Proceso Hijo
        child_pid = os.getpid()
        parent_pid = os.getppid()
        print(f"Soy el proceso hijo (PID: {child_pid}, PPID: {parent_pid}).")
        
        # El hijo solo necesita escribir, cierra el descriptor de lectura
        os.close(read_fd) 
        
        message = "¡Hola desde el hijo para el padre!"
        print(f"Hijo (PID: {child_pid}): Enviando mensaje al padre. Descriptores abiertos para el hijo: {os.listdir(f'/proc/{child_pid}/fd')}")
        os.write(write_fd, message.encode('utf-8'))
        
        print(f"Hijo (PID: {child_pid}): Mensaje enviado. Esperando 15 segundos para que lo observes con 'lsof -p {child_pid}'...")
        # Mantén el descriptor de escritura abierto para que lsof lo vea
        time.sleep(15) 
        
        os.close(write_fd)
        print(f"Hijo (PID: {child_pid}): Descriptor de escritura cerrado. Terminando.")
        os._exit(0) 

    else:  # Proceso Padre
        parent_pid = os.getpid()
        print(f"Soy el proceso padre (PID: {parent_pid}). Mi hijo tiene PID: {pid}")
        
        # El padre solo necesita leer, cierra el descriptor de escritura
        os.close(write_fd)
        
        print(f"Padre (PID: {parent_pid}): Esperando mensaje del hijo. Descriptores abiertos para el padre: {os.listdir(f'/proc/{parent_pid}/fd')}")
        print(f"Padre (PID: {parent_pid}): Esperando 20 segundos para que observes el pipe con 'lsof -p {parent_pid}'...")
        # Mantén el descriptor de lectura abierto para que lsof lo vea
        time.sleep(20) 
        
        print(f"Padre (PID: {parent_pid}): Ahora leyendo mensaje del hijo...")
        received_message_bytes = os.read(read_fd, 1024)
        received_message = received_message_bytes.decode('utf-8')
        print(f"Padre (PID: {parent_pid}): Recibió: '{received_message}'")
        
        os.close(read_fd)
        print(f"Padre (PID: {parent_pid}): Descriptor de lectura cerrado.")
        
        # El padre espera al hijo para recolectar su estado
        status = os.waitpid(pid, 0)
        print(f"Padre: El proceso hijo (PID: {status[0]}) ha terminado.")
        print(f"Padre (PID: {parent_pid}) finalizando.")

if __name__ == "__main__":
    print ("lsof -p 12346 <-- Reemplaza con el PID real del hijo")
    pipe_lsof_example()