import ply.yacc as yacc
from lexer import tokens, lexer # tokens para o yacc, lexer para testar no parse()

# --- Definição da Gramática e Precedência ---

# A precedência dos operadores é crucial para resolver ambiguidades em expressões.
# Por exemplo, em "3 + 4 * 2", o "*" tem maior precedência que o "+",
# então a expressão é avaliada como "3 + (4 * 2)".
#
# A lista é definida do operador de menor precedência (no topo) para o de maior precedência (no fundo).
#
# - 'left': O operador agrupa da esquerda para a direita (ex: a - b - c é (a - b) - c).
# - 'right': O operador agrupa da direita para a esquerda (ex: a ** b ** c é a ** (b ** c)).
# - 'nonassoc': O operador não pode ser encadeado (ex: a < b < c é um erro).
#
# Os nomes dos tokens (OR, AND, etc.) devem corresponder aos definidos no lexer.py.
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    # Operadores relacionais são 'nonassoc' para evitar cadeias como 'a .LT. b .LT. c'
    # que são sintaticamente ambíguas ou sem sentido em Fortran 77.
    ('nonassoc', 'LT', 'LE', 'EQ', 'NE', 'GT', 'GE'),
    ('left', '+', '-'),
    ('left', '*', '/'),
    ('right', 'POW'),
    ('right', 'UMINUS'), # Operador unário menos
)

# Regra inicial
# Esta é a regra de topo da gramática. O parser tenta reduzir todo o código fonte a esta regra.
# Se conseguir, o programa é sintaticamente válido.
def p_program(p):
    """
    program : optional_program_statement declaration_section executable_section END
    """
    # p[0] é o valor de retorno desta regra, que será o nó raiz da nossa AST.
    # p[1], p[2], p[3], etc., correspondem aos símbolos à direita da regra na docstring.
    #
    # Exemplo:
    # p[1] -> resultado de 'optional_program_statement' (nome do programa ou None)
    # p[2] -> resultado de 'declaration_section' (lista de declarações)
    # p[3] -> resultado de 'executable_section' (lista de statements executáveis)
    # p[4] -> o token 'END'
    #
    # A AST é construída usando tuplos, onde o primeiro elemento é o tipo de nó
    # e os restantes são os seus filhos ou atributos.
    # Isso permite uma representação hierárquica do código.
    # Esta é a raiz da nossa Árvore Sintática Abstrata (AST)
    p[0] = ('PROGRAM', p[1], p[2], p[3])
    print("Programa Fortran reconhecido com sucesso!")

def p_optional_program_statement(p):
    """
    optional_program_statement : PROGRAM VAR
                               | empty
    """    
    # Verifica se a regra corresponde a 'PROGRAM VAR' (len(p) > 2) ou 'empty' (len(p) == 2).
    if len(p) > 2:
        # Se for 'PROGRAM VAR', p[2] é o nome da variável (o nome do programa).
        p[0] = p[2] 
    else:
        # Se for 'empty', significa que não há declaração de PROGRAM,
        # então o nome do programa é None.
        # A regra 'empty' é uma produção vazia, que permite que uma parte da gramática
        # seja opcional.
        p[0] = None # Programa sem nome

# Secções do programa
def p_declaration_section(p):
    """
    declaration_section : declaration_section declaration
                        | empty
    """    
    # Esta é uma regra recursiva para acumular declarações.
    # Se houver mais de uma declaração, p[1] será a lista de declarações anteriores
    # e p[2] será a declaração atual.
    if len(p) > 2:
        # Adiciona a nova declaração à lista existente.
        p[0] = p[1] + [p[2]]
    else:
        # Se for a primeira (ou única) declaração, ou se a secção for vazia,
        # inicia uma lista vazia.
        p[0] = []

def p_executable_section(p):
    """
    executable_section : executable_section statement
                       | empty
    """
    # Semelhante a 'declaration_section', esta regra acumula statements executáveis.
    # p[1] é a lista de statements anteriores, p[2] é o statement atual.
    if len(p) > 2:
        # Adiciona o novo statement à lista existente.
        p[0] = p[1] + [p[2]]
    else:
        # Se a secção for vazia, inicia uma lista vazia.
        p[0] = []

