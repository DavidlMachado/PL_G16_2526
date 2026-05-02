"""
Test runner para o compilador Fortran 77.
Corre testes léxicos, sintáticos e semânticos e mostra os resultados.

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
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  True,
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
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  True,
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
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  True,
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
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  True,
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
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  True,
    },

    # ── Teste extra: erro léxico ──────────────────────────────────────────────

    {
        'name': 'Erro Léxico - Carácter ilegal @',
        'code': """\
 PROGRAM ERRO
 A = 10 @ ! O @ nao existe no Fortran
 END
""",
        'expect_lex_ok':  False,   # deve detetar o @
        'expect_parse_ok': None,   # None = não testamos (pode falhar ou não)
        'expect_sem_ok':  None,
    },

    # ── Testes semânticos ─────────────────────────────────────────────────────

    {
        'name': 'Erro Semântico - Variável não declarada',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 Y = 10
 END
""",
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  False,   # Y não declarada
    },

    {
        'name': 'Erro Semântico - Variável declarada duas vezes',
        'code': """\
 PROGRAM TESTE
 INTEGER X
 INTEGER X
 END
""",
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  False,
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
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  False,   # não se pode atribuir LOGICAL a INTEGER
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
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  False,
    },

    {
        'name': 'Erro Semântico - FUNCTION sem RETURN',
        'code': """\
 INTEGER FUNCTION SEMRET(X)
 INTEGER X
 X = X + 1
 END
""",
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  False,
    },

    {
        'name': 'Erro Semântico - Array fora dos limites',
        'code': """\
 PROGRAM TESTE
 INTEGER ARR(3)
 ARR(5) = 10
 END
""",
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  False,
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
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  False,   # label 99 nunca declarado
    },

    {
        'name': 'Aviso - Variável não utilizada',
        'code': """\
 PROGRAM TESTE
 INTEGER X, Y
 X = 5
 END
""",
        'expect_lex_ok':  True,
        'expect_parse_ok': True,
        'expect_sem_ok':  True,    # sem erros, mas deve gerar aviso para Y
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
    """Corre um teste e devolve (lex_ok, parse_ok, sem_ok)."""
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
        from parser import parser as fortran_parser
        from lexer import lexer as fortran_lexer2
        fortran_lexer2.lineno = 1
        fortran_lexer2.line_start = 0
        ast = fortran_parser.parse(code, lexer=fortran_lexer2)
        parse_ok = ast is not None
    except Exception as e:
        print(f"  {RED}[ERRO SINTÁTICO INTERNO]: {e}{RESET}")
        traceback.print_exc()

    # ── Fase 3: Semântico ─────────────────────────────────────────────────────
    sem_ok = False
    if ast is not None:
        try:
            from semanticanalyzer import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            sem_ok = analyzer.analyze(ast)
        except Exception as e:
            print(f"  {RED}[ERRO SEMÂNTICO INTERNO]: {e}{RESET}")
            traceback.print_exc()

    return lex_ok, parse_ok, sem_ok

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
            lex_ok, parse_ok, sem_ok = run_test(test)
        except Exception as e:
            print(f"  {RED}Erro interno no test runner: {e}{RESET}")
            traceback.print_exc()
            failed += 1
            continue

        exp_lex  = test.get('expect_lex_ok')
        exp_par  = test.get('expect_parse_ok')
        exp_sem  = test.get('expect_sem_ok')

        print_result(f"Léxico   (obtido={'OK' if lex_ok else 'ERRO'}, esperado={'OK' if exp_lex else 'ERRO' if exp_lex is not None else '?'})", lex_ok, exp_lex)
        print_result(f"Sintaxe  (obtido={'OK' if parse_ok else 'ERRO'}, esperado={'OK' if exp_par else 'ERRO' if exp_par is not None else '?'})", parse_ok, exp_par)
        print_result(f"Semântica(obtido={'OK' if sem_ok else 'ERRO'}, esperado={'OK' if exp_sem else 'ERRO' if exp_sem is not None else '?'})", sem_ok, exp_sem)

        # Conta como passou se todas as fases com expectativa definiram corretamente
        checks = []
        if exp_lex  is not None: checks.append(lex_ok  == exp_lex)
        if exp_par  is not None: checks.append(parse_ok == exp_par)
        if exp_sem  is not None: checks.append(sem_ok   == exp_sem)

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