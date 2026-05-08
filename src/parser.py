import ply.yacc as yacc
from lexer import tokens, lexer
from errors import Errors

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('nonassoc', 'LT', 'LE', 'EQ', 'NE', 'GT', 'GE'),
    ('left', '+', '-'),
    ('left', '*', '/'),
    ('right', 'POW'),
    ('right', 'UMINUS'),
)

# --- Regra Raiz: ficheiro pode ter programa principal + subprogramas ---

def p_file(p):
    """
    file : program_unit
         | file program_unit
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_program_unit(p):
    """
    program_unit : main_program
                 | function_subprogram
                 | subroutine_subprogram
    """
    p[0] = p[1]

# --- Programa Principal ---

def p_main_program(p):
    """
    main_program : optional_program_statement declaration_section executable_section END
    """
    p[0] = ('PROGRAM', p[1], p[2], p[3])

def p_optional_program_statement(p):
    """
    optional_program_statement : PROGRAM VAR
                               | empty
    """
    p[0] = p[2] if len(p) > 2 else None

# --- Subprogramas  ---

def p_function_subprogram(p):
    """
    function_subprogram : type FUNCTION VAR '(' param_list ')' declaration_section executable_section END
                        | FUNCTION VAR '(' param_list ')' declaration_section executable_section END
    """
    if len(p) == 10:
        # Com tipo de retorno explícito: INTEGER FUNCTION CONVRT(N, B)
        line = p.lineno(2)
        p[0] = ('FUNCTION', p[3], p[1], p[5], p[7], p[8], line)
    else:
        line = p.lineno(1)
        p[0] = ('FUNCTION', p[2], None, p[4], p[6], p[7], line)

def p_subroutine_subprogram(p):
    """
    subroutine_subprogram : SUBROUTINE VAR '(' param_list ')' declaration_section executable_section END
                          | SUBROUTINE VAR '(' ')' declaration_section executable_section END
    """
    line = p.lineno(1)
    if len(p) == 9:
        p[0] = ('SUBROUTINE', p[2], p[5], p[6], p[7], line)
    else:
        p[0] = ('SUBROUTINE', p[2], [], p[5], p[6], line)

def p_param_list(p):
    """
    param_list : VAR
               | param_list ',' VAR
               | empty
    """
    if len(p) == 2:
        p[0] = [p[1]] if p[1] is not None else []
    else:
        p[0] = p[1] + [p[3]]

# --- Secções ---

def p_declaration_section(p):
    """
    declaration_section : declaration_section declaration
                        | empty
    """
    if len(p) > 2:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []

def p_executable_section(p):
    """
    executable_section : executable_section statement
                       | empty
    """
    if len(p) > 2:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []

# --- Declarações ---

def p_declaration(p):
    """
    declaration : type var_decl_list
    """
    p[0] = ('DECLARE', p[1], p[2])

def p_type(p):
    """
    type : INTEGER
         | REAL
         | LOGICAL
         | CHARACTER
    """
    p[0] = p[1]

def p_var_decl_list(p):
    """
    var_decl_list : var_decl
                  | var_decl_list ',' var_decl
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

def p_var_decl(p):
    """
    var_decl : VAR
             | VAR '(' INTVAL ')'
    """
    # Suporte a arrays: INTEGER NUMS(5)
    line = p.lineno(1)
    if len(p) == 2:
        p[0] = ('SCALAR', p[1], line)
    else:
        p[0] = ('ARRAY', p[1], p[3], line)

# --- Statements ---

def p_statement(p):
    """
    statement : labeled_statement
              | unlabeled_statement
    """
    p[0] = p[1]

def p_labeled_statement(p):
    """
    labeled_statement : LABEL unlabeled_statement
    """
    line = p.lineno(1) # A linha do próprio Label (o número)
    p[0] = ('LABEL', p[1], p[2], line)

def p_unlabeled_statement(p):
    """
    unlabeled_statement : assignment_statement
                        | if_statement
                        | do_statement
                        | goto_statement
                        | print_statement
                        | read_statement
                        | continue_statement
                        | return_statement
                        | stop_statement
                        | call_statement
    """
    p[0] = p[1]

def p_assignment_statement(p):
    """
    assignment_statement : VAR '=' expression
                         | VAR '(' expression ')' '=' expression
    """
    if len(p) == 4:
        line = p.lineno(2) # A linha do sinal '='
        # p.lineno(1) para o 'VAR' saber a sua própria linha
        p[0] = ('ASSIGN', ('VAR', p[1], p.lineno(1)), p[3], line)
    else:
        line = p.lineno(5) # A linha do sinal '='
        # p.lineno(1) para o ARRAY saber a sua linha
        p[0] = ('ASSIGN', ('ARRAY_ACCESS', p[1], p[3], p.lineno(1)), p[6], line)

def p_if_statement(p):
    """
    if_statement : IF '(' expression ')' THEN executable_section ENDIF
                 | IF '(' expression ')' THEN executable_section ELSE executable_section ENDIF
    """
    line = p.lineno(1)  # linha do token IF
    if len(p) == 8:
        p[0] = ('IF', p[3], p[6], [], line)
    else:
        p[0] = ('IF', p[3], p[6], p[8], line)

def p_do_statement(p):
    """
    do_statement : DO INTVAL VAR '=' expression ',' expression
                 | DO INTVAL VAR '=' expression ',' expression ',' expression
    """
    line = p.lineno(1) # A linha onde está a palavra 'DO'
    if len(p) == 8:
        p[0] = ('DO', p[2], p[3], p[5], p[7], ('CONST', 'INT', 1), line)
    else:
        p[0] = ('DO', p[2], p[3], p[5], p[7], p[9], line)

