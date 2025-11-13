import json
import hashlib
import os
import datetime
import statistics

BLOCKCHAIN_FILE = "blockchain.json"
REPORT_FILE = "reporte.txt"

def calculate_hash(block_data, prev_hash):
    """
    Recalcula el hash de un bloque dado sus datos y el hash previo.
    Debe ser idéntica a la función calculate_hash en main_system.py
    """
    block_string = json.dumps(block_data, sort_keys=True)
    return hashlib.sha256((prev_hash + block_string).encode('utf-8')).hexdigest()

def verify_blockchain():
    print(f"--- Verificación de Cadena de Bloques ({BLOCKCHAIN_FILE}) ---")
    if not os.path.exists(BLOCKCHAIN_FILE):
        print(f"Error: El archivo '{BLOCKCHAIN_FILE}' no existe.")
        return

    blockchain = []
    try:
        with open(BLOCKCHAIN_FILE, 'r') as f:
            blockchain = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: El archivo '{BLOCKCHAIN_FILE}' no es un JSON válido o está vacío.")
        return

    total_blocks = len(blockchain)
    corrupted_blocks = 0
    alert_blocks = 0

    # Para el promedio general
    all_frecuencias = []
    all_presiones_sistolicas = []
    all_oxigenos = []

    print(f"Total de bloques encontrados: {total_blocks}")

    for i, block in enumerate(blockchain):
        # 1. Verificar prev_hash
        expected_prev_hash = blockchain[i-1]["hash"] if i > 0 else "0" * 64
        if block["prev_hash"] != expected_prev_hash:
            print(f"Bloque {i}: ¡CORRUPCIÓN DETECTADA! prev_hash incorrecto.")
            print(f"  Esperado: {expected_prev_hash[:10]}..., Encontrado: {block['prev_hash'][:10]}...")
            corrupted_blocks += 1

        # 2. Recalcular y verificar hash propio
        # Crear un diccionario para el cálculo del hash, excluyendo el campo 'hash'
        block_data_for_hash = {
            "timestamp": block["timestamp"],
            "datos": block["datos"],
            "alerta": block["alerta"],
            "prev_hash": block["prev_hash"]
        }
        recalculated_hash = calculate_hash(block_data_for_hash, block["prev_hash"])
        
        if block["hash"] != recalculated_hash:
            print(f"Bloque {i}: ¡CORRUPCIÓN DETECTADA! Hash recalculado no coincide.")
            print(f"  Esperado: {block['hash'][:10]}..., Recalculado: {recalculated_hash[:10]}...")
            corrupted_blocks += 1

        # 3. Contar alertas
        if block.get("alerta", False): # Usar .get para manejar si el campo falta por alguna razón
            alert_blocks += 1

        # 4. Recopilar datos para promedios
        try:
            all_frecuencias.append(block["datos"]["frecuencia"]["media"])
            all_presiones_sistolicas.append(block["datos"]["presion"]["media"])
            all_oxigenos.append(block["datos"]["oxigeno"]["media"])
        except KeyError as e:
            print(f"Advertencia: Bloque {i} falta campo de datos para promedio: {e}")

    # Calcular promedios generales
    avg_frecuencia = statistics.mean(all_frecuencias) if all_frecuencias else 0
    avg_presion = statistics.mean(all_presiones_sistolicas) if all_presiones_sistolicas else 0
    avg_oxigeno = statistics.mean(all_oxigenos) if all_oxigenos else 0

    # Generar reporte final
    with open(REPORT_FILE, 'w') as f:
        f.write(f"--- Reporte de Análisis Biométrico ---\n")
        f.write(f"Fecha del Reporte: {datetime.datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"Archivo de Cadena de Bloques: {BLOCKCHAIN_FILE}\n\n")
        f.write(f"Cantidad total de bloques: {total_blocks}\n")
        f.write(f"Número de bloques con alertas: {alert_blocks}\n")
        f.write(f"Número de bloques corruptos detectados: {corrupted_blocks}\n\n")
        f.write(f"Promedio general de Frecuencia: {avg_frecuencia:.2f}\n")
        f.write(f"Promedio general de Presión Sistólica: {avg_presion:.2f}\n")
        f.write(f"Promedio general de Oxígeno: {avg_oxigeno:.2f}\n")
        f.write(f"----------------------------------------\n")

    print(f"\nVerificación completada. {corrupted_blocks} bloques corruptos encontrados.")
    print(f"Reporte generado en '{REPORT_FILE}'.")

if __name__ == "__main__":
    verify_blockchain()