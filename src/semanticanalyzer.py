from errors import Errors

class SemanticError(Exception):
    pass

class SymbolTable:
    def __init__(self):
        # Dicionário de scopes (global é o principal)
        self.scopes = {'global': {}}
        self.current_scope = 'global' # Scope atual

    def enter_scope(self, scope_name):
        if scope_name not in self.scopes:
            self.scopes[scope_name] = {}
        self.current_scope = scope_name

    def leave_scope(self):
        self.current_scope = 'global'

    def declare(self, name, type_val, is_array=False, size=None, line=None):
        # Vai buscar o scope
        scope = self.scopes[self.current_scope]
        
        # Verifica se a variável existe
        if name in scope:
            msg = Errors.get('sem', line, 'VAR_EXISTE', nome=name)
            raise SemanticError(msg)

        # Adiciona à tabela 
        scope[name] = {
            'type': type_val, 
            'is_array': is_array, 
            'size': size,         # Vai ser um número para Arrays, e None para Scalars
            'used': False,
            'line': line
        }
    
        return True

    def lookup(self, name, line=None):
        # Vai buscar o scope atual
        current_scope = self.scopes[self.current_scope]
        
        # Procura primeiro no scope atual
        if name in current_scope:
            current_scope[name]['used'] = True
            return current_scope[name]

        # Se não estiver no local, procura no global
        elif name in self.scopes['global']:
            self.scopes['global'][name]['used'] = True
            return self.scopes['global'][name]

        # Se não tiver no scope atual nem no global dá erro
        msg = Errors.get('sem', line, 'VAR_N_EXISTE', nome=name)
        raise SemanticError(msg)

