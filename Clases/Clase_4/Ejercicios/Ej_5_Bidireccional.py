import os
import sys
import select
import signal
import threading

def setup_signal_handler():
    """Configura el manejador de señales para salir limpiamente con Ctrl+C"""
    def signal_handler(sig, frame):
        print("\nSaliendo del chat...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

def read_messages(reader, name, should_exit):
    """Función para leer mensajes del pipe en un hilo separado"""
    try:
        while not should_exit[0]:
            readable, _, _ = select.select([reader], [], [], 0.5)
            if readable:
                message = reader.readline()
                if not message:
                    print(f"\n{name} ha dejado el chat.")
                    should_exit[0] = True
                    break
                print(f"\n{name}: {message.strip()}")
                print("Tú > ", end='', flush=True)
    except Exception as e:
        print(f"\nError al leer mensajes: {e}")
        should_exit[0] = True
    finally:
        try:
            reader.close()
        except:
            pass


def chat_process(read_pipe, write_pipe, name, other_name):
    """Gestiona el proceso de chat para un participante"""
    try:
        # Inicializar objeto para controlar la salida del hilo
        should_exit = [False]
        
        # Configurar el manejador de señales
        setup_signal_handler()
        
        # Abro el pipe de lectura
        reader = os.fdopen(read_pipe, 'r')
        # Abro el pipe de escritura
        writer = os.fdopen(write_pipe, 'w')

        # Crear un hilo para leer mensajes del otro participante
        reader_thread = threading.Thread(
            target=read_messages, 
            args=(reader, other_name, should_exit)
        )
        reader_thread.daemon = True  # El hilo terminará cuando el programa principal termine
        reader_thread.start()
        
        # Abrir el pipe de escritura
    
        print(f"¡Bienvenido al chat, {name}!")
        print(f"Estás chateando con {other_name}.")
        print("Escribe 'exit' para salir.\n")
        
        # Bucle principal para enviar mensajes
        while not should_exit[0]:
            message = input(f"Tú > ")
            
            if message.lower() == 'exit':
                print("Saliendo del chat...")
                should_exit[0] = True
                break
            
            # Enviar el mensaje
            try:
                writer.write(f"{message}\n")
                writer.flush()
            except BrokenPipeError:
                print("El otro participante ha cerrado el chat. Cerrando...")
                should_exit[0] = True
                break

        
    except Exception as e:
        print(f"Error en el proceso de chat: {e}")
    finally:
        try:
            writer.close()
        except:
            pass


def main():
    # Crear pipes para comunicación bidireccional
    pipe_a_to_b_r, pipe_a_to_b_w = os.pipe()  # A envía a B
    pipe_b_to_a_r, pipe_b_to_a_w = os.pipe()  # B envía a A
    
    # Bifurcar el proceso
    pid = os.fork()
    
    if pid > 0:  # Proceso padre (participante A)
        # Cerrar extremos no utilizados
        os.close(pipe_a_to_b_r)
        os.close(pipe_b_to_a_w)
        
        # Gestionar el chat como participante A
        chat_process(pipe_b_to_a_r, pipe_a_to_b_w, "Participante A", "Participante B")
        
        # Esperar a que el proceso hijo termine
        try:
            os.waitpid(pid, 0)
        except:
            pass
        
    else:  # Proceso hijo (participante B)
        # Cerrar extremos no utilizados
        os.close(pipe_a_to_b_w)
        os.close(pipe_b_to_a_r)
        
        # Gestionar el chat como participante B
        chat_process(pipe_a_to_b_r, pipe_b_to_a_w, "Participante B", "Participante A")
        
        # Salir del proceso hijo
        sys.exit(0)

if __name__ == "__main__":
    main()