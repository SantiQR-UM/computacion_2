import os
import time
import signal
import sys
import argparse

def main_signal_sender():
    parser = argparse.ArgumentParser(description="Envía señales SIGUSR1/SIGUSR2 a un PID específico.")
    parser.add_argument("--pid", type=int, required=True, help="PID del proceso receptor.")
    parser.add_argument("--duration", type=int, default=10, help="Duración en segundos del envío de señales.")
    args = parser.parse_args()

    receiver_pid = args.pid
    duration = args.duration
    sender_pid = os.getpid()

    print(f"--- Ejercicio 20: Emisor de Señales ---")
    print(f"Emisor (PID: {sender_pid}): Listo para enviar señales a PID {receiver_pid} por {duration} segundos.")
    print("Enviando SIGUSR1 cada 2 segundos y SIGUSR2 cada 3 segundos.")

    start_time = time.time()
    signal_count_usr1 = 0
    signal_count_usr2 = 0

    while time.time() - start_time < duration:
        if int(time.time() - start_time) % 2 == 0 and int(time.time() - start_time) % 2 != (int(time.time() - start_time) - 1) % 2:
            # Enviar SIGUSR1 cada 2 segundos (aproximadamente)
            try:
                os.kill(receiver_pid, signal.SIGUSR1)
                signal_count_usr1 += 1
                print(f"Emisor: Enviado SIGUSR1 a {receiver_pid}. Total SIGUSR1: {signal_count_usr1}")
            except ProcessLookupError:
                print(f"Emisor: Proceso {receiver_pid} no encontrado. Terminando.")
                break
        
        if int(time.time() - start_time) % 3 == 0 and int(time.time() - start_time) % 3 != (int(time.time() - start_time) - 1) % 3:
            # Enviar SIGUSR2 cada 3 segundos (aproximadamente)
            try:
                os.kill(receiver_pid, signal.SIGUSR2)
                signal_count_usr2 += 1
                print(f"Emisor: Enviado SIGUSR2 a {receiver_pid}. Total SIGUSR2: {signal_count_usr2}")
            except ProcessLookupError:
                print(f"Emisor: Proceso {receiver_pid} no encontrado. Terminando.")
                break
        
        time.sleep(1) # Esperar 1 segundo para la siguiente iteración

    print(f"Emisor: Finalizado el envío de señales. Total SIGUSR1: {signal_count_usr1}, Total SIGUSR2: {signal_count_usr2}.")
    sys.exit(0)

if __name__ == "__main__":
    main_signal_sender()