import os
import time

FIFO_PATH = "/tmp/mi_fifo"

def emitter_script():
    print(f"Emisor: Intentando abrir FIFO para escritura: {FIFO_PATH}")
    try:
        # Abrir el FIFO en modo escritura binaria
        # 'wb' para escritura binaria
        with open(FIFO_PATH, 'wb') as fifo:
            print("Emisor: FIFO abierto. Escribiendo mensajes...")
            for i in range(5):
                message = f"Mensaje {i+1} desde el emisor."
                # Codificar el mensaje a bytes
                fifo.write(message.encode('utf-8') + b'\n') # Agregamos un salto de línea para facilitar la lectura
                print(f"Emisor: Enviado: '{message}'")
                time.sleep(1) # Espera un segundo entre mensajes
            
            final_message = "FIN_DE_MENSAJES"
            fifo.write(final_message.encode('utf-8') + b'\n')
            print(f"Emisor: Enviado: '{final_message}'")
            print("Emisor: Todos los mensajes enviados y FIFO cerrado.")
            
    except FileNotFoundError:
        print(f"Error: FIFO no encontrado en {FIFO_PATH}. Asegúrate de crearlo con 'mkfifo /tmp/mi_fifo'")
    except Exception as e:
        print(f"Ocurrió un error en el emisor: {e}")

if __name__ == "__main__":
    emitter_script()