# Compilador Fortran 77 (ANSI X3.9-1978)

Este projeto consiste no desenvolvimento de um compilador para a linguagem **Fortran 77**, realizado no âmbito da unidade curricular de **Processamento de Linguagens (2026)**. O objetivo principal é traduzir código fonte Fortran para o código máquina da Máquina Virtual disponibilizada.

---

## 🏗 Estrutura do Projeto

A organização do repositório segue uma lógica modular para facilitar a manutenção e o processo de compilação:

```text
PL_G16_2526/
├── Report.latex         # Technical report in LaTeX
├── src/                 # Compiler source code
│   ├── main.py          # Main compiler program (ponto de entrada)
│   ├── lexer.py         # Lexical analyzer (ply.lex)
│   ├── parser.py        # Syntax analyzer (ply.yacc)
│   ├── semantic.py      # Semantic analyzer
│   ├── codegen.py       # EWVM code generator
│   └── utils/           # Auxiliary modules and support
│       ├── errors.py    # Centralized error messaging system
│       └── colors.py    # Terminal styling definitions
├── tests/               # Test programs (.f and .vm)
├── docs/                # Technical documentation (Grammar and Tokens)
│   ├── grammar.md       # Grammar description
│   └── tokens.md        # Tokens identification
└── README.md            # Project instructions
```

---

## 🚀 Requisitos Técnicos Implementados

O compilador suporta as construções essenciais da norma Fortran 77:
* **Tipos**: Declaração de variáveis e tipos (INTEGER, REAL, LOGICAL).
* **Expressões**: Aritméticas, lógicas e relacionais.
* **Fluxo**: `IF-THEN-ELSE`, ciclos `DO` com labels e comandos `GOTO`.
* **I/O**: Operações de `READ` e `PRINT`.
* **Subprogramas**: Suporte para `SUBROUTINE` e `FUNCTION` (Valorização).

---

## 🛠 Como Executar



---

## 👥 Grupo de Trabalho

Constituintes do grupo de trabalho:

| Nome | Número |
| :--- | :--- |
| David Lopes Machado | a107325 |
|  |  |
| Rodrigo de Sousa Campos Pacheco da Rocha | a107335 |

