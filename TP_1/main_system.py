import multiprocessing
import os
import time
import random
import datetime
import hashlib
import json
import statistics
import queue
import select

# --- Constantes y Configuraciones ---
NUM_SAMPLES = 60
WINDOW_SIZE = 30
PIPE_BUFFER_SIZE = 4096 
BLOCKCHAIN_FILE = "blockchain.json"

# --- Clase para el Bloque de la Cadena de Bloques ---
class Block:
    def __init__(self, timestamp, data, alert, prev_hash=''):
        self.timestamp = timestamp
        self.data = data
        self.alert = alert
        self.prev_hash = prev_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps(self.to_dict(include_hash=False), sort_keys=True)
        return hashlib.sha256((self.prev_hash + block_string).encode('utf-8')).hexdigest()

    def to_dict(self, include_hash=True):
        block_dict = {
            "timestamp": self.timestamp,
            "datos": self.data,
            "alerta": self.alert,
            "prev_hash": self.prev_hash
        }
        if include_hash:
            block_dict["hash"] = self.hash
        return block_dict

# --- Funciones de Blockchain ---
def load_blockchain():
    if os.path.exists(BLOCKCHAIN_FILE) and os.path.getsize(BLOCKCHAIN_FILE) > 0:
        with open(BLOCKCHAIN_FILE, 'r') as f:
            try:
                raw_blocks = json.load(f)
                blockchain = []
                for b_data in raw_blocks:
                    block = Block(
                        b_data["timestamp"],
                        b_data["datos"],
                        b_data["alerta"],
                        b_data["prev_hash"]
                    )
                    if block.hash != b_data["hash"]:
                        print(f"ADVERTENCIA: Hash del bloque {b_data['timestamp']} no coincide al cargar.")
                    blockchain.append(block)
                print(f"Cadena de bloques cargada con {len(blockchain)} bloques.")
                return blockchain
            except json.JSONDecodeError:
                print("ADVERTENCIA: Archivo blockchain.json corrupto o vacío. Iniciando cadena vacía.")
                return []
    return []

def save_blockchain(blockchain_list):
    with open(BLOCKCHAIN_FILE, 'w') as f:
        json.dump([b.to_dict() for b in blockchain_list], f, indent=4)

# --- Proceso Principal (Generador de Datos) ---
def data_generator(freq_pipe_w, pres_pipe_w, oxy_pipe_w, stop_event):
    pid = os.getpid()
    print(f"[Generador PID: {pid}] Iniciado.")

    for i in range(NUM_SAMPLES):
        if stop_event.is_set():
            print(f"[Generador PID: {pid}] Detenido por evento de stop.")
            break

        timestamp = datetime.datetime.now().isoformat(timespec='seconds')

        frecuencia = random.randint(60, 180)
        presion_sistolica = random.randint(110, 180)
        presion_diastolica = random.randint(70, 110)
        oxigeno = random.randint(90, 100)

        data = {
            "timestamp": timestamp,
            "frecuencia": frecuencia,
            "presion": [presion_sistolica, presion_diastolica],
            "oxigeno": oxigeno
        }

        data_str = json.dumps(data)

        try:
            os.write(freq_pipe_w, data_str.encode('utf-8'))
            os.write(pres_pipe_w, data_str.encode('utf-8'))
            os.write(oxy_pipe_w, data_str.encode('utf-8'))
            print(f"[Generador PID: {pid}] Enviado muestra {i+1}/{NUM_SAMPLES} ({timestamp}).")
        except BrokenPipeError:
            print(f"[Generador PID: {pid}] Error: Pipe roto. El receptor pudo haber terminado.")
            break
        except Exception as e:
            print(f"[Generador PID: {pid}] Error al escribir en pipe: {e}")
            break

        time.sleep(1)

    print(f"[Generador PID: {pid}] Finalizado. Cerrando pipes de escritura.")
    os.close(freq_pipe_w)
    os.close(pres_pipe_w)
    os.close(oxy_pipe_w)


