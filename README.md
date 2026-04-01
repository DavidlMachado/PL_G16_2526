# Compilador Fortran 77 (ANSI X3.9-1978)

Este projeto consiste no desenvolvimento de um compilador para a linguagem **Fortran 77**, realizado no âmbito da unidade curricular de **Processamento de Linguagens (2026)**. O objetivo principal é traduzir código fonte Fortran para o código máquina da Máquina Virtual disponibilizada.

---

## 🏗 Estrutura do Projeto

A organização do repositório segue uma lógica modular para facilitar a manutenção e o processo de compilação:

* **src/**: Código-fonte do compilador implementado em Python utilizando a biblioteca `ply`.
    * `pcprogram.py`: Ponto de entrada (Main) do compilador.
    * `analex.py`: Analisador Léxico (`ply.lex`).
    * `anasin.py`: Analisador Sintático (`ply.yacc`).
    * `anasem.py`: Analisador Semântico (verificação de tipos e labels).
    * `geraCod.py`: Gerador de código para a Máquina Virtual.
    * `Erros.py` & `Cores.py`: Utilitários para tratamento de erros e output.
* **testes/**: Ficheiros de programas exemplo (.f) e os respetivos ficheiros de código em VM.
* **doc/**: Documentação técnica e gramática.
* **Relatorio.pdf**: Relatório técnico (máximo 10 páginas).

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