class SemanticAnalyzer:
    def __init__(self):
        # Variável que guarda os scopes
        self.symbol_table = SymbolTable()
        # Lista de erros encontrados
        self.errors = []
        # Lista de avisos
        self.warnings = []

        self.declared_labels = set()   # Ex: todos os números antes do CONTINUE
        self.expected_labels = set() # Ex: os números que os DOs dizem que vão fechar

    def add_error(self, error):
        if error:
            self.errors.append(error)
            print(error)
    
    def add_warning(self, warning):
        if warning:
            self.warnings.append(warning)
            print(warning)

    def visit(self, node):
        """Método despachante genérico (dispatch) do Visitor Pattern."""
        if node is None:
            return None
                
        method_name = f"visit_{node[0]}"
        visitor = getattr(self, method_name, None)
        return visitor(node)

    def visit_CONST(self, node):
        """Recebe um nodo do tipo (Const, 'INT', 42) e convertemos para o tipo para o correspondente no Frotran"""
        type_val = node[1]

        if type_val == 'INT':
            return 'INTEGER'
        elif type_val == 'BOOL':
            return 'LOGICAL'
        elif type_val == 'REAL':
            return 'REAL'
        elif type_val == 'STRING':
            return 'CHARACTER'

        # Caso não seja nenhum destes tipos classificamos como unknown para continuar a verificar e procurar mais erros
        return 'UNKNOWN'

    def visit_VAR(self, node):
        """Recebe um nodo do tipo ('VAR', N, line) e vai buscar o tipo das variáveis à symbol table"""
        var_name = node[1]
        line = node[-1]
        try:
            # Vai buscar a informação da variável se ela existir {type, is_array, used}
            var_info = self.symbol_table.lookup(var_name,line)

            # Retorna o tipo
            var_type = var_info.get('type', None)
            return var_type
        except SemanticError as e:
            # Se a variável não existir adiciona um erro
            self.add_error(str(e))
            # Mais uma vez retornamos unknow para não parar de procurar por outros erros
            return 'UNKNOWN'

    def visit_BINOP(self, node):
        """
        Recebe um nodo do tipo ('+', ('CONST', 'INT', 2), ('CONST', 'INT', 3)) 
        e verifica se as variavéis sao compativeis para a operação
        """
        op = node[0]
        left = node[1]
        right = node[2]
        line = node[-1]

        # verificamos o que tem à esquerda e à direita
        type_left = self.visit(left)
        type_right = self.visit(right)

        # Caso haja algum erro em baixo subimos o erro
        if 'UNKNOWN' in (type_left,type_right):
            return 'UNKNOWN'

        expected = ""  # Variável para guardar o que queríamos, caso haja um erro

        # Regras para lógica
        if op in ['AND', 'OR']:
            if type_left == 'LOGICAL' and type_right == 'LOGICAL':
                return 'LOGICAL'

            expected = 'Logical'

        # Regras para comparação 
        elif op in ['LT', 'LE', 'EQ', 'NE', 'GT', 'GE']:
            # Nas comparaçãos 
            if type_left in ['INTEGER', 'REAL'] and type_right in ['INTEGER', 'REAL']:
                return 'LOGICAL'

            expected = 'Números'
   
        # Regras para a matemática
        elif op in ['+', '-', '*', '/', '**']:
            # Se forem dois integers retorna Integer
            if type_left == 'INTEGER' and type_right == 'INTEGER':
                return 'INTEGER'
            
            # Se for um integer e um Real retorna Real
            elif type_left in ['INTEGER', 'REAL'] and type_right in ['INTEGER', 'REAL']:
                return 'REAL'
            
            expected = 'Números'

        # Se a função não fez "return" em cima, é porque houve um erro
        msg = Errors.get('sem', line, 'TIPO_INCOMPATIVEL', 
                         esperado=expected, 
                         recebido=f'{type_left} e {type_right}')
        self.add_error(msg)

        return 'UNKNOWN'

    
    def visit_ASSIGN(self, node):
        """
        Recebe um nodo do tipo ('ASSIGN', target, expression, line) e realiza a análise semantica
        da instrução. (ex: X = 10 + 5)
        O objetivo é verificar a legalidade da operação verificando os tipos e se a variável existe
        """
        target = node[1]
        expression = node[2]
        line = node[-1]

        type_target = self.visit(target)
        type_expression = self.visit(expression)

        # Ignora se já existirem erros
        if 'UNKNOWN' in (type_target, type_expression):
            return 'UNKNOWN'

        # Se os tipos forem iguais retorna o tipo do alvo
        if type_target == type_expression:
            return type_target
        
        # Aqui vamos permitir que se faça REAL = INTEGER ou INTEGER = REAL
        elif type_target in ['INTEGER', 'REAL'] and type_expression in ['INTEGER', 'REAL']:
            # Contudo se se fizer INTEGER = REAL avisamos que o valor vai ser truncado para um integer (Ex: 5.4 fica 5)
            if type_target == 'INTEGER' and type_expression == 'REAL':
                msg = Errors.get('w', line, 'TRUNC_VAL', nome=target[1])
                self.add_warning(msg)

            return type_target

        else:
            msg = Errors.get('sem', line, 'TIPO_INCOMPATIVEL', esperado=type_target, recebido=type_expression)
            self.add_error(msg)

            return 'UNKNOWN'

    def visit_DECLARE(self, node):
        """
        Recebe um nodo do tipo ('DECLARE', type, vars_list, line)
        Exemplo: INTEGER X, Y, Z(10)
        O objetivo é registar cada variável na Symbol Table com o tipo correto.
        """
        type_vars = node[1]
        vars_list = node[2]
        line = node[-1]

        for var in vars_list:
            # var pode ser ('SCALAR', 'X') ou ('ARRAY', 'Z', size)
            var_type = var[0]
            var_name = var[1]

            try:
                if var_type == 'SCALAR':
                    self.symbol_table.declare(var_name, type_vars, False, line)

                elif var_type == 'ARRAY':
                    self.symbol_table.declare(var_name, type_vars, True, var[2], line)

            except SemanticError as e:
                self.add_error(str(e))

    def visit_LABEL(self, node):
        """
        Recebe um nodo do tipo ('LABEL', 10, CONTINUE, 10) e regista esse label verificando se há duplicados.
        """
        label_num = node[1]
        instruction = node[2]
        line = node[-1]

        if label_num in self.declared_labels:
            msg = Errors.get('sem', line, 'LABEL_DUPLICADO', 10)
            self.add_error(msg)
        
        else:
            self.declared_labels.add(label_num)

        # depois de guardar a label analisamos o que vem à frente dela
        return self.visit(instruction)

    def visit_GOTO(self, node):
        """Recebe um nodo do tipo ('GOTO', 10) e regista que o programa quer saltar para um label."""
        target_label = node[1]
        self.expected_labels.add(target_label)
        return None

    def visit_DO(self, node):
        """
        Receives a node of type ('DO', label, var, start, end, step, line)
        Validates the label, the control variable and the numeric expressions.
        """
        expected_label = node[1]
        var = node[2]
        start_expr = node[3]
        end_expr = node[4]
        step_expr = node[5]
        line = node[-1]

        # Adiciona esta label às esperadas
        self.expected_labels.add(expected_label)

        var_name = var[1]

        try:
            # Caso a variável exista verificamos se é um integer ou real
            var_info = self.symbol_table.lookup(var_name, line)
            var_type = var_info.get('type', None)

            if var_type not in ['INTEGER', 'REAL']:
                msg = Errors.get('sem', line, 'TIPO_INCOMPATIVEL', esperado='INTEGER ou REAL', recebido=var_type)
                self.add_error(msg)

        except SemanticError as e:
            self.add_error(str(e))

        # Agora validamos as expressoes de inicio do ciclio, final e avanço
        to_test = [start_expr, end_expr, step_expr]

        for expr in to_test:
            expr_type = self.visit(expr)

            # Se já existe um erro ignoramos
            if expr_type == 'UNKNOWN':
                continue

            # Verificamos se a expressão é um número como é suposto
            if expr_type not in ['INTEGER', 'REAL']:
                msg = Errors.get('sem', line, 'TIPO_INCOMPATIVEL', esperado='INTEGER ou REAL', recebido=expr_type)
                self.add_error(msg)

        return None

    def visit_ARRAY_ACCESS(self, node):
        """ 
        Recebe um nodo ('ARRAY_ACCESS', var_name, index_expr, line)e garante que X(5) à esquerda do '=' é válido.
        """
        var_name = node[1]
        index_expr = node[2]
        line = node[-1]

        try:
            var_info = self.symbol_table.lookup(var_name, line)

            if not var_info.get('is_array'):
                msg = Errors.get('sem', line, 'NAO_E_ARRAY', nome=var_name)
                self.add_error(msg)
                return 'UNKNOWN'

            index_type = self.visit(index_expr)
            
            # Se não houver já um erro no tipo do index ou se ele nao for integer adicionamos um erro
            # Não mandamos outro erro caso já exista um pois assim um utilizador não tem erros duplicados
            if index_type not in ['UNKNOWN', 'INTEGER']:
                msg = Errors.get('sem', line, 'INDICE_TIPO', nome=var_name, recebido=index_type)
                self.add_error(msg)
                return 'UNKNOWN'

            # agora verificamos se o indice não ultrapassa os limites do array
            if index_expr[0] == 'CONST' and index_expr[1] == 'INT':
                index_val = index_expr[2]
                array_size = var_info.get('size')
                
                if index_val < 1 or index_val > array_size:
                    msg = Errors.get('sem', line, 'OUT_OF_BOUNDS', nome=var_name, tamanho=array_size, recebido=index_val)
                    self.add_error(msg)
                    return 'UNKNOWN'

            return var_info.get('type')

        except SemanticError as e:
            self.add_error(str(e))
            return 'UNKNOWN'

    def visit_CALL(self, node):
        """
        Recebe um nodo do tipo ('CALL', name, args_list, line)
        e resolve a ambiguidade entre Arrays e Funções dentro de expressões.
        """
        name = node[1]
        args_list = node[2]
        line = node[-1]

        try:
            # Vamos buscar a info à tabela de símbolos
            info = self.symbol_table.lookup(name, line)

            # Caso seja um array 
            if info.get('is_array'):
                # O compilador só suporta arrays 1D logo só pode ter um argumento nos parêntesis
                if len(args_list) != 1:
                    msg = Errors.get('sem', line, 'NUM_ARGS', nome=name, esperado=1, recebido=len(args_list))
                    self.add_error(msg)
                    return 'UNKNOWN'

                index_expr = args_list[0]
                index_type = self.visit(index_expr)

                # Validamos se o índice é um número inteiro
                if index_type not in ['UNKNOWN', 'INTEGER']:
                    msg = Errors.get('sem', line, 'INDICE_TIPO', nome=name, recebido=index_type)
                    self.add_error(msg)
                    return 'UNKNOWN'

                # Verifica os limites do array (em tempo de compilação)
                if index_expr[0] == 'CONST' and index_expr[1] == 'INT':
                    index_val = index_expr[2]
                    array_size = info.get('size')
                    
                    if index_val < 1 or index_val > array_size:
                        msg = Errors.get('sem', line, 'OUT_OF_BOUNDS', nome=name, tamanho=array_size, recebido=index_val)
                        self.add_error(msg)
                        return 'UNKNOWN'

                return info.get('type')

            # Caso seja uma função
            else:
                # Validamos que os argumentos passados para a função são válidos
                for arg in args_list:
                    self.visit(arg)
                
                # Como as funções também têm um tipo associado (ex: INTEGER FUNCTION OLA()), devolvemos o tipo que estiver na tabela
                return info.get('type')

        except SemanticError:
            # Se a Tabela de Símbolos não conhece o nome, lança erro.
            # Como o nó se chama CALL e usa parênteses, assumimos que o 
            # utilizador estava a tentar chamar uma Função que não existe!
            msg = Errors.get('sem', line, 'FUNCAO_N_DECLARADA', nome=name)
            self.add_error(msg)
            return 'UNKNOWN'

    def check_unresolved_labels(self):
        """Corre no final da análise semântica e verifica se há labels em falta"""
        missing_labels = self.expected_labels - self.declared_labels

        for label in missing_labels:
            msg = Errors.get('sem', 'Fim', 'DO_LABEL_N_EXISTE', label=label)
            self.add_error(msg)

    def check_unused_variables(self):
        """Procura por variáveis não utilizadas imprimindo warnings"""
        for scope_name, scope_vars in self.symbol_table.scopes.items():
            for name, info in scope_vars.items():
                if not info['used']:
                    msg = Errors.get('w', info['line'], 'VAR_N_USADA', nome=name)
                    self.add_warning(msg)

   def analyze(self, ast):
        """Ponto de entrada do Analisador Semântico."""
        self.visit(ast)
        self.check_unresolved_labels()
        self.check_unused_variables()
        return len(self.errors) == 0