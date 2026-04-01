# Compilador Fortran 77 (ANSI X3.9-1978)

[cite_start]Este projeto consiste no desenvolvimento de um compilador para a linguagem **Fortran 77**, realizado no âmbito da unidade curricular de **Processamento de Linguagens (2026)**[cite: 3, 4]. [cite_start]O objetivo principal é traduzir código fonte Fortran para o código máquina da Máquina Virtual disponibilizada[cite: 8].

---

## 🏗 Estrutura do Projeto

A organização do repositório segue uma lógica modular para facilitar a manutenção e o processo de compilação:

* [cite_start]**src/**: Código-fonte do compilador implementado em Python utilizando a biblioteca `ply`[cite: 13, 18, 134].
    * `pcprogram.py`: Ponto de entrada (Main) do compilador.
    * [cite_start]`analex.py`: Analisador Léxico (`ply.lex`)[cite: 13].
    * [cite_start]`anasin.py`: Analisador Sintático (`ply.yacc`)[cite: 18].
    * [cite_start]`anasem.py`: Analisador Semântico (verificação de tipos e labels)[cite: 19, 20].
    * [cite_start]`geraCod.py`: Gerador de código para a Máquina Virtual[cite: 22].
    * `Erros.py` & `Cores.py`: Utilitários para tratamento de erros e output.
* [cite_start]**testes/**: Ficheiros de programas exemplo (.f) e os respetivos ficheiros de código em VM[cite: 31, 137].
* [cite_start]**doc/**: Documentação técnica e gramática[cite: 135, 136].
* [cite_start]**Relatorio.pdf**: Relatório técnico (máximo 10 páginas)[cite: 135].

---

## 🚀 Requisitos Técnicos Implementados

[cite_start]O compilador suporta as construções essenciais da norma Fortran 77[cite: 118]:
* [cite_start]**Tipos**: Declaração de variáveis e tipos (INTEGER, REAL, LOGICAL)[cite: 119].
* [cite_start]**Expressões**: Aritméticas, lógicas e relacionais[cite: 120].
* [cite_start]**Fluxo**: `IF-THEN-ELSE`, ciclos `DO` com labels e comandos `GOTO`[cite: 121].
* [cite_start]**I/O**: Operações de `READ` e `PRINT`[cite: 122].
* [cite_start]**Subprogramas**: Suporte para `SUBROUTINE` e `FUNCTION` (Valorização)[cite: 123, 124].

---

## 🛠 Como Executar

1.  **Instalar dependências**:
    ```bash
    pip install ply
    ```
2.  **Compilar um ficheiro Fortran**:
    ```bash
    python3 src/pcprogram.py testes/exemplo.f
    ```

---

## 👥 Grupo e Prazos
* [cite_start]**Grupo**: 3 elementos[cite: 126].
* [cite_start]**Registo do Grupo**: Até 05/04/2026[cite: 130].
* [cite_start]**Entrega Final**: 17/05/2026 às 23:59[cite: 132].
* [cite_start]**Defesas**: De 01/06/2026 a 05/06/2026[cite: 138].