# --- Regras para Declarações ---

# Declarações de variáveis
def p_declaration(p):
    """
    declaration : type var_list
    """
    # Associa o tipo a cada variável na lista
    # p[1] é o tipo (ex: 'INTEGER'), p[2] é a lista de variáveis (ex: ['X', 'Y']).
    p[0] = (p[1], p[2])
    # Exemplo de AST: ('INTEGER', ['X', 'Y'])


def p_type(p):
    """
    type : INTEGER
         | REAL
         | LOGICAL
         | CHARACTER
    """
    # O valor do token (ex: 'INTEGER') é o próprio tipo.
    p[0] = p[1]

def p_var_list(p):
    """
    var_list : VAR
             | var_list ',' VAR
    """    
    # Regra recursiva para lidar com listas de variáveis separadas por vírgula.
    if len(p) == 2:
        # Caso base: apenas uma variável. Retorna uma lista com essa variável.
        # p[1] é o nome da variável (string).
        p[0] = [p[1]]
    else:
        # Caso recursivo: adiciona a nova variável (p[3]) à lista existente (p[1]).
        # p[1] é a lista de variáveis já processadas.
        # p[3] é o nome da nova variável.
        p[0] = p[1] + [p[3]]

# Statements executáveis
def p_statement(p):
    """
    statement : labeled_statement
              | unlabeled_statement
    """
    # Um statement pode ter um label ou não. Simplesmente passa o resultado adiante.
    p[0] = p[1]

def p_labeled_statement(p):
    """
    labeled_statement : INTVAL unlabeled_statement
    """
    # Um statement com label é representado por um tuplo ('LABEL', número_do_label, statement_real).
    # p[1] é o valor inteiro do label.
    # p[2] é o statement sem label que segue o número.
    # (label, statement)
    p[0] = ('LABEL', p[1], p[2])

def p_unlabeled_statement(p):
    """
    unlabeled_statement : assignment_statement
                        | if_statement
                        | do_statement
                        | goto_statement
                        | print_statement
                        | read_statement
                        | continue_statement
    """
    # Esta regra agrupa todos os tipos de statements que não têm um label.
    # Simplesmente passa o resultado do statement específico adiante.
    p[0] = p[1]

def p_assignment_statement(p):
    """
    assignment_statement : VAR '=' expression
    """
    # Representa uma atribuição: VAR = EXPRESSION.
    # p[1] é o nome da variável, p[3] é a expressão a ser atribuída.
    p[0] = ('ASSIGN', p[1], p[3])

def p_if_statement(p):
    """
    if_statement : IF '(' expression ')' THEN executable_section ENDIF
                 | IF '(' expression ')' THEN executable_section ELSE executable_section ENDIF
    """
    # Lida com IF-THEN e IF-THEN-ELSE.
    # A diferença é o número de elementos na regra (len(p)).
    if len(p) == 8: # IF-THEN
        # p[3] é a condição, p[6] é o bloco THEN.
        p[0] = ('IF', p[3], p[6])
    else: # IF-THEN-ELSE
        # p[3] é a condição, p[6] é o bloco THEN, p[8] é o bloco ELSE.
        p[0] = ('IF-ELSE', p[3], p[6], p[8])
    # Exemplo de AST: ('IF', (condição), [statement1, statement2])
    # Exemplo de AST: ('IF-ELSE', (condição), [then_stmt], [else_stmt])

def p_do_statement(p):
    """
    do_statement : DO INTVAL VAR '=' expression ',' expression
                 | DO INTVAL VAR '=' expression ',' expression ',' expression
    """
    # Lida com ciclos DO.
    # p[2] é o label de destino do DO (INTVAL).
    # p[3] é a variável de controlo (VAR).
    # p[5] é a expressão inicial.
    # p[7] é a expressão final.
    # p[9] (se existir) é a expressão do passo (step).
    if len(p) == 8: # Sem step
        # Se não houver step explícito, o Fortran 77 assume 1.
        p[0] = ('DO', p[2], p[3], p[5], p[7], ('CONST', 'INT', 1)) # Step default é 1
    else: # Com step
        # Com step explícito.
        p[0] = ('DO', p[2], p[3], p[5], p[7], p[9])
    # Exemplo de AST: ('DO', label, 'I', (expr_inicio), (expr_fim), (expr_step))

