import multiprocessing
import time
import random

class BankAccount:
    def __init__(self):
        self.balance = multiprocessing.Value('d', 0.0) # 'd' para float
        self.lock = multiprocessing.RLock() # Usamos RLock

    def _log_transaction(self, amount, type):
        """Método interno para registrar la transacción."""
        with self.lock: # Este método también adquiere el lock
            print(f"[{multiprocessing.current_process().name}] -> Log: {type} {amount:.2f}, Saldo actual: {self.balance.value:.2f}")

    def deposit(self, amount):
        with self.lock: # Adquirir el lock
            print(f"[{multiprocessing.current_process().name}] Depositando {amount:.2f}...")
            # Llamada recursiva a otro método sincronizado
            self._log_transaction(amount, "Deposito") 
            self.balance.value += amount
            print(f"[{multiprocessing.current_process().name}] Saldo después del depósito: {self.balance.value:.2f}")

    def withdraw(self, amount):
        with self.lock: # Adquirir el lock
            print(f"[{multiprocessing.current_process().name}] Retirando {amount:.2f}...")
            if self.balance.value >= amount:
                # Llamada recursiva a otro método sincronizado
                self._log_transaction(amount, "Retiro") 
                self.balance.value -= amount
                print(f"[{multiprocessing.current_process().name}] Saldo después del retiro: {self.balance.value:.2f}")
            else:
                print(f"[{multiprocessing.current_process().name}] Fondos insuficientes para retirar {amount:.2f}. Saldo: {self.balance.value:.2f}")

def simulate_transactions(account, transactions_per_process):
    process_name = multiprocessing.current_process().name
    print(f"{process_name} iniciando transacciones.")
    for _ in range(transactions_per_process):
        amount = random.uniform(10, 100)
        if random.random() < 0.7: # 70% de probabilidad de depósito
            account.deposit(amount)
        else: # 30% de probabilidad de retiro
            account.withdraw(amount)
        time.sleep(random.uniform(0.01, 0.1)) # Pequeña pausa

    print(f"{process_name} finalizando transacciones.")

def main_r_lock():
    print("--- Demostración de RLock (Cuenta Bancaria) ---")
    
    account = BankAccount()
    num_processes = 3
    transactions_per_process = 5

    processes = []
    print(f"Creando {num_processes} procesos para simular transacciones en la cuenta bancaria...")
    
    for i in range(num_processes):
        p = multiprocessing.Process(name=f"Proceso-{i+1}", target=simulate_transactions, args=(account, transactions_per_process))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    print(f"\nSaldo final de la cuenta: {account.balance.value:.2f}")
    print("Todos los procesos han terminado. Demostración de RLock finalizada.")
    print("-" * 50)

if __name__ == "__main__":
    main_r_lock()