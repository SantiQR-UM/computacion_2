import os
import sys

def main():
    # Crear dos pipes: uno para enviar del padre al hijo, otro para recibir respuesta
    parent_to_child_r, parent_to_child_w = os.pipe()
    child_to_parent_r, child_to_parent_w = os.pipe()
    
    # Bifurcar el proceso
    pid = os.fork()
    
    if pid > 0:  # Proceso padre
        # Cerrar extremos no utilizados
        os.close(parent_to_child_r)
        os.close(child_to_parent_w)
        
        # Mensaje a enviar
        message = "Hola, proceso hijo!"
        print(f"Padre: Enviando mensaje: '{message}'")
        
        # Enviar mensaje al hijo
        os.write(parent_to_child_w, message.encode())
        os.close(parent_to_child_w)  # Cerrar después de escribir
        
        # Recibir respuesta del hijo
        response = os.read(child_to_parent_r, 1024).decode()
        os.close(child_to_parent_r)  # Cerrar después de leer
        
        print(f"Padre: Recibí respuesta: '{response}'")
        
        # Esperar a que el hijo termine
        os.waitpid(pid, 0)
        
    else:  # Proceso hijo
        # Cerrar extremos no utilizados
        os.close(parent_to_child_w)
        os.close(child_to_parent_r)
        
        # Leer mensaje del padre
        message = os.read(parent_to_child_r, 1024).decode()
        os.close(parent_to_child_r)  # Cerrar después de leer
        
        print(f"Hijo: Recibí mensaje: '{message}'")
        
        # Enviar eco al padre
        os.write(child_to_parent_w, message.encode())
        os.close(child_to_parent_w)  # Cerrar después de escribir
        
        # Salir del proceso hijo
        sys.exit(0)

if __name__ == "__main__":
    main()