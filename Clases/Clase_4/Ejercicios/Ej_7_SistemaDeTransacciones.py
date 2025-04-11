# Implementa un sistema donde múltiples procesos "generadores" crean transacciones (operaciones con un ID, tipo y monto), las envían a un proceso "validador" que verifica su integridad, y finalmente a un proceso "registrador" que acumula las estadísticas. Usa múltiples pipes para manejar este flujo complejo y asegúrate de manejar correctamente la sincronización y el cierre de la comunicación.

import os
import sys
import time
import random
import json
from collections import defaultdict

# Estructura para representar una transacción
class Transaction:
    def __init__(self, id=None, tipo=None, monto=None):
        self.id = id or random.randint(1000, 9999)
        self.tipo = tipo or random.choice(["deposito", "retiro", "transferencia", "pago"])
        self.monto = monto or round(random.uniform(10.0, 1000.0), 2)
    
    def to_json(self):
        """Convierte la transacción a formato JSON para transmisión"""
        return json.dumps({
            "id": self.id,
            "tipo": self.tipo,
            "monto": self.monto
        })
    
    @classmethod
    def from_json(cls, json_str):
        """Crea una transacción desde una cadena JSON"""
        try:
            data = json.loads(json_str)
            return cls(data["id"], data["tipo"], data["monto"])
        except Exception as e:
            print(f"Error al deserializar transacción: {e}")
            return None
    
    def __str__(self):
        return f"Transacción #{self.id}: {self.tipo} ${self.monto:.2f}"

def generator_process(name, write_pipe, num_transactions):
    """
    Proceso generador que crea transacciones aleatorias
    y las envía al validador.
    """
    try:
        with os.fdopen(write_pipe, 'w') as pipe:
            print(f"Generador {name}: Iniciando generación de {num_transactions} transacciones")
            
            for i in range(num_transactions):
                # Crear una transacción aleatoria
                transaction = Transaction()
                
                # Enviarla al validador
                pipe.write(transaction.to_json() + "\n")
                pipe.flush()
                
                print(f"Generador {name}: Enviada {transaction}")
                
                # Pequeña pausa aleatoria
                time.sleep(random.uniform(0.3, 0.8))
            
            # Enviar señal de finalización
            pipe.write("END\n")
            pipe.flush()
            print(f"Generador {name}: Finalizando")
            
    except Exception as e:
        print(f"Error en generador {name}: {e}")

def validator_process(read_pipes, write_pipe):
    """
    Proceso validador que recibe transacciones de múltiples generadores,
    verifica su validez y las pasa al registrador.
    """
    try:
        # Abrir todos los pipes de lectura y el pipe de escritura
        readers = [os.fdopen(pipe, 'r') for pipe in read_pipes]
        writer = os.fdopen(write_pipe, 'w')
        
        active_readers = len(readers)
        transactions_processed = 0
        transactions_valid = 0
        transactions_invalid = 0
        
        print(f"Validador: Iniciando con {active_readers} generadores")
        
        # Procesar mientras haya generadores activos
        while active_readers > 0:
            for i, reader in enumerate(readers):
                if reader is None:
                    continue  # Saltear pipes cerrados
                
                # Leer una línea (no bloqueante)
                line = reader.readline().strip()
                
                if not line:
                    continue  # No hay datos disponibles, continuar
                
                if line == "END":
                    print(f"Validador: Generador {i} ha terminado")
                    readers[i] = None  # Marcar el reader como inactivo
                    active_readers -= 1
                    continue
                
                # Procesar la transacción
                transactions_processed += 1
                
                try:
                    # Deserializar la transacción
                    transaction = Transaction.from_json(line)
                    
                    # Validar la transacción (reglas de ejemplo)
                    valid = True
                    error_msg = None
                    
                    if transaction.monto <= 0:
                        valid = False
                        error_msg = "Monto debe ser positivo"
                    elif transaction.tipo == "retiro" and transaction.monto > 500:
                        valid = False
                        error_msg = "Retiros no pueden exceder $500"
                    
                    # Enviar al registrador (con resultado de validación)
                    result = {
                        "transaction": transaction.__dict__,
                        "valid": valid,
                        "error": error_msg,
                        "timestamp": time.time()
                    }
                    
                    writer.write(json.dumps(result) + "\n")
                    writer.flush()
                    
                    if valid:
                        transactions_valid += 1
                        print(f"Validador: Transacción #{transaction.id} válida")
                    else:
                        transactions_invalid += 1
                        print(f"Validador: Transacción #{transaction.id} inválida: {error_msg}")
                
                except Exception as e:
                    print(f"Validador: Error procesando transacción: {e}")
            
            # Pequeña pausa para no saturar la CPU
            time.sleep(0.1)
        
        # Enviar estadísticas finales al registrador
        stats = {
            "final_stats": True,
            "processed": transactions_processed,
            "valid": transactions_valid,
            "invalid": transactions_invalid
        }
        
        writer.write(json.dumps(stats) + "\n")
        writer.flush()
        writer.write("END\n")
        writer.flush()
        
        print(f"Validador: Finalizado. Procesadas {transactions_processed} transacciones")
        
    except Exception as e:
        print(f"Error en validador: {e}")
    finally:
        # Cerrar todos los pipes
        for reader in readers:
            if reader is not None:
                reader.close()
        writer.close()