def p_goto_statement(p):
    """
    goto_statement : GOTO INTVAL
    """
    # Representa um GOTO para um label específico.
    # p[2] é o valor inteiro do label.
    p[0] = ('GOTO', p[2])

def p_continue_statement(p):
    """
    continue_statement : CONTINUE
    """
    # O statement CONTINUE não tem argumentos.
    p[0] = ('CONTINUE',)

def p_print_statement(p):
    """
    print_statement : PRINT '*' ',' expression_list
    """
    p[0] = ('PRINT', p[4])
    # p[4] é a lista de expressões a serem impressas.
    # Exemplo de código: PRINT *, 'RESULT:', X, 10
    # Exemplo de AST: ('PRINT', [('CONST', 'STRING', 'RESULT:'), ('VAR', 'X'), ('CONST', 'INT', 10)])

def p_read_statement(p):
    """
    read_statement : READ '*' ',' var_list
    """
    p[0] = ('READ', p[4])
    # p[4] é a lista de variáveis onde os valores lidos serão armazenados.
    # Exemplo de código: READ *, VALOR1, VALOR2
    # Exemplo de AST: ('READ', ['VALOR1', 'VALOR2'])

def p_expression_list(p):
    """
    expression_list : expression
                    | expression_list ',' expression
    """    
    # Regra recursiva para lidar com listas de expressões separadas por vírgula.
    # Usada em PRINT, por exemplo.
    if len(p) == 2:
        # Caso base: uma única expressão.
        p[0] = [p[1]]
    else:
        # Caso recursivo: adiciona a nova expressão (p[3]) à lista existente (p[1]).
        p[0] = p[1] + [p[3]]

# Expressões
def p_expression_binop(p):
    """
    expression : expression '+' expression
               | expression '-' expression
               | expression '*' expression
               | expression '/' expression
               | expression POW expression
               | expression LT expression
               | expression LE expression
               | expression EQ expression
               | expression NE expression
               | expression GT expression
               | expression GE expression
               | expression AND expression
               | expression OR expression
    """
    # Regra genérica para operadores binários.
    # p[1] é a expressão da esquerda, p[2] é o operador, p[3] é a expressão da direita.
    # A precedência e associatividade são tratadas pela variável 'precedence' definida acima.
    p[0] = (p[2], p[1], p[3])
    # Exemplo de AST: ('+', (expr_esq), (expr_dir))

def p_expression_function_call(p):
    """
    expression : VAR '(' expression_list ')'
    """
    # Regra para chamadas de função, como MOD(NUM, I)
    # p[1] é o nome da função, p[3] é a lista de argumentos.
    p[0] = ('CALL', p[1], p[3])

def p_expression_unary(p):
    """
    expression : NOT expression
               | '-' expression %prec UMINUS
    """
    # Regra para operadores unários (NOT e negação).
    # p[1] é o operador (o literal '-' ou o valor do token NOT, que é '.NOT.').
    # p[2] é a expressão à qual o operador se aplica.
    if p[1] == '-':
        # Operador unário menos (negação).
        # O '%prec UMINUS' força esta regra a ter a precedência definida para UMINUS,
        # o que a torna de maior precedência que a subtração binária.
        p[0] = ('UMINUS', p[2])
    else:
        # Operador lógico NOT unário.
        p[0] = ('NOT', p[2])
    # Exemplo de AST: ('UMINUS', ('VAR', 'X')), ('NOT', ('VAR', 'FLAG'))

def p_expression_group(p):
    """
    expression : '(' expression ')'
    """
    p[0] = p[2]
    # Parênteses são usados para agrupar expressões e alterar a precedência.
    # O valor da expressão agrupada é simplesmente o valor da expressão interna.

