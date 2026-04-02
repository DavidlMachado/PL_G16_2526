import ply.lex as lex
import re

literals = ['=', '+', '-', '*', '/', '(', ')', ',', ':', '.']

# Dicionário de Palavras Reservadas
# A chave é o que se escreve no Fortran, o valor é o nome do Token gerado.
reserved = {
    'PROGRAM': 'PROGRAM',
    'SUBROUTINE': 'SUBROUTINE',
    'FUNCTION': 'FUNCTION',
    'IF': 'IF',
    'THEN': 'THEN',
    'ELSE': 'ELSE',
    'ENDIF': 'ENDIF',
    'DO': 'DO',
    'END': 'END',
    'CONTINUE': 'CONTINUE',
    'GOTO': 'GOTO',
    'PRINT': 'PRINT',
    'READ': 'READ',
    'INTEGER': 'INTEGER',
    'REAL': 'REAL',
    'LOGICAL': 'LOGICAL',
    'CHARACTER': 'CHARACTER'
}

# Lista de Tokens 
tokens = [
    # Valores
    'VAR', 'INTVAL', 'REALVAL',  'STRING', 'BOOLEAN',
    # Operadores Relacionais e Lógicos 
    'LT', 'LE', 'EQ', 'NE', 'GT', 'GE', 'NOT', 'AND', 'OR',
    # Exponencial
    'POW',
] + list(reserved.values())

t_ignore = ' \t'

# Contar linhas (essencial para mensagens de erro)
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Regra para Comentários

def t_COMMENT(t):
    r'!.*'
    pass

# Regras para  Operadores Relacionais e Lógicos

t_LT = r'\.LT\.'

t_LE = r'\.LE\.'

t_EQ = r'\.EQ\.'

t_NE = r'\.NE\.'

t_GT = r'\.GT\.'

t_GE = r'\.GE\.'

t_NOT = r'\.NOT\.'

t_AND = r'\.AND\.'

t_OR = r'\.OR\.'

t_POW = r'\*\*'

# Regras para os Valores

def t_BOOLEAN(t):
    r'\.(TRUE|FALSE)\.'
    t.value = True if 'true' in t.value.lower() else False
    return t

def t_STRING(t):
    r"'[^']*'"
    t.value = t.value[1:-1] # Remove as aspas
    return t

def t_REALVAL(t):
    r'\d+\.\d{1,}'
    t.value = float(t.value)
    return t

def t_INTVAL(t):
    r'\d+'
    t.value = int(t.value)
    return t

# Regra para Variáveis
def t_VAR(t):
    r'[a-zA-Z][a-zA-Z0-9]*'
    val_upper = t.value.upper()
    # Verifica se o tipo é um reservado e muda-o nesse caso
    t.type = reserved.get(val_upper, 'VAR')
    return t

# Lidar com caracteres que o lexer não conhece
def t_error(t):
    # Calcula a coluna (posição dentro da linha)
    last_cr = t.lexer.lexdata.rfind('\n', 0, t.lexpos)
    if last_cr < 0:
        column = t.lexpos + 1
    else:
        column = (t.lexpos - last_cr)

    print(f"Erro Léxico: Carácter '{t.value[0]}' ilegal na linha {t.lineno}, coluna {column}")
    
    # Continuamos a percorrer o código para ver se há mais erros
    t.lexer.skip(1)

# Construir o lexer
lexer = lex.lex()