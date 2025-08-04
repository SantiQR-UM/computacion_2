import argparse
import random

def generador_script():
    parser = argparse.ArgumentParser(description="Genera números aleatorios.")
    parser.add_argument("--n", type=int, default=10, help="Número de enteros aleatorios a generar.")
    args = parser.parse_args()

    print(f"Generando {args.n} números aleatorios...")
    for _ in range(args.n):
        number = random.randint(1, 100) # Números entre 1 y 100
        print(number) # Imprime cada número en una nueva línea

if __name__ == "__main__":
    generador_script()