# --- Proceso Analizador (Genérico) ---
def analyzer_process(pipe_r, result_queue, analysis_type, stop_event):
    pid = os.getpid()
    print(f"[Analizador {analysis_type.capitalize()} PID: {pid}] Iniciado.")

    data_window = [] # Ventana móvil de los últimos 30 segundos
    
    # Hacer el pipe no bloqueante para el select, aunque os.read() sigue siendo bloqueante.
    # select.select es lo que nos permite el timeout.
    
    while True: # Loop infinito, la salida se controla con break
        # Prioridad 1: ¿Debería terminar?
        if stop_event.is_set():
            print(f"[Analizador {analysis_type.capitalize()} PID: {pid}] Detenido por evento de stop.")
            break # Sale del bucle si el evento está seteado

        # Prioridad 2: ¿Hay datos disponibles para leer en el pipe?
        # select.select monitorea el pipe_r para lectura, con un timeout.
        # Si pipe_r está listo para leer en 0.1 segundos, ready_to_read contendrá [pipe_r].
        # Si no, estará vacío.
        ready_to_read, _, _ = select.select([pipe_r], [], [], 0.1) # Timeout de 0.1 segundos

        if ready_to_read: # Si hay datos disponibles
            try:
                data_str = os.read(pipe_r, PIPE_BUFFER_SIZE).decode('utf-8')

                if not data_str: # Pipe cerrado por el escritor (EOF)
                    print(f"[Analizador {analysis_type.capitalize()} PID: {pid}] Pipe cerrado por el generador (EOF).")
                    break # Sale del bucle

                full_data = json.loads(data_str)
                current_timestamp = full_data["timestamp"]

                signal_value = None
                if analysis_type == "frecuencia":
                    signal_value = full_data["frecuencia"]
                elif analysis_type == "presion":
                    signal_value = full_data["presion"][0]
                elif analysis_type == "oxigeno":
                    signal_value = full_data["oxigeno"]
                
                if signal_value is not None:
                    data_window.append(signal_value)
                    if len(data_window) > WINDOW_SIZE:
                        data_window.pop(0)

                    media = 0
                    desv = 0
                    if len(data_window) > 1:
                        media = statistics.mean(data_window)
                        desv = statistics.stdev(data_window)
                    elif len(data_window) == 1:
                        media = data_window[0]
                        desv = 0

                    result = {
                        "tipo": analysis_type,
                        "timestamp": current_timestamp,
                        "media": round(media, 2),
                        "desv": round(desv, 2)
                    }
                    
                    result_queue.put(result)
                    print(f"[Analizador {analysis_type.capitalize()} PID: {pid}] Procesado {current_timestamp}. Media: {result['media']:.2f}")

            except json.JSONDecodeError:
                print(f"[Analizador {analysis_type.capitalize()} PID: {pid}] Error de JSON al leer del pipe. Datos recibidos: {data_str[:50]}...")
            except BrokenPipeError:
                print(f"[Analizador {analysis_type.capitalize()} PID: {pid}] Error: Pipe roto. El generador pudo haber terminado.")
                break
            except Exception as e:
                print(f"[Analizador {analysis_type.capitalize()} PID: {pid}] Error inesperado: {e}")
                break
        else:
            # Si no hay datos listos, el select.select() ya esperó el timeout.
            pass # El bucle volverá a empezar y chequeará el stop_event.

    print(f"[Analizador {analysis_type.capitalize()} PID: {pid}] Finalizado. Cerrando pipe de lectura.")
    os.close(pipe_r)


# --- Proceso Verificador ---
def verifier_process(freq_q, pres_q, oxy_q, stop_event, blockchain_lock):
    pid = os.getpid()
    print(f"[Verificador PID: {pid}] Iniciado.")

    blockchain = load_blockchain()
    processed_timestamps = {}

    while not stop_event.is_set() or any(q.qsize() > 0 for q in [freq_q, pres_q, oxy_q]):
        try:
            result_freq = freq_q.get(timeout=0.1) # Timeout más pequeño para mayor reactividad
            
            timestamp = result_freq["timestamp"]
            if timestamp not in processed_timestamps:
                processed_timestamps[timestamp] = {}
            processed_timestamps[timestamp][result_freq["tipo"]] = result_freq

            timeout_per_block = 2
            end_time = time.time() + timeout_per_block
            while len(processed_timestamps[timestamp]) < 3 and time.time() < end_time:
                try:
                    result = freq_q.get_nowait()
                    processed_timestamps[timestamp][result["tipo"]] = result
                except queue.Empty:
                    pass
                try:
                    result = pres_q.get_nowait()
                    processed_timestamps[timestamp][result["tipo"]] = result
                except queue.Empty:
                    pass
                try:
                    result = oxy_q.get_nowait()
                    processed_timestamps[timestamp][result["tipo"]] = result
                except queue.Empty:
                    pass
                time.sleep(0.01)
            
            if len(processed_timestamps[timestamp]) == 3:
                all_results = processed_timestamps.pop(timestamp)
                
                alert = False
                freq_data = all_results["frecuencia"]
                pres_data = all_results["presion"]
                oxy_data = all_results["oxigeno"]

                if freq_data["media"] >= 200:
                    alert = True
                    print(f"[{timestamp}] ALERTA: Frecuencia media ({freq_data['media']}) fuera de rango.")
                if not (90 <= oxy_data["media"] <= 100):
                    alert = True
                    print(f"[{timestamp}] ALERTA: Oxígeno medio ({oxy_data['media']}) fuera de rango.")
                if pres_data["media"] >= 200:
                    alert = True
                    print(f"[{timestamp}] ALERTA: Presión sistólica media ({pres_data['media']}) fuera de rango.")

                prev_hash = blockchain[-1].hash if blockchain else "0" * 64
                
                block_data = {
                    "frecuencia": {"media": freq_data["media"], "desv": freq_data["desv"]},
                    "presion": {"media": pres_data["media"], "desv": pres_data["desv"]},
                    "oxigeno": {"media": oxy_data["media"], "desv": oxy_data["desv"]}
                }
                
                new_block = Block(timestamp, block_data, alert, prev_hash)
                
                with blockchain_lock:
                    blockchain.append(new_block)
                    save_blockchain(blockchain)
                
                print(f"\n[Verificador PID: {pid}] Bloque {len(blockchain)-1} encadenado. Hash: {new_block.hash[:10]}... Alerta: {new_block.alert}")
            elif timestamp in processed_timestamps:
                missing = [t for t in ["frecuencia", "presion", "oxigeno"] if t not in processed_timestamps[timestamp]]
                print(f"[Verificador PID: {pid}] ADVERTENCIA: Timeout para timestamp {timestamp}. Faltan resultados para: {missing}. Descartando.")
                processed_timestamps.pop(timestamp)
                
        except queue.Empty:
            if not stop_event.is_set():
                time.sleep(0.05)
            else:
                pass
        except Exception as e:
            print(f"[Verificador PID: {pid}] Error en el verificador: {e}")
            break
    
    print(f"[Verificador PID: {pid}] Finalizado. Última cadena de bloques guardada.")


