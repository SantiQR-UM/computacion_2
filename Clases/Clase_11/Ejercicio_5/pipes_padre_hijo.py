import os
import time

def pipe_communication_example():
    # Creamos un pipe
    # read_fd: descriptor de archivo para leer
    # write_fd: descriptor de archivo para escribir
    read_fd, write_fd = os.pipe()

    pid = os.fork()

    if pid == 0:  # Proceso Hijo
        print(f"Soy el proceso hijo (PID: {os.getpid()}).")
        # El hijo solo necesita escribir, por lo que cierra el descriptor de lectura
        os.close(read_fd) 
        
        message = "¡Hola desde el hijo!"
        # Codificamos el mensaje a bytes antes de enviarlo
        os.write(write_fd, message.encode('utf-8'))
        print(f"Hijo envió: '{message}'")
        
        # Cierra el descriptor de escritura después de enviar el mensaje
        os.close(write_fd)
        print("Hijo: descriptor de escritura cerrado.")
        os._exit(0) # El hijo termina

    else:  # Proceso Padre
        print(f"Soy el proceso padre (PID: {os.getpid()}). Mi hijo tiene PID: {pid}")
        # El padre solo necesita leer, por lo que cierra el descriptor de escritura
        os.close(write_fd)
        
        print("Padre esperando mensaje del hijo...")
        # Leemos el mensaje del pipe. Se lee en bytes.
        # El tamaño del buffer (1024) debe ser suficiente para el mensaje
        received_message_bytes = os.read(read_fd, 1024)
        # Decodificamos los bytes a una cadena de texto
        received_message = received_message_bytes.decode('utf-8')
        
        print(f"Padre recibió: '{received_message}'")
        
        # Cierra el descriptor de lectura después de recibir el mensaje
        os.close(read_fd)
        print("Padre: descriptor de lectura cerrado.")
        
        # El padre espera al hijo para recolectar su estado
        status = os.waitpid(pid, 0)
        print(f"El proceso hijo (PID: {status[0]}) ha terminado.")

if __name__ == "__main__":
    pipe_communication_example()