def p_goto_statement(p):
    """
    goto_statement : GOTO INTVAL
    """
    line = p.lineno(1)
    p[0] = ('GOTO', p[2], line)

def p_continue_statement(p):
    """
    continue_statement : CONTINUE
    """
    line = p.lineno(1)
    p[0] = ('CONTINUE', line)

def p_return_statement(p):
    """
    return_statement : RETURN
    """
    line = p.lineno(1)
    p[0] = ('RETURN', line)

def p_stop_statement(p):
    """
    stop_statement : STOP
    """
    line = p.lineno(1)
    p[0] = ('STOP', line)

def p_call_statement(p):
    """
    call_statement : CALL VAR '(' expression_list ')'
                   | CALL VAR '(' ')'
    """
    if len(p) == 6:
        p[0] = ('CALL_STMT', p[2], p[4])
    else:
        p[0] = ('CALL_STMT', p[2], [])

def p_print_statement(p):
    """
    print_statement : PRINT '*' ',' expression_list
    """
    p[0] = ('PRINT', p[4])

def p_read_statement(p):
    """
    read_statement : READ '*' ',' read_list
    """
    line = p.lineno(1)
    p[0] = ('READ', p[4], line)

def p_read_list(p):
    """
    read_list : read_item
              | read_list ',' read_item
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

def p_read_item(p):
    """
    read_item : VAR
              | VAR '(' expression ')'
    """
    if len(p) == 2:
        p[0] = ('VAR', p[1], p.lineno(1))
    else:
        p[0] = ('ARRAY_ACCESS', p[1], p[3], p.lineno(1))

# --- Expressões ---

def p_expression_list(p):
    """
    expression_list : expression
                    | expression_list ',' expression
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

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
    line = p.lineno(2) # Vai buscar a linha para ela ser guardada
    p[0] = (p[2], p[1], p[3], line)

def p_expression_function_call(p):
    """
    expression : VAR '(' expression_list ')'
    """
    # Cobre MOD(X,Y), chamadas a FUNCTION, e acesso a arrays como NUMS(I)
    # A distinção array vs função será feita na análise semântica
    line = p.lineno(1)
    p[0] = ('CALL', p[1], p[3], line)

def p_expression_unary(p):
    """
    expression : NOT expression
               | '-' expression %prec UMINUS
    """
    line = p.lineno(1)
    if p[1] == '-':
        p[0] = ('UMINUS', p[2], line)
    else:
        p[0] = ('NOT', p[2], line)

def p_expression_group(p):
    """
    expression : '(' expression ')'
    """
    p[0] = p[2]

def p_expression_val(p):
    """
    expression : INTVAL
               | REALVAL
               | BOOLEAN
               | STRING
               | VAR
    """
    token_type = p.slice[1].type
    line = p.lineno(1) # Apanha a linha da variável
    if token_type == 'VAR':
        p[0] = ('VAR', p[1], line)
    elif token_type == 'BOOLEAN':
        p[0] = ('CONST', 'BOOL', p[1], line)
    elif token_type == 'INTVAL':
        p[0] = ('CONST', 'INT', p[1], line)
    elif token_type == 'REALVAL':
        p[0] = ('CONST', 'REAL', p[1], line)
    elif token_type == 'STRING':
        p[0] = ('CONST', 'STRING', p[1], line)

def p_empty(p):
    'empty :'
    pass

# --- Erros---

class SintaxError(Exception):
    pass

def p_main_program_error_end(p):
    """
    main_program : optional_program_statement declaration_section executable_section error
    """
    msg = Errors.get('sin', p.lineno(1), 'FALTA_END', bloco='PROGRAM')
    raise SintaxError(msg)

def p_function_subprogram_error_end(p):
    """
    function_subprogram : type FUNCTION VAR '(' param_list ')' declaration_section executable_section error
                        | FUNCTION VAR '(' param_list ')' declaration_section executable_section error
    """
    msg = Errors.get('sin', p.lineno(2), 'FALTA_END', bloco='FUNCTION')
    raise SintaxError(msg)

# Exemplo de regra com Exception para o Fortran:
def p_if_statement_error(p):
    """
    if_statement : IF '(' expression ')' error
    """
    # Se abriu o IF mas o que se segue não faz sentido (ex: falta o THEN)
    msg = Errors.get('sin', p.lineno(1), 'FALTA_THEN')
    raise SintaxError(msg)  

def p_if_statement_error_endif(p):
    """
    if_statement : IF '(' expression ')' THEN executable_section error
                | IF '(' expression ')' THEN executable_section ELSE executable_section error
    """
    # Se abriu o IF mas nunca encontrou o ENDIF para fechar
    msg = Errors.get('sin', p.lineno(1), 'FALTA_ENDIF')
    raise SintaxError(msg)

def p_error(p):
    if p:
        msg = Errors.get('sin', p.lineno, 'TOKEN_INESPERADO', token=p.value, tipo_token=p.type)
    else:
        msg = Errors.get('sin', None, 'EOF_INESPERADO')
    raise SintaxError(msg)

parser = yacc.yacc()

def run_parser_test(filename):
    try:
        with open(filename, 'r') as f:
            data = f.read()
        print(f"--- A analisar: {filename} ---")
        result = parser.parse(data, lexer=lexer)
        if result:
            import pprint
            print("\n--- AST ---")
            pprint.pprint(result, indent=2)
        print("-" * 40)
    except FileNotFoundError:
        print(f"Erro: ficheiro '{filename}' não encontrado.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_parser_test(sys.argv[1])
    else:
        print("Uso: python3 parser.py <ficheiro.f>")