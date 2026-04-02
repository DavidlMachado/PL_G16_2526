import sys
from lexer import lexer

# Este ficheiro é temporário e apenas para testar o lexer 

def run_test(filename):
    try:
        with open(filename, 'r') as f:
            data = f.read()
            lexer.input(data)
            
            print(f"--- Tokens para o ficheiro: {filename} ---")
            for tok in lexer:
                # Imprime o tipo, o valor, a linha e a posição
                print(f"Type: {tok.type:12} | Value: {str(tok.value):15} | Line: {tok.lineno}")
            print("-" * 40)
    
           
    except FileNotFoundError:
        print(f"Erro: O ficheiro {filename} não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro durante o teste: {e}")

if __name__ == "__main__":
    # Se passares o nome do ficheiro pelo terminal, ele testa esse.
    # Exemplo: python3 src/test_lexer.py tests/exemplo1.f
    if len(sys.argv) > 1:
        run_test(sys.argv[1])
    else:
        print("Uso: python3 src/test_lexer.py <caminho_do_ficheiro>")