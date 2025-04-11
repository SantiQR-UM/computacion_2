import os
import sys

def main():
    # Crear un pipe
    read_fd, write_fd = os.pipe()
    
    # Bifurcar el proceso
    pid = os.fork()
    
    if pid > 0:  # Proceso padre
        # Cerrar el extremo de lectura en el padre
        os.close(read_fd)
        
        # Convertir el descriptor de escritura a un objeto de archivo
        write_pipe = os.fdopen(write_fd, 'w')
        
        # Solicitar entrada al usuario
        message = input("Ingrese un mensaje para enviar al proceso hijo: ")
        
        # Enviar el mensaje al hijo
        write_pipe.write(message + "\n")
        write_pipe.flush()  # Asegurar que los datos se envíen inmediatamente
        
        print(f"Padre: Mensaje enviado al hijo.")
        
        # Cerrar el pipe de escritura
        write_pipe.close()
        
        # Esperar a que el hijo termine
        os.waitpid(pid, 0)
        print("Padre: El proceso hijo ha terminado.")
        
    else:  # Proceso hijo
        # Cerrar el extremo de escritura en el hijo
        os.close(write_fd)
        
        # Convertir el descriptor de lectura a un objeto de archivo
        read_pipe = os.fdopen(read_fd)
        
        print("Hijo: Esperando mensaje del padre...")
        
        # Leer el mensaje del padre
        message = read_pipe.readline().strip()
        
        print(f"Hijo: Mensaje recibido: '{message}'")
        print(f"Hijo: Procesando el mensaje...")
        
        # Simular algún procesamiento
        processed_message = message.upper()
        
        print(f"Hijo: Mensaje procesado: '{processed_message}'")
        
        # Cerrar el pipe de lectura
        read_pipe.close()
        
        # Salir del proceso hijo
        sys.exit(0)

if __name__ == "__main__":
    main()