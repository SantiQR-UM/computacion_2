import argparse

# Creamos un parser
parser = argparse.ArgumentParser(description='Process input and output files.')

# Definimos los argumentos
parser.add_argument('-i', '--input', type=str, required=True, help='Input file')
parser.add_argument('-o', '--output', type=str, required=True, help='Output file')

# Parseamos los argumentos
try:
	args = parser.parse_args()
except Exception as error:
	print(str(error))
	sys.exit(2)

print(f'Input file: {args.input}')
print(f'Output file: {args.output}')