def logger_process(read_pipe):
    """
    Proceso registrador que recibe transacciones validadas
    y mantiene estadísticas.
    """
    try:
        # Estadísticas
        stats = {
            "total_valid": 0,
            "total_invalid": 0,
            "total_amount": 0,
            "by_type": defaultdict(int),
            "by_type_amount": defaultdict(float)
        }
        
        transactions = []
        
        with os.fdopen(read_pipe, 'r') as reader:
            print("Registrador: Iniciando registro de transacciones")
            
            while True:
                line = reader.readline().strip()
                
                if not line:
                    continue
                
                if line == "END":
                    break
                
                data = json.loads(line)
                
                # Verificar si son estadísticas finales
                if data.get("final_stats"):
                    print("\nRegistrador: Recibidas estadísticas finales del validador:")
                    print(f"  Total procesadas: {data['processed']}")
                    print(f"  Válidas: {data['valid']}")
                    print(f"  Inválidas: {data['invalid']}")
                    continue
                
                # Procesar la transacción validada
                transaction = data["transaction"]
                valid = data["valid"]
                
                if valid:
                    stats["total_valid"] += 1
                    stats["total_amount"] += transaction["monto"]
                    stats["by_type"][transaction["tipo"]] += 1
                    stats["by_type_amount"][transaction["tipo"]] += transaction["monto"]
                    
                    # Guardar para resumen final
                    transactions.append(transaction)
                else:
                    stats["total_invalid"] += 1
                
                # Mostrar progreso
                total = stats["total_valid"] + stats["total_invalid"]
                if total % 5 == 0:  # Mostrar cada 5 transacciones
                    print(f"Registrador: Procesadas {total} transacciones hasta ahora")
            
            # Mostrar resumen final
            print("\n===== RESUMEN FINAL DE TRANSACCIONES =====")
            print(f"Total de transacciones válidas: {stats['total_valid']}")
            print(f"Total de transacciones inválidas: {stats['total_invalid']}")
            print(f"Monto total procesado: ${stats['total_amount']:.2f}")
            
            print("\nTransacciones por tipo:")
            for tipo, count in stats["by_type"].items():
                amount = stats["by_type_amount"][tipo]
                print(f"  {tipo.capitalize()}: {count} transacciones, ${amount:.2f}")
            
            # Mostrar las 5 transacciones más grandes
            if transactions:
                print("\nTop 5 transacciones por monto:")
                top_transactions = sorted(transactions, key=lambda x: x["monto"], reverse=True)[:5]
                for i, t in enumerate(top_transactions, 1):
                    print(f"  {i}. #{t['id']} ({t['tipo']}): ${t['monto']:.2f}")
            
            print("==========================================")
            
    except Exception as e:
        print(f"Error en registrador: {e}")

def main():
    # Número de generadores
    num_generators = 3
    
    # Pipes para comunicación generadores -> validador
    gen_to_val_pipes = []
    for i in range(num_generators):
        r, w = os.pipe()
        gen_to_val_pipes.append((r, w))
    
    # Pipe para comunicación validador -> registrador
    val_to_log_r, val_to_log_w = os.pipe()
    
    # Crear procesos generadores
    generator_pids = []
    for i in range(num_generators):
        pid = os.fork()
        
        if pid == 0:  # Proceso hijo (generador)
            # Cerrar todos los pipes excepto el de escritura de este generador
            for j, (r, w) in enumerate(gen_to_val_pipes):
                if j != i:
                    os.close(r)
                    os.close(w)
                else:
                    os.close(r)  # Solo necesitamos el extremo de escritura
            
            # Cerrar el pipe validador -> registrador
            os.close(val_to_log_r)
            os.close(val_to_log_w)
            
            # Ejecutar el proceso generador
            generator_process(f"G{i+1}", gen_to_val_pipes[i][1], 
                            random.randint(8, 15))  # Generar entre 8-15 transacciones
            
            # Salir del proceso hijo
            sys.exit(0)
        
        generator_pids.append(pid)
    
    # Crear proceso validador
    val_pid = os.fork()
    
    if val_pid == 0:  # Proceso hijo (validador)
        # Cerrar extremos no utilizados de los pipes generador -> validador
        for r, w in gen_to_val_pipes:
            os.close(w)  # Solo necesitamos los extremos de lectura
        
        # Cerrar extremo de lectura del pipe validador -> registrador
        os.close(val_to_log_r)
        
        # Ejecutar el proceso validador
        validator_process([r for r, _ in gen_to_val_pipes], val_to_log_w)
        
        # Salir del proceso hijo
        sys.exit(0)
    
    # Crear proceso registrador
    log_pid = os.fork()
    
    if log_pid == 0:  # Proceso hijo (registrador)
        # Cerrar todos los pipes generador -> validador
        for r, w in gen_to_val_pipes:
            os.close(r)
            os.close(w)
        
        # Cerrar extremo de escritura del pipe validador -> registrador
        os.close(val_to_log_w)
        
        # Ejecutar el proceso registrador
        logger_process(val_to_log_r)
        
        # Salir del proceso hijo
        sys.exit(0)
    
    # Proceso principal: cerrar todos los pipes
    for r, w in gen_to_val_pipes:
        os.close(r)
        os.close(w)
    
    os.close(val_to_log_r)
    os.close(val_to_log_w)
    
    # Esperar a que todos los procesos terminen
    for pid in generator_pids:
        os.waitpid(pid, 0)
    
    os.waitpid(val_pid, 0)
    os.waitpid(log_pid, 0)
    
    print("Sistema de procesamiento de transacciones completado.")

if __name__ == "__main__":
    main()