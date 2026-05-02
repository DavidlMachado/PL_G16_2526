from colors import Colors

class Errors:
    FLAG_WARNINGS = True

    MENSAGENS = {
        # Erros semânticos
        'VAR_EXISTE':           "A variável '{nome}' já foi declarada neste escopo.",
        'VAR_N_EXISTE':         "A variável '{nome}' não foi declarada.",
        'TIPO_INCOMPATIVEL':    "Tipo incompatível: esperava '{esperado}', recebeu '{recebido}'.",
        'FUNCAO_N_DECLARADA':   "A função/subrotina '{nome}' não foi declarada.",
        'FUNC_DUPLICADA':       "A função/subrotina '{nome}' já foi definida.",
        'NUM_ARGS':             "Número de argumentos inválido para '{nome}': esperava {esperado}, recebeu {recebido}.",
        'ARG_TIPO':             "Argumento '{param}' com tipo inválido: esperava '{esperado}', recebeu '{recebido}'.",
        'ASSIGN_TIPO':          "Não é possível atribuir '{recebido}' à variável '{nome}' do tipo '{esperado}'.",
        'NAO_E_ARRAY':          "'{nome}' não é um array.",
        'E_ARRAY':              "'{nome}' é array e não pode ser usado como escalar.",
        'INDICE_TIPO':          "O índice do array '{nome}' deve ser INTEGER, recebeu '{recebido}'.",
        'OUT_OF_BOUNDS': "Índice fora dos limites para o array '{nome}'. Tamanho máximo é {tamanho}, mas recebeu {recebido}.",
        'DO_LABEL_N_EXISTE':    "O label '{label}' do ciclo DO não existe.",
        'DO_LABEL_SEM_CONTINUE':"O label '{label}' do ciclo DO não corresponde a um CONTINUE.",
        'GOTO_LABEL_N_EXISTE':  "O label '{label}' do GOTO não existe.",
        'LABEL_DUPLICADO':      "O label '{label}' já foi declarado neste escopo.",
        'RETURN_FORA_SUBPROG':  "RETURN fora de uma FUNCTION ou SUBROUTINE.",
        'FUNC_SEM_RETURN':      "A FUNCTION '{nome}' pode não retornar um valor.",

        # Avisos
        'TRUNC_VAL':            "Atribuição de REAL a INTEGER na variável '{nome}'. O valor será truncado!",
        'VAR_N_USADA':          "A variável '{nome}' foi declarada, mas nunca utilizada.",
        'FUNC_N_USADA':          "A função/soubrotina '{nome}' foi declarada, mas nunca chamada.",

        # Erros sintáticos
        'TOKEN_INESPERADO':     "Token inesperado '{token}' (tipo: {tipo_token}).",
        'EOF_INESPERADO':       "Fim de ficheiro inesperado.",
        'FALTA_END':            "Esperava 'END' para fechar o bloco '{bloco}'.",
        'FALTA_THEN':           "Esperava 'THEN' após a condição do IF.",
        'FALTA_ENDIF':          "Esperava 'ENDIF' para fechar o bloco IF.",

        # Erros léxicos
        'CHAR_ILEGAL':          "Carácter '{char}' ilegal.",

        # Erros de geração
        'TIPO_N_IMPLEMENTADO':  "O tipo '{nome}' não está implementado na geração de código.",
    }

    TIPOS = {
        'lex': 'Erro Léxico',
        'sin': 'Erro Sintático',
        'sem': 'Erro Semântico',
        'ger': 'Erro de Geração',
        'w':   'Aviso',
    }

    @staticmethod
    def get(tipo, linha, chave, **kwargs):
        """
        Uso: Errors.get('sem', 10, 'VAR_N_EXISTE', nome='X')
        Uso para avisos: Errors.get('w', 15, 'TRUNC_VAL', nome='Y')
        """
        # Ignora avisos se a flag estiver a False
        if tipo == 'w' and not Errors.FLAG_WARNINGS:
            return None

        prefixo = Errors.TIPOS.get(tipo, 'Erro')
        
        # Amarelo para avisos, Vermelho para erros
        cor = Colors.YELLOW if tipo == 'w' else Colors.RED
        template = Errors.MENSAGENS.get(chave, "Erro desconhecido.")

        linha_str = str(linha) if linha is not None else 'indefinida'

        try:
            mensagem = template.format(**kwargs)
        except KeyError as e:
            mensagem = f"{template} [argumento em falta: {e}]"

        return f"{cor}{prefixo}: {mensagem} {Colors.BOLD}(Linha {linha_str}){Colors.RESET}"

    @staticmethod
    def report(tipo, linha, chave, **kwargs):
        """
        Imprime o erro diretamente.
        Uso: Errors.report('sem', 10, 'VAR_N_EXISTE', nome='X')
        """
        msg = Errors.get(tipo, linha, chave, **kwargs)
        if msg:
            print(msg)