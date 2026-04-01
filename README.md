# Compilador Fortran 77 (ANSI X3.9-1978)

Este projeto consiste no desenvolvimento de um compilador para a linguagem **Fortran 77**, realizado no âmbito da unidade curricular de **Processamento de Linguagens (2026)**. O objetivo principal é traduzir código fonte Fortran para o código máquina da Máquina Virtual disponibilizada.

---

## 🏗 Estrutura do Projeto

A organização do repositório segue uma lógica modular para facilitar a manutenção e o processo de compilação:

```text
PL_G16_2526/
├── Relatorio.latex      # Relatório técnico em LaTeX
├── src/
│   ├── pcprogram.py    # Programa principal do compilador
│   ├── analex.py       # Analisador léxico (ply.lex)
│   ├── anasin.py       # Analisador sintático (ply.yacc)
│   ├── anasem.py       # Analisador semântico
│   ├── geraCod.py      # Gerador de código EWVM
│   ├── utils/          # Módulos auxiliares e suporte
│   │   ├── Erros.py    # Sistema centralizado de mensagens de erro
│   │   └── Cores.py    # Definições para estilização do terminal
├── testes/             # Programas de teste (.f e .vm)
├── doc/                # Documentação técnica (Gramática e Tokens)
│   ├── gramatica.md
│   └── tokens.md
└── README.md           # Instruções do projeto
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

## 👥 Grupo 
* **Grupo**: 3 elementos.