def p_expression_val(p):
    """
    expression : INTVAL
               | REALVAL
               | BOOLEAN
               | STRING
               | VAR
    """
    # Esta regra lida com os valores literais e variáveis.
    # Para simplificar a AST e padronizar, encapsulamos os valores em tuplos.
    # Usamos p.slice[1].type para identificar o tipo do token de forma explícita,
    # o que é mais robusto do que usar isinstance(), especialmente para booleanos
    # (já que em Python, isinstance(True, int) é verdadeiro).
    if p.slice[1].type == 'BOOLEAN':
        p[0] = ('CONST', 'BOOL', p[1])
    elif p.slice[1].type == 'INTVAL':
        p[0] = ('CONST', 'INT', p[1])
    elif p.slice[1].type == 'REALVAL':
        p[0] = ('CONST', 'REAL', p[1])
    elif p.slice[1].type == 'STRING':
        p[0] = ('CONST', 'STRING', p[1])
    elif p.slice[1].type == 'VAR':
        # Variáveis são representadas pelo seu nome.
        p[0] = ('VAR', p[1])
    # Exemplo de AST: ('CONST', 'INT', 10), ('VAR', 'X')

# Regra para produções vazias
# Esta regra é um "truque" do YACC para permitir que partes da gramática sejam opcionais.
# Por exemplo, 'optional_program_statement' pode ser 'PROGRAM VAR' ou 'empty'.
def p_empty(p):
    'empty :'
    pass

# Tratamento de erros de sintaxe
# Esta função é chamada automaticamente pelo PLY quando o parser encontra um erro de sintaxe,
# ou seja, uma sequência de tokens que não corresponde a nenhuma regra da gramática.
def p_error(p):
    if p:
        # Se 'p' não for None, significa que o erro ocorreu num token específico.
        # 'p.value' é o valor do token inesperado.
        # 'p.lineno' é o número da linha onde o erro ocorreu.
        # 'p.lexpos' é a posição do token no texto original.
        # Calculamos a coluna para uma mensagem de erro mais precisa.
        last_cr = lexer.lexdata.rfind('\n', 0, p.lexpos)
        if last_cr < 0:
            column = p.lexpos + 1
        else:
            column = (p.lexpos - last_cr)
        print(f"Erro de Sintaxe: Token inesperado '{p.value}' na linha {p.lineno}, coluna {column}")
    else:
        # Se 'p' for None, significa que o parser chegou ao fim do ficheiro
        # mas a gramática não foi completamente reduzida à regra inicial 'program'.
        # Isso geralmente indica um programa incompleto ou malformado.
        print("Erro de Sintaxe: Fim de ficheiro inesperado (EOF)")

# Construir o parser
parser = yacc.yacc()
# Esta linha constrói a tabela de parsing com base nas regras p_... e na precedência.

# --- Função de Teste ---
def run_parser_test(filename):
    try:
        with open(filename, 'r') as f:
            data = f.read()
            print(f"--- A analisar o ficheiro: {filename} ---")
            result = parser.parse(data, lexer=lexer)
            # O método parser.parse() recebe o texto a analisar e o lexer a usar.
            # Se a análise for bem-sucedida, retorna a AST (o valor de p[0] da regra 'program').
            # Se houver um erro de sintaxe, p_error é chamado e parser.parse() retorna None.
            if result:
                # Imprimir a AST de forma mais legível
                import pprint
                pp = pprint.PrettyPrinter(indent=2)
                print("\n--- Árvore Sintática Abstrata (AST) ---")
                pp.pprint(result)
            print("-" * 40)
    except FileNotFoundError:
        print(f"Erro: O ficheiro {filename} não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro durante a análise: {e}")

# Este bloco garante que a função de teste só é executada quando o script parser.py
# é invocado diretamente (ex: python3 parser.py meu_programa.f),
# e não quando é importado como um módulo noutro script.
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_parser_test(sys.argv[1])
    else:
        print("Uso: python3 src/parser.py <caminho_do_ficheiro>")
