"""
Test runner para o compilador Fortran 77.
Corre testes léxicos, sintáticos, semânticos e de otimização e mostra os resultados.

Uso: python3 test_runner.py
"""

import sys
import os
import traceback

# ─── Cores para output ───────────────────────────────────────────────────────

GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
BLUE   = '\033[94m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

# ─── Funções de verificação da AST ───────────────────────────────────────────

def ast_find_program(ast, name=None):
    """Devolve o nodo PROGRAM da AST (ou o primeiro se name=None)."""
    for node in ast:
        if node[0] == 'PROGRAM':
            if name is None or node[1] == name:
                return node
    return None

def ast_find_unit(ast, tag, name):
    """Devolve um nodo FUNCTION ou SUBROUTINE com o nome dado."""
    for node in ast:
        if node[0] == tag and node[1] == name:
            return node
    return None

def ast_has_unit(ast, tag, name):
    """Verifica se existe uma FUNCTION ou SUBROUTINE com o nome dado na AST."""
    return ast_find_unit(ast, tag, name) is not None

def ast_var_declared(program_node, var_name):
    """Verifica se uma variável ainda está declarada no programa."""
    # Declarações estão em node[2] para PROGRAM, node[4] para FUNCTION, node[3] para SUBROUTINE
    tag = program_node[0]
    if tag == 'PROGRAM':
        decls = program_node[2]
    elif tag == 'FUNCTION':
        decls = program_node[4]
    elif tag == 'SUBROUTINE':
        decls = program_node[3]
    else:
        return False

    for decl in decls:
        for var in decl[2]:
            if var[1] == var_name:
                return True
    return False

def ast_count_stmts(stmts, tag):
    """Conta statements com uma determinada tag numa lista de statements (não recursivo)."""
    return sum(1 for s in stmts if s is not None and s[0] == tag)

def ast_get_stmts(program_node):
    """Devolve a lista de statements de um nodo de programa."""
    tag = program_node[0]
    if tag == 'PROGRAM':
        return program_node[3]
    elif tag == 'FUNCTION':
        return program_node[5]
    elif tag == 'SUBROUTINE':
        return program_node[4]
    return []

def ast_stmts_after_goto(stmts):
    """
    Verifica se existem statements não-LABEL após um GOTO.
    Devolve True se houver dead code, False se o optimizer limpou tudo.
    """
    for i, stmt in enumerate(stmts):
        if stmt is not None and stmt[0] == 'GOTO':
            # Verifica o que vem a seguir
            for next_stmt in stmts[i+1:]:
                if next_stmt is not None and next_stmt[0] != 'LABEL':
                    return True  # há dead code
    return False  # está limpo

def ast_stmts_after_goto_recursive(stmts):
    """Versão recursiva que desce em IFs e LABELs."""
    if ast_stmts_after_goto(stmts):
        return True
    for stmt in stmts:
        if stmt is None:
            continue
        if stmt[0] == 'IF':
            if ast_stmts_after_goto_recursive(stmt[2]):  # then_block
                return True
            if ast_stmts_after_goto_recursive(stmt[3]):  # else_block
                return True
        if stmt[0] == 'LABEL':
            inner = stmt[2]
            if inner and inner[0] == 'IF':
                if ast_stmts_after_goto_recursive(inner[2]):
                    return True
                if ast_stmts_after_goto_recursive(inner[3]):
                    return True
    return False

# ─── Definição dos testes ────────────────────────────────────────────────────