# --- Función Principal para llamar a funciones ---
def main_system():
    if os.path.exists(BLOCKCHAIN_FILE):
        os.remove(BLOCKCHAIN_FILE)
        print(f"Limpiado archivo de blockchain: {BLOCKCHAIN_FILE}")

    freq_pipe_r, freq_pipe_w = os.pipe()
    pres_pipe_r, pres_pipe_w = os.pipe()
    oxy_pipe_r, oxy_pipe_w = os.pipe()

    freq_queue = multiprocessing.Queue()
    pres_queue = multiprocessing.Queue()
    oxy_queue = multiprocessing.Queue()

    stop_event = multiprocessing.Event()
    blockchain_lock = multiprocessing.Lock()

    processes = []

    generator_p = multiprocessing.Process(
        target=data_generator,
        args=(freq_pipe_w, pres_pipe_w, oxy_pipe_w, stop_event),
        name="GeneratorProcess"
    )
    processes.append(generator_p)

    analyzer_freq_p = multiprocessing.Process(
        target=analyzer_process,
        args=(freq_pipe_r, freq_queue, "frecuencia", stop_event),
        name="FreqAnalyzerProcess"
    )
    processes.append(analyzer_freq_p)

    analyzer_pres_p = multiprocessing.Process(
        target=analyzer_process,
        args=(pres_pipe_r, pres_queue, "presion", stop_event),
        name="PresAnalyzerProcess"
    )
    processes.append(analyzer_pres_p)

    analyzer_oxy_p = multiprocessing.Process(
        target=analyzer_process,
        args=(oxy_pipe_r, oxy_queue, "oxigeno", stop_event),
        name="OxyAnalyzerProcess"
    )
    processes.append(analyzer_oxy_p)

    verifier_p = multiprocessing.Process(
        target=verifier_process,
        args=(freq_queue, pres_queue, oxy_queue, stop_event, blockchain_lock),
        name="VerifierProcess"
    )
    processes.append(verifier_p)

    for p in processes:
        p.start()

    generator_p.join()
    print("[Main] Generador ha terminado. Señalizando a otros procesos para terminar.")

    # Dar un tiempo prudencial para que los analizadores y el verificador procesen lo último
    # antes de forzar el cierre.
    time.sleep(3)

    # CERRAR LOS EXTREMOS DE ESCRITURA DE LOS PIPES EN EL PROCESO PADRE
    try:
        os.close(freq_pipe_w)
        os.close(pres_pipe_w)
        os.close(oxy_pipe_w)
        print("[Main] Pipes de escritura del padre cerrados.")
    except OSError as e:
        print(f"[Main] Error al cerrar pipes de escritura en el padre (posiblemente ya cerrados): {e}")

    # Señalizar a los procesos restantes que deben terminar
    stop_event.set()
    print("[Main] Evento de stop enviado.")

    # Esperar a que todos los procesos terminen
    for p in processes:
        p.join(timeout=15)
        if p.is_alive():
            print(f"[Main] ADVERTENCIA: Proceso {p.name} (PID: {p.pid}) NO TERMINÓ después del join. Forzando terminación.")
            # Si el proceso sigue vivo, es probable que esté bloqueado en I/O.
            p.terminate() # <-- Intentar terminar si persiste el problema
            p.join() # Esperar a que la terminación se complete
        else:
            print(f"[Main] Proceso {p.name} (PID: {p.pid}) finalizado.")

    print("[Main] Todos los procesos han terminado o se ha superado el tiempo de espera. Recursos limpiados.")

if __name__ == "__main__":
    main_system()