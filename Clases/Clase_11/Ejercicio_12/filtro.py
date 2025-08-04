import argparse
import sys

def filtro_script():
    parser = argparse.ArgumentParser(description="Filtra números mayores que un umbral.")
    parser.add_argument("--min", type=int, default=50, help="Umbral mínimo para los números.")
    args = parser.parse_args()

    print(f"Filtrando números mayores que {args.min} (recibiendo de stdin)...")
    for line in sys.stdin: # Leer desde la entrada estándar
        try:
            number = int(line.strip()) # Convertir la línea a entero
            if number > args.min:
                print(number) # Imprimir solo los números que cumplen la condición
        except ValueError:
            # Ignorar líneas que no sean números
            sys.stderr.write(f"Advertencia: Ignorando línea no numérica: '{line.strip()}'\n")

if __name__ == "__main__":
    filtro_script()