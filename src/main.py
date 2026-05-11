import sys
import os

from lexer import lexer
from parser import parser, SintaxError
from semantic import SemanticAnalyzer, SemanticError
from optimizer import Optimizer
from codegen import CodeGenerator
from utils.errors import Errors

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print("Uso: python3 src/main.py <input_file> [opções]")
        print("\nOpções:")
        print("  -o, --output <file>  : Nome do ficheiro de saída para o código VM (default: <input_file>.vm)")
        print("  --no-opt             : Desativa todas as otimizações.")
        print("  --no-warn            : Suprime todos os avisos.")
        print("\nExemplo: python3 src/main.py tests/exemplo1.f -o out.vm")
        sys.exit(0)

    input_file = sys.argv[1]
    output_file = None
    no_opt = False
    no_warn = False

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['-o', '--output']:
            if i + 1 < len(sys.argv):
                output_file = sys.argv[i+1]
                i += 2
            else:
                print(f"Erro: A flag '{arg}' requer um nome de ficheiro.")
                sys.exit(1)
        elif arg == '--no-opt':
            no_opt = True
            i += 1
        elif arg == '--no-warn':
            no_warn = True
            i += 1
        else:
            print(f"Aviso: Argumento desconhecido '{arg}' ignorado.")
            i += 1

    if not output_file:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}.vm"

    if no_warn:
        Errors.FLAG_WARNINGS = False

    try:
        with open(input_file, 'r') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Erro: Ficheiro de entrada '{input_file}' não encontrado.")
        sys.exit(1)

    print(f"A compilar '{input_file}'...")

    # --- Análise Léxica ---
    lexer.lineno = 1
    lexer.line_start = 0
    lexer.error_count = 0
    lexer.input(code)
    while True:
        tok = lexer.token()
        if not tok:
            break
    if lexer.error_count > 0:
        print(f"Compilação falhou com {lexer.error_count} erro(s) léxico(s).")
        sys.exit(1)
    print("  ✓ Análise Léxica concluída.")

    # --- Análise Sintática ---
    ast = None
    try:
        # Reinicializa o mesmo lexer para o parser, pois ele foi consumido na fase anterior.
        lexer.lineno = 1
        lexer.line_start = 0
        lexer.input(code) # O mais importante: reposiciona o lexer no início do código.
        ast = parser.parse(code, lexer=lexer)
    except SintaxError as e:
        print(e) # A exceção já vem formatada
        print("Compilação falhou devido a um erro sintático.")
        sys.exit(1)
    
    if not ast:
        print("Compilação falhou na análise sintática (AST vazia).")
        sys.exit(1)
    print("  ✓ Análise Sintática concluída.")

    # --- Análise Semântica ---
    analyzer = SemanticAnalyzer()
    if not analyzer.analyze(ast):
        print(f"Compilação falhou com {len(analyzer.errors)} erro(s) semântico(s).")
        sys.exit(1)
    print("  ✓ Análise Semântica concluída.")

    # --- Otimização ---
    opt_ast = ast
    if not no_opt:
        optimizer = Optimizer(analyzer.symbol_table, analyzer.goto_labels.union(analyzer.do_labels))
        opt_ast = optimizer.optimize(ast)
        optimizer.report()
        print("  ✓ Otimização concluída.")
    else:
        print("  - Otimização desativada.")

    # --- Geração de Código ---
    generator = CodeGenerator(analyzer.symbol_table, analyzer.goto_labels)
    vm_code = generator.generate(opt_ast)
    if not vm_code:
        print("Compilação falhou na geração de código.")
        sys.exit(1)
    print("  ✓ Geração de Código concluída.")

    try:
        with open(output_file, 'w', newline='\n') as f:
            clean_code = [line.replace('\r', '').strip() for line in vm_code if line.strip()]
            f.write('\n'.join(clean_code))
    except IOError as e:
        print(f"Erro ao escrever no ficheiro de saída '{output_file}': {e}")
        sys.exit(1)

    print(f"\nCompilação bem-sucedida! Código VM guardado em '{output_file}'.")

if __name__ == '__main__':
    main()
