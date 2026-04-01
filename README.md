# PL_G16_2526
Compilador Fortran 77 (ANSI X3.9-1978)

Este projeto consiste no desenvolvimento de um compilador para a linguagem Fortran 77, realizado no âmbito da unidade curricular de Processamento de Linguagens (2026). O objetivo principal é traduzir código fonte Fortran para o código máquina da Máquina Virtual disponibilizada.
🏗 Estrutura do Projeto

A organização do repositório segue uma lógica modular para facilitar a manutenção e o processo de compilação:
Plaintext

ProjetoPLC25/
├── src/                    # Código-fonte do compilador (Python + PLY)
│   ├── pcprogram.py        # Ponto de entrada do compilador
│   ├── analex.py           # Analisador Léxico (ply.lex)
│   ├── anasin.py           # Analisador Sintático (ply.yacc)
│   ├── anasem.py           # Analisador Semântico e Tabela de Símbolos
│   ├── geraCod.py          # Gerador de código para a VM
│   ├── Erros.py            # Gestão de mensagens de erro
│   └── Cores.py            # Utilitário para formatação de output
├── testes/                 # Conjunto de testes e exemplos [cite: 137]
├── doc/                    # Documentação técnica [cite: 135]
│   ├── gramatica.md        # Especificação da gramática utilizada
│   └── tokens.md           # Definição dos tokens identificados
├── Relatorio.latex         # Relatório técnico final (Máx. 10 páginas)
└── README.md               # Instruções de utilização e configuração

🚀 Funcionalidades Implementadas

O compilador suporta as construções essenciais da norma Fortran 77:

    Análise Léxica: Identificação de palavras-chave, identificadores e operadores.

    Análise Sintática: Validação da estrutura gramatical via ply.yacc.

    Análise Semântica: Verificação de tipos, declarações e coerência de labels (ciclos DO).

    Geração de Código: Tradução direta ou via representação intermédia para a VM.
