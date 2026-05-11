import ply.lex as lex
from utils.errors import Errors

literals = ['=', '+', '-', '*', '/', '(', ')', ',', ':']

# Palavras Reservadas
reserved = {
    'PROGRAM':    'PROGRAM',
    'SUBROUTINE': 'SUBROUTINE',
    'FUNCTION':   'FUNCTION',
    'RETURN':     'RETURN',
    'IF':         'IF',
    'THEN':       'THEN',
    'ELSE':       'ELSE',
    'ELSEIF':     'ELSEIF',
    'ENDIF':      'ENDIF',
    'DO':         'DO',
    'END':        'END',
    'CONTINUE':   'CONTINUE',
    'GOTO':       'GOTO',
    'PRINT':      'PRINT',
    'READ':       'READ',
    'INTEGER':    'INTEGER',
    'REAL':       'REAL',
    'LOGICAL':    'LOGICAL',
    'CHARACTER':  'CHARACTER',
    'STOP':       'STOP',
    'CALL':       'CALL',
}

tokens = [
    'VAR', 'INTVAL', 'REALVAL', 'STRING', 'BOOLEAN',
    'LT', 'LE', 'EQ', 'NE', 'GT', 'GE',
    'NOT', 'AND', 'OR',
    'POW',
    'LABEL',      # número no início da linha (ex: "10" em "10 CONTINUE")
] + list(reserved.values())

t_ignore = ' \t'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.line_start = t.lexpos + len(t.value)

# Comentários: estilo free-form (!)
def t_COMMENT(t):
    r'!.*'
    pass

# Operadores relacionais e lógicos — ANTES de t_VAR e dos literais
t_LT  = r'\.LT\.'
t_LE  = r'\.LE\.'
t_EQ  = r'\.EQ\.'
t_NE  = r'\.NE\.'
t_GT  = r'\.GT\.'
t_GE  = r'\.GE\.'
t_NOT = r'\.NOT\.'
t_AND = r'\.AND\.'
t_OR  = r'\.OR\.'
t_POW = r'\*\*'

def t_BOOLEAN(t):
    r'\.(TRUE|FALSE)\.'
    t.value = True if 'TRUE' in t.value.upper() else False
    return t

def t_STRING(t):
    r"'[^']*'"
    t.value = t.value[1:-1]  # Remove aspas
    return t

def t_REALVAL(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

def t_INTVAL(t):
    r'\d+'
    raw_len = len(t.value)      # comprimento original ANTES de converter
    t.value = int(t.value)
    line_start = getattr(t.lexer, 'line_start', 0)
    text_before = t.lexer.lexdata[line_start:t.lexpos]
    text_after = t.lexer.lexdata[t.lexpos + raw_len:]
    next_char = text_after[0] if text_after else ''
    if text_before.strip() == '' and next_char in (' ', '\t'):
        t.type = 'LABEL'
    return t

def t_VAR(t):
    r'[a-zA-Z][a-zA-Z0-9]*'
    t.type = reserved.get(t.value.upper(), 'VAR')
    if t.type == 'VAR':
        t.value = t.value.upper()  # Fortran é case-insensitive
    return t

def t_error(t):
    # Reporta o erro léxico passando o primeiro carácter inválido
    Errors.report('lex', t.lineno, 'CHAR_ILEGAL', char=t.value[0])
    t.lexer.error_count += 1
    t.lexer.skip(1)  # Salta o carácter problemático e continua

lexer = lex.lex()
lexer.line_start = 0
lexer.error_count = 0