TESTS = [

    # ── Exemplos do guião ────────────────────────────────────────────────────

    {
        'name': 'Exemplo 1 - Olá Mundo',
        'code': """\
 PROGRAM HELLO
 PRINT *, 'Ola, Mundo!'
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_codegen_ok': True,
        'check_codegen': lambda vm_code: (
            'pushs "Ola, Mundo!"' in vm_code and 'writes' in vm_code,
            "Código para PRINT devia incluir pushs e writes"
        )
    },

    {
        'name': 'Exemplo 2 - Fatorial',
        'code': """\
 PROGRAM FATORIAL
 INTEGER N, I, FAT
 PRINT *, 'Introduza um numero inteiro positivo:'
 READ *, N
 FAT = 1
 DO 10 I = 1, N
 FAT = FAT * I
 10 CONTINUE
 PRINT *, 'Fatorial de ', N, ': ', FAT
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_codegen_ok': True,
        'check_codegen': lambda vm_code: (
            any('dostart' in line for line in vm_code) and any('doend' in line for line in vm_code),
            "Ciclo DO devia gerar labels do_start e do_end"
        )
    },

    {
        'name': 'Exemplo 3 - É primo?',
        'code': """\
 PROGRAM PRIMO
 INTEGER NUM, I
 LOGICAL ISPRIM
 PRINT *, 'Introduza um numero inteiro positivo:'
 READ *, NUM
 ISPRIM = .TRUE.
 I = 2
 20 IF (I .LE. (NUM/2) .AND. ISPRIM) THEN
 IF (MOD(NUM, I) .EQ. 0) THEN
 ISPRIM = .FALSE.
 ENDIF
 I = I + 1
 GOTO 20
 ENDIF
 IF (ISPRIM) THEN
 PRINT *, NUM, ' e um numero primo'
 ELSE
 PRINT *, NUM, ' nao e um numero primo'
 ENDIF
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_codegen_ok': True,
        'check_codegen': lambda vm_code: (
            any('ifelse' in line for line in vm_code) and any('ifend' in line for line in vm_code),
            "Instrução IF devia gerar labels if_else e if_end"
        )
    },

    {
        'name': 'Exemplo 4 - Soma de array',
        'code': """\
 PROGRAM SOMAARR
 INTEGER NUMS(5)
 INTEGER I, SOMA
 SOMA = 0
 PRINT *, 'Introduza 5 numeros inteiros:'
 DO 30 I = 1, 5
 READ *, NUMS(I)
 SOMA = SOMA + NUMS(I)
 30 CONTINUE
 PRINT *, 'A soma dos numeros e: ', SOMA
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_codegen_ok': True,
        'check_codegen': lambda vm_code: (
            any('storen' in line for line in vm_code) and any('loadn' in line for line in vm_code),
            "Acesso a array devia usar storen/loadn"
        )
    },

    {
        'name': 'Exemplo 5 - Conversor de bases com função',
        'code': """\
 PROGRAM CONVERSOR
 INTEGER NUM, BASE, RESULT, CONVRT
 PRINT *, 'INTRODUZA UM NUMERO DECIMAL INTEIRO:'
 READ *, NUM
 DO 10 BASE = 2, 9
 RESULT = CONVRT(NUM, BASE)
 PRINT *, 'BASE ', BASE, ': ', RESULT
 10 CONTINUE
 END
 INTEGER FUNCTION CONVRT(N, B)
 INTEGER N, B, QUOT, REM, POT, VAL
 VAL = 0
 POT = 1
 QUOT = N
 20 IF (QUOT .GT. 0) THEN
 REM = MOD(QUOT, B)
 VAL = VAL + (REM * POT)
 QUOT = QUOT / B
 POT = POT * 10
 GOTO 20
 ENDIF
 CONVRT = VAL
 RETURN
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_codegen_ok': True,
        'check_codegen': lambda vm_code: (
            any('call fCONVRT' in line for line in vm_code) and any('fCONVRT:' in line for line in vm_code),
            "Chamada de função devia gerar 'call fCONVRT' e a definição 'fCONVRT:'"
        )
    },

    # ── Erro léxico ───────────────────────────────────────────────────────────

    {
        'name': 'Erro Léxico - Carácter ilegal @',
        'code': """\
 PROGRAM ERRO
 A = 10 @ ! O @ não existe em Fortran
 END
""",
        'expect_lex_ok':   False,
        'expect_parse_ok': None,
        'expect_sem_ok':   None,
    },

    # ── Erros Sintáticos ───────────────────────────────────────────────────────────

    {
        'name': 'Erro Sintático - Declaração de variável após instrução executável',
        'code': """\
 PROGRAM TESTE
 X = 1
 INTEGER X
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': False,  # O Parser tem de barrar isto!
        'expect_sem_ok':   None,   # Nem chega à Semântica
    },

    # ── Erros semânticos ──────────────────────────────────────────────────────

    {
        'name': 'Erro Semântico - Variável não declarada',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 Y = 10
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   False,
    },

    {
        'name': 'Erro Semântico - Variável declarada duas vezes',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 INTEGER X
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   False,
    },

    {
        'name': 'Erro Semântico - Tipo incompatível na atribuição',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 LOGICAL Y
 Y = .TRUE.
 X = Y
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   False,
    },

    {
        'name': 'Erro Semântico - RETURN fora de subprograma',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 1
 RETURN
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   False,
    },

    {
        'name': 'Erro Semântico - FUNCTION sem RETURN',
        'code': """\
 INTEGER FUNCTION SEMRET(X)
 INTEGER X
 X = X + 1
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   False,
    },

    {
        'name': 'Erro Semântico - Array fora dos limites',
        'code': """\
 PROGRAM TESTE
 INTEGER ARR(3)
 ARR(5) = 10
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   False,
    },

    {
        'name': 'Erro Semântico - DO com label inexistente',
        'code': """\
 PROGRAM TESTE
 INTEGER I
 DO 99 I = 1, 10
 I = I + 1
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   False,
    },

    {
        'name': 'Aviso - Variável não utilizada',
        'code': """\
 PROGRAM TESTE
 INTEGER X, Y
 X = 5
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
    },

{
    'name': 'Erro Semântico - Número errado de argumentos',
    'code': """\
 PROGRAM TESTE
 INTEGER R, FOO
 R = FOO(1, 2)
 PRINT *, R
 END
 INTEGER FUNCTION FOO(X)
 INTEGER X
 FOO = X + 1
 RETURN
 END
""",
    'expect_lex_ok':   True,
    'expect_parse_ok': True,
    'expect_sem_ok':   False,  # FOO espera 1 argumento, recebeu 2
},

    # ── Testes do Optimizer ───────────────────────────────────────────────────

    # --- Dead Code Elimination ---

    {
        'name': 'Optimizer - Dead code simples após GOTO',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 1
 GOTO 10
 X = 99
 10 CONTINUE
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        # Verifica que não há dead code após GOTO na AST otimizada
        'check_opt': lambda opt_ast: (
            not ast_stmts_after_goto(ast_get_stmts(ast_find_program(opt_ast))),
            "Dead code após GOTO devia ter sido removido"
        ),
    },

    {
        'name': 'Optimizer - Múltiplas instruções de dead code após GOTO',
        'code': """\
 PROGRAM TESTE
 INTEGER X, Y, Z
 X = 1
 GOTO 10
 X = 99
 Y = 88
 Z = 77
 10 CONTINUE
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        'check_opt': lambda opt_ast: (
            not ast_stmts_after_goto(ast_get_stmts(ast_find_program(opt_ast))),
            "As 3 instruções de dead code deviam ter sido removidas"
        ),
    },

    {
        'name': 'Optimizer - Dead code dentro de IF (GOTO dentro do then_block)',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 READ *, X
 IF (X .GT. 0) THEN
 GOTO 10
 X = 99
 ENDIF
 10 CONTINUE
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        # Verifica recursivamente dentro dos blocos IF
        'check_opt': lambda opt_ast: (
            not ast_stmts_after_goto_recursive(ast_get_stmts(ast_find_program(opt_ast))),
            "Dead code dentro do IF devia ter sido removido"
        ),
    },

    {
        'name': 'Optimizer - Dead code dentro de LABEL com IF',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 READ *, X
 20 IF (X .GT. 0) THEN
 GOTO 10
 X = 55
 ENDIF
 10 CONTINUE
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        'check_opt': lambda opt_ast: (
            not ast_stmts_after_goto_recursive(ast_get_stmts(ast_find_program(opt_ast))),
            "Dead code dentro do LABEL+IF devia ter sido removido"
        ),
    },

    {
        'name': 'Optimizer - GOTO no else_block',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 READ *, X
 IF (X .GT. 0) THEN
 X = 1
 ELSE
 GOTO 10
 X = 99
 ENDIF
 10 CONTINUE
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        'check_opt': lambda opt_ast: (
            not ast_stmts_after_goto_recursive(ast_get_stmts(ast_find_program(opt_ast))),
            "Dead code no else_block devia ter sido removido"
        ),
    },

    {
        'name': 'Optimizer - Sem dead code (GOTO no fim)',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 1
 GOTO 10
 10 CONTINUE
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        # Não há dead code entre GOTO e LABEL, AST deve ficar igual
        'check_opt': lambda opt_ast: (
            not ast_stmts_after_goto(ast_get_stmts(ast_find_program(opt_ast))),
            "Não devia haver dead code para remover"
        ),
    },

    # --- Eliminar variáveis não usadas ---

    {
        'name': 'Optimizer - Variável não usada removida',
        'code': """\
 PROGRAM TESTE
 INTEGER X, Y
 X = 5
 PRINT *, X
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        # Y nunca é usada, deve ser removida das declarações
        'check_opt': lambda opt_ast: (
            not ast_var_declared(ast_find_program(opt_ast), 'Y'),
            "Variável 'Y' devia ter sido removida das declarações"
        ),
    },

    {
        'name': 'Optimizer - Variável usada mantida',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 5
 PRINT *, X
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        # X é usada, deve ser mantida
        'check_opt': lambda opt_ast: (
            ast_var_declared(ast_find_program(opt_ast), 'X'),
            "Variável 'X' devia ter sido mantida nas declarações"
        ),
    },

    {
        'name': 'Optimizer - Todas as variáveis não usadas removem a declaração inteira',
        'code': """\
 PROGRAM TESTE
 INTEGER X, Y
 PRINT *, 'ola'
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        # X e Y não são usadas, a declaração inteira deve desaparecer
        'check_opt': lambda opt_ast: (
            not ast_var_declared(ast_find_program(opt_ast), 'X') and
            not ast_var_declared(ast_find_program(opt_ast), 'Y'),
            "Declaração inteira devia ter sido removida"
        ),
    },

    {
    'name': 'Optimizer - Label não alvo de GOTO removido',
    'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 1
 10 CONTINUE
 X = 2
 END
""",
    'expect_lex_ok':   True,
    'expect_parse_ok': True,
    'expect_sem_ok':   True,
    'expect_opt_ok':   True,
    # O label 10 existe mas nunca é alvo de nenhum GOTO, deve ser removido
    'check_opt': lambda opt_ast: (
        all(s[0] != 'LABEL' for s in ast_get_stmts(ast_find_program(opt_ast)) if s is not None),
        "Label '10' nunca é alvo de um GOTO e devia ter sido removido"
    ),
},

{
    'name': 'Optimizer - Label alvo de DO mantido',
    'code': """\
 PROGRAM TESTE
 INTEGER I
 DO 10 I = 1, 5
 10 CONTINUE
 END
""",
    'expect_lex_ok':   True,
    'expect_parse_ok': True,
    'expect_sem_ok':   True,
    'expect_opt_ok':   True,
    # O label 10 é alvo do DO, deve ser mantido
    'check_opt': lambda opt_ast: (
        any(s[0] == 'LABEL' and s[1] == 10 for s in ast_get_stmts(ast_find_program(opt_ast)) if s is not None),
        "Label '10' é alvo de um DO e devia ter sido mantido"
    ),
},
{
    'name': 'Optimizer - Label alvo de GOTO mantido',
    'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 1
 GOTO 10
 10 CONTINUE
 X = 2
 END
""",
    'expect_lex_ok':   True,
    'expect_parse_ok': True,
    'expect_sem_ok':   True,
    'expect_opt_ok':   True,
    # O label 10 é alvo do GOTO, deve ser mantido
    'check_opt': lambda opt_ast: (
        any(s[0] == 'LABEL' and s[1] == 10 for s in ast_get_stmts(ast_find_program(opt_ast)) if s is not None),
        "Label '10' é alvo de um GOTO e devia ter sido mantido"
    ),
},

    # --- Eliminar funções/subrotinas não usadas ---

    {
        'name': 'Optimizer - Função não usada removida da AST',
        'code': """\
 PROGRAM TESTE
 PRINT *, 'ola'
 END
 INTEGER FUNCTION FOO(X)
 INTEGER X
 FOO = X + 1
 RETURN
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        # FOO nunca é chamada, deve ser removida da AST
        'check_opt': lambda opt_ast: (
            not ast_has_unit(opt_ast, 'FUNCTION', 'FOO'),
            "Função 'FOO' devia ter sido removida da AST"
        ),
    },

    {
        'name': 'Optimizer - Função usada mantida na AST',
        'code': """\
 PROGRAM TESTE
 INTEGER R, FOO
 R = FOO(5)
 PRINT *, R
 END
 INTEGER FUNCTION FOO(X)
 INTEGER X
 FOO = X + 1
 RETURN
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        # FOO é chamada, deve ser mantida
        'check_opt': lambda opt_ast: (
            ast_has_unit(opt_ast, 'FUNCTION', 'FOO'),
            "Função 'FOO' devia ter sido mantida na AST"
        ),
    },

    {
        'name': 'Optimizer - Variável não usada dentro de função',
        'code': """\
 PROGRAM TESTE
 INTEGER R, FOO
 R = FOO(5)
 PRINT *, R
 END
 INTEGER FUNCTION FOO(X)
 INTEGER X, TEMP
 FOO = X + 1
 RETURN
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_opt_ok':   True,
        # TEMP não é usada dentro de FOO, deve ser removida
        'check_opt': lambda opt_ast: (
            not ast_var_declared(ast_find_unit(opt_ast, 'FUNCTION', 'FOO'), 'TEMP'),
            "Variável 'TEMP' devia ter sido removida de dentro da função 'FOO'"
        ),
    },

    {
        'name': 'Erro Semântico - FUNCTION sem atribuição de valor de retorno',
        'code': """\
 PROGRAM TESTE
 INTEGER R, FOO
 R = FOO(5)
 PRINT *, R
 END
 INTEGER FUNCTION FOO(X)
 INTEGER X
 PRINT *, 'A calcular...'
 RETURN
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   False,
    },

    # --- Constant Folding ---

    {
    'name': 'Optimizer - Constant Folding simples',
    'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 5 + 3
 END
""",
    'expect_lex_ok':   True,
    'expect_parse_ok': True,
    'expect_sem_ok':   True,
    'expect_opt_ok':   True,
    'check_opt': lambda opt_ast: (
        ast_get_stmts(ast_find_program(opt_ast))[0][2] == ('CONST', 'INT', 8, 3),
        "5 + 3 devia ter sido simplificado para 8"
    ),
},
{
    'name': 'Optimizer - Constant Folding encadeado',
    'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 2 * (4 + 1)
 END
""",
    'expect_lex_ok':   True,
    'expect_parse_ok': True,
    'expect_sem_ok':   True,
    'expect_opt_ok':   True,
    'check_opt': lambda opt_ast: (
        ast_get_stmts(ast_find_program(opt_ast))[0][2] == ('CONST', 'INT', 10, 3),
        "2 * (4 + 1) devia ter sido simplificado para 10"
    ),
},
{
    'name': 'Optimizer - Constant Folding com IF (.TRUE.)',
    'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 1
 IF (.TRUE.) THEN
 X = 2
 ELSE
 X = 3
 ENDIF
 END
""",
    'expect_lex_ok':   True,
    'expect_parse_ok': True,
    'expect_sem_ok':   True,
    'expect_opt_ok':   True,
    'check_opt': lambda opt_ast: (
        ast_count_stmts(ast_get_stmts(ast_find_program(opt_ast)), 'IF') == 0,
        "IF (.TRUE.) devia ter sido eliminado"
    ),
},
{
    'name': 'Optimizer - Constant Folding com IF (.FALSE.)',
    'code': """\
 PROGRAM TESTE
 INTEGER X
 X = 1
 IF (.FALSE.) THEN
 X = 2
 ENDIF
 END
""",
    'expect_lex_ok':   True,
    'expect_parse_ok': True,
    'expect_sem_ok':   True,
    'expect_opt_ok':   True,
    'check_opt': lambda opt_ast: (
        ast_count_stmts(ast_get_stmts(ast_find_program(opt_ast)), 'IF') == 0,
        "IF (.FALSE.) devia ter sido eliminado"
    ),
    'expect_codegen_ok': True,
    'check_codegen': lambda vm_code: (
        not any('if_' in line for line in vm_code),
        "CodeGen não devia gerar labels de IF para um IF(.FALSE.) otimizado"
    )
},

    # ── Testes do CodeGen ───────────────────────────────────────────────────

    {
        'name': 'CodeGen - Atribuição a variável e array',
        'code': """\
 PROGRAM TESTE
 INTEGER X, ARR(5)
 X = 10
 ARR(1) = 20
 END
""",
        'expect_lex_ok':   True,
        'expect_parse_ok': True,
        'expect_sem_ok':   True,
        'expect_codegen_ok': True,
        'check_codegen': lambda vm_code: (
            any('storeg' in line for line in vm_code) and any('store' in line for line in vm_code),
            "Atribuição a variável devia usar 'storeg' e a array 'store'"
        )
    },
]

# ─── Funções auxiliares ───────────────────────────────────────────────────────

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'═' * 60}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'═' * 60}{RESET}")

def print_result(label, ok, expected):
    if expected is None:
        status = f"{YELLOW}[IGNORADO]{RESET}"
    elif ok == expected:
        status = f"{GREEN}[OK]{RESET}"
    else:
        status = f"{RED}[FALHOU]{RESET}"
    print(f"  {status} {label}")

def run_test(test):
    """Corre um teste e devolve (lex_ok, parse_ok, sem_ok, opt_ok, opt_ast, codegen_ok, vm_code)."""

    code = test['code']

    # ── Fase 1: Léxico ────────────────────────────────────────────────────────
    lex_ok = False
    try:
        from lexer import lexer as fortran_lexer
        fortran_lexer.lineno = 1
        fortran_lexer.line_start = 0
        fortran_lexer.error_count = 0
        fortran_lexer.input(code)
        while True:
            tok = fortran_lexer.token()
            if not tok:
                break
        lex_ok = fortran_lexer.error_count == 0
    except Exception as e:
        print(f"  {RED}[ERRO LÉXICO INTERNO]: {e}{RESET}")
        traceback.print_exc()

    # ── Fase 2: Sintático ─────────────────────────────────────────────────────
    ast = None
    parse_ok = False
    try:
        from parser import parser as fortran_parser, SintaxError
        from lexer import lexer as fortran_lexer2
        fortran_lexer2.lineno = 1
        fortran_lexer2.line_start = 0
        ast = fortran_parser.parse(code, lexer=fortran_lexer2)
        parse_ok = ast is not None
    except SintaxError as e:
        # A exceção já tem a mensagem de erro formatada.
        print(f"  {e}")
        parse_ok = False
    except Exception as e:
        print(f"  {RED}[ERRO SINTÁTICO INTERNO]: {e}{RESET}")
        traceback.print_exc()

    # ── Fase 3: Semântico ─────────────────────────────────────────────────────
    analyzer = None
    sem_ok = False
    if ast is not None:
        try:
            from semantic import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            sem_ok = analyzer.analyze(ast)
        except Exception as e:
            print(f"  {RED}[ERRO SEMÂNTICO INTERNO]: {e}{RESET}")
            traceback.print_exc()

    # ── Fase 4: Optimizer ─────────────────────────────────────────────────────
    opt_ast = None
    opt_ok = False
    if sem_ok and ast is not None and analyzer is not None:
        try:
            from optimizer import Optimizer
            optimizer = Optimizer(analyzer.symbol_table, analyzer.goto_labels.union(analyzer.do_labels))
            opt_ast = optimizer.optimize(ast)
            opt_ok = opt_ast is not None
        except Exception as e:
            print(f"  {RED}[ERRO OPTIMIZER INTERNO]: {e}{RESET}")
            traceback.print_exc()

    # ── Fase 5: CodeGen ───────────────────────────────────────────────────────
    vm_code = None
    codegen_ok = False
    if sem_ok and opt_ast is not None and analyzer is not None:
        try:
            from codegen import CodeGenerator
            generator = CodeGenerator(analyzer.symbol_table, analyzer.goto_labels)
            vm_code = generator.generate(opt_ast)
            codegen_ok = vm_code is not None and len(vm_code) > 0
        except Exception as e:
            print(f"  {RED}[ERRO CODEGEN INTERNO]: {e}{RESET}")
            traceback.print_exc()

    if vm_code is not None and codegen_ok:
        print(f"\n  {BLUE}Código VM gerado:{RESET}")
        for line in vm_code:
            print(f"    {line}")

    return lex_ok, parse_ok, sem_ok, opt_ok, opt_ast, codegen_ok, vm_code

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print_header("Test Runner — Compilador Fortran 77")

    passed = 0
    failed = 0
    total  = len(TESTS)

    for i, test in enumerate(TESTS, 1):
        name = test['name']
        print(f"\n{BOLD}Teste {i}/{total}: {name}{RESET}")
        print(f"  {BLUE}Código:{RESET}")
        for line in test['code'].strip().split('\n'):
            print(f"    {line}")
        print()

        try:
            lex_ok, parse_ok, sem_ok, opt_ok, opt_ast, codegen_ok, vm_code = run_test(test)
        except Exception as e:
            print(f"  {RED}Erro interno no test runner: {e}{RESET}")
            traceback.print_exc()
            failed += 1
            continue

        exp_lex = test.get('expect_lex_ok')
        exp_par = test.get('expect_parse_ok')
        exp_sem = test.get('expect_sem_ok')
        exp_opt = test.get('expect_opt_ok')
        exp_codegen = test.get('expect_codegen_ok')

        print_result(f"Léxico   (obtido={'OK' if lex_ok else 'ERRO'}, esperado={'OK' if exp_lex else 'ERRO' if exp_lex is not None else '?'})", lex_ok, exp_lex)
        print_result(f"Sintaxe  (obtido={'OK' if parse_ok else 'ERRO'}, esperado={'OK' if exp_par else 'ERRO' if exp_par is not None else '?'})", parse_ok, exp_par)
        print_result(f"Semântica(obtido={'OK' if sem_ok else 'ERRO'}, esperado={'OK' if exp_sem else 'ERRO' if exp_sem is not None else '?'})", sem_ok, exp_sem)

        if exp_opt is not None:
            print_result(f"Optimizer(obtido={'OK' if opt_ok else 'ERRO'}, esperado={'OK' if exp_opt else 'ERRO'})", opt_ok, exp_opt)
        
        if exp_codegen is not None:
            print_result(f"CodeGen  (obtido={'OK' if codegen_ok else 'ERRO'}, esperado={'OK' if exp_codegen else 'ERRO'})", codegen_ok, exp_codegen)

        # Verifica a AST otimizada se houver uma função de verificação
        check_fn = test.get('check_opt')
        check_passed = True
        if check_fn and opt_ast is not None:
            try:
                result, msg = check_fn(opt_ast)
                if result:
                    print(f"  {GREEN}[OK]{RESET} Verificação Optimizer: {msg}")
                else:
                    print(f"  {RED}[FALHOU]{RESET} Verificação Optimizer: {msg}")
                    check_passed = False
            except Exception as e:
                print(f"  {RED}[ERRO]{RESET} Verificação Optimizer falhou com exceção: {e}")
                traceback.print_exc()
                check_passed = False

        # Verifica o código gerado se houver uma função de verificação
        check_codegen_fn = test.get('check_codegen')
        check_codegen_passed = True
        if check_codegen_fn and vm_code is not None:
            try:
                result, msg = check_codegen_fn(vm_code)
                if result:
                    print(f"  {GREEN}[OK]{RESET} Verificação CodeGen: {msg}")
                else:
                    print(f"  {RED}[FALHOU]{RESET} Verificação CodeGen: {msg}")
                    check_codegen_passed = False
            except Exception as e:
                print(f"  {RED}[ERRO]{RESET} Verificação CodeGen falhou com exceção: {e}")
                traceback.print_exc()
                check_passed = False

        # Conta como passou se todas as fases com expectativa estiverem corretas
        checks = []
        if exp_lex is not None: checks.append(lex_ok  == exp_lex)
        if exp_par is not None: checks.append(parse_ok == exp_par)
        if exp_sem is not None: checks.append(sem_ok   == exp_sem)
        if exp_opt is not None: checks.append(opt_ok   == exp_opt)
        if exp_codegen is not None: checks.append(codegen_ok == exp_codegen)
        checks.append(check_passed)
        checks.append(check_codegen_passed)

        if all(checks):
            passed += 1
            print(f"  {GREEN}{BOLD}✓ Teste passou{RESET}")
        else:
            failed += 1
            print(f"  {RED}{BOLD}✗ Teste falhou{RESET}")

    # ── Sumário ───────────────────────────────────────────────────────────────
    print_header("Sumário")
    print(f"  Total  : {total}")
    print(f"  {GREEN}Passou : {passed}{RESET}")
    print(f"  {RED}Falhou : {failed}{RESET}")

    score = int((passed / total) * 100) if total > 0 else 0
    color = GREEN if score >= 80 else YELLOW if score >= 50 else RED
    print(f"\n  {color}{BOLD}Score: {score}%{RESET}\n")

if __name__ == '__main__':
    main()