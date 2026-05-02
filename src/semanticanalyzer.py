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
        self.do_labels = set()      # labels pedidos por DO
        self.goto_labels = set()    # labels pedidos por GOTO

        self.BINOPS = {'+', '-', '*', '/', '**', 'LT', 'LE', 'EQ', 'NE', 'GT', 'GE', 'AND', 'OR'}

        self._register_builtins()

    def _register_builtins(self):
        """Regista as funções intrínsecas do Fortran 77 na tabela de símbolos global."""
        builtins = {
            'MOD':   'INTEGER',   # MOD(A, B) -> resto da divisão
            'ABS':   'REAL',      # ABS(X) -> valor absoluto
            'SQRT':  'REAL',      # SQRT(X) -> raiz quadrada
            'INT':   'INTEGER',   # INT(X) -> conversão para inteiro
            'REAL':  'REAL',      # REAL(X) -> conversão para real
            'MAX':   'REAL',      # MAX(A, B, ...) -> máximo
            'MIN':   'REAL',      # MIN(A, B, ...) -> mínimo
            'FLOAT': 'REAL',      # FLOAT(X) -> conversão para real
            'IABS':  'INTEGER',   # IABS(X) -> valor absoluto inteiro
            'IFIX':  'INTEGER',   # IFIX(X) -> conversão para inteiro
        }

        for name, return_type in builtins.items():
            # Registamos os built-ins como usados para no final nao dar warning de inutilização
            self.symbol_table.scopes['global'][name] = {
                'type': return_type,
                'is_array': False,
                'size': None,
                'used': True, 
                'line': None
            }

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

        tag = node[0]
        if tag in self.BINOPS:
            return self.visit_BINOP(node)

        method_name = f"visit_{tag}"
        visitor = getattr(self, method_name, None)

        if visitor is None:
            return 'UNKNOWN'

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
        Recebe um nodo do tipo ('DECLARE', type, vars_list)
        Exemplo: INTEGER X, Y, Z(10)
        O objetivo é registar cada variável na Symbol Table com o tipo correto.
        """
        type_vars = node[1]
        vars_list = node[2]

        for var in vars_list:
            # var pode ser ('SCALAR', 'X') ou ('ARRAY', 'Z', size)
            var_type = var[0]
            var_name = var[1]
            line = var[-1]

            try:
                if var_type == 'SCALAR':
                    self.symbol_table.declare(var_name, type_vars, is_array=False, line=line)

                elif var_type == 'ARRAY':
                    self.symbol_table.declare(var_name, type_vars, is_array=True, size=var[2], line=line)

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
            msg = Errors.get('sem', line, 'LABEL_DUPLICADO', label=label_num)
            self.add_error(msg)
        
        else:
            self.declared_labels.add(label_num)

        # depois de guardar a label analisamos o que vem à frente dela
        return self.visit(instruction)

    def visit_GOTO(self, node):
        """Recebe um nodo do tipo ('GOTO', 10) e regista que o programa quer saltar para um label."""
        target_label = node[1]
        self.goto_labels.add(target_label)
        return None

    def visit_DO(self, node):
        """
        Receives a node of type ('DO', label, var, start, end, step, line)
        Validates the label, the control variable and the numeric expressions.
        """
        expected_label = node[1]
        var_name = node[2]
        start_expr = node[3]
        end_expr = node[4]
        step_expr = node[5]
        line = node[-1]

        # Adiciona esta label às esperadas
        self.do_labels.add(expected_label)

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

    def visit_IF(self, node):
        """
        Recebe um nodo do tipo ('IF', condition, then_block, else_block, line) 
        e verifica se a condição é lógica e visita os blocos.
        """
        condition = node[1]
        then_block = node[2]
        else_block = node[3]
        line = node[-1]

        cond_type = self.visit(condition)
        if cond_type not in ('UNKNOWN', 'LOGICAL'):
            msg = Errors.get('sem', line, 'TIPO_INCOMPATIVEL', esperado='LOGICAL', recebido=cond_type)
            self.add_error(msg)

        for stmt in then_block:
            self.visit(stmt)

        for stmt in else_block:
            self.visit(stmt)

    def visit_PRINT(self, node):
        """Recebe um nodo do tipo ('PRINT', expression_list) e visita cada expressão da lista."""
        for expr in node[1]:
            self.visit(expr)

    def visit_READ(self, node):
        """Recebe um nodo do tipo ('READ', read_list, line) e verifica se cada item foi declarado."""
        for item in node[1]:
            self.visit(item)

    def visit_CONTINUE(self, node):
        """Recebe um nodo do tipo ('CONTINUE',) e não faz nada (instrução de marcação)."""
        return None

    def visit_STOP(self, node):
        """Recebe um nodo do tipo ('STOP',) e não faz nada (termina o programa em runtime)."""
        return None

    def visit_RETURN(self, node):
        """Recebe um nodo do tipo ('RETURN', line) e verifica se está dentro de uma FUNCTION ou SUBROUTINE."""
        line = node[-1]
        if self.symbol_table.current_scope == 'global':
            msg = Errors.get('sem', line, 'RETURN_FORA_SUBPROG')
            self.add_error(msg)
        return None

    def visit_UMINUS(self, node):
        """Recebe um nodo do tipo ('UMINUS', expression, line) e verifica se a expressão é numérica."""
        line = node[-1]
        type_val = self.visit(node[1])
        if type_val not in ('UNKNOWN', 'INTEGER', 'REAL'):
            msg = Errors.get('sem', line, 'TIPO_INCOMPATIVEL', esperado='INTEGER ou REAL', recebido=type_val)
            self.add_error(msg)
            return 'UNKNOWN'
        return type_val

    def visit_NOT(self, node):
        """Recebe um nodo do tipo ('NOT', expression) e verifica se a expressão é lógica."""
        line = node[-1]
        type_val = self.visit(node[1])
        if type_val not in ('UNKNOWN', 'LOGICAL'):
            msg = Errors.get('sem', line, 'TIPO_INCOMPATIVEL', esperado='LOGICAL', recebido=type_val)
            self.add_error(msg)
            return 'UNKNOWN'
        return 'LOGICAL'

    def visit_PROGRAM(self, node):
        """Recebe um nodo do tipo ('PROGRAM', nome, declarações, statements) e visita todas as declarações e instruções."""
        for decl in node[2]:
            self.visit(decl)

        for stmt in node[3]:
            self.visit(stmt)

    def _has_return(self, stmts):
        """Verifica se existe pelo menos um RETURN acessível na lista de statements."""
        for stmt in stmts:
            if stmt is None:
                continue
            tag = stmt[0]
            if tag == 'RETURN':
                return True
            if tag == 'LABEL':
                # ('LABEL', num, instrução, line)
                if self._has_return([stmt[2]]):
                    return True
            if tag == 'IF':
                # Se AMBOS os ramos têm return, é garantido
                # Se só um tem, não é garantido (usamos aviso, não erro)
                if self._has_return(stmt[2]) or self._has_return(stmt[3]):
                    return True
        return False

    def visit_FUNCTION(self, node):
        """
        Recebe um nodo do tipo ('FUNCTION', nome, tipo_retorno, params, declarações, statements, line) 
        e verifica se a função tem RETURN.
        """
        name = node[1]
        return_type = node[2]
        line = node[-1]

        try:
            self.symbol_table.declare(name, return_type, line=line)

        except SemanticError:
            # Em Fortran 77 é válido pré-declarar o tipo da função no programa chamador
            # Verificamos se o tipo é compatível
            existing = self.symbol_table.scopes['global'].get(name)
            if existing and existing.get('type') != return_type:
                msg = Errors.get('sem', line, 'FUNC_DUPLICADA', nome=name)
                self.add_error(msg)
                return

        # Regista e entra no scope
        self.symbol_table.enter_scope(name)

        declarations = node[4]
        statements = node[5]

        # Visita todas as declarações
        for decl in declarations:
            self.visit(decl)
        # Visita todos os statements
        for stmt in statements:
            self.visit(stmt)

        # Verifica se a função tem um RETURN
        if not self._has_return(statements):
            msg = Errors.get('sem', None, 'FUNC_SEM_RETURN', nome=name)
            self.add_error(msg)

        self.symbol_table.leave_scope()

    def visit_SUBROUTINE(self, node):
        """
        Recebe um nodo do tipo ('SUBROUTINE', nome, params, declarações, statements, line) 
        e visita todas as declarações e instruções.
        """
        name = node[1]
        line = node[-1]

        # Regista a subroutine (ela não tem tipo de retorno)
        try:
            self.symbol_table.declare(name, None, line=line)
        except SemanticError:
            msg = Errors.get('sem', line, 'FUNC_DUPLICADA', nome=name)
            self.add_error(msg)
            return

        # Regista e entra no scope
        self.symbol_table.enter_scope(name)

        declarations = node[3]
        statements = node[4]

        # Visita todas as declarações
        for decl in declarations:
            self.visit(decl)
        # Visita todos os statements
        for stmt in statements:
            self.visit(stmt)

        self.symbol_table.leave_scope()

    def check_unresolved_labels(self):
        """Corre no final da análise semântica e verifica se há labels em falta"""
        # Verifica labels de DO
        for label in self.do_labels - self.declared_labels:
            msg = Errors.get('sem', 'Fim', 'DO_LABEL_N_EXISTE', label=label)
            self.add_error(msg)

        # Verifica labels de GOTO
        for label in self.goto_labels - self.declared_labels:
            msg = Errors.get('sem', 'Fim', 'GOTO_LABEL_N_EXISTE', label=label)
            self.add_error(msg)

    def check_unused_variables(self):
        """Procura por variáveis não utilizadas imprimindo warnings"""
        for scope_name, scope_vars in self.symbol_table.scopes.items():
            for name, info in scope_vars.items():
                if not info['used']:
                    # Diferenciamos funções e subroutines através do scope
                    if name in self.symbol_table.scopes:
                        msg = Errors.get('w', info['line'], 'FUNC_N_USADA', nome=name)
                    else:
                        msg = Errors.get('w', info['line'], 'VAR_N_USADA', nome=name)
                    self.add_warning(msg)

    def analyze(self, ast):
        """Ponto de entrada do Analisador Semântico."""
        for unit in ast:
            self.visit(unit)

        self.check_unresolved_labels()
        self.check_unused_variables()

        return len(self.errors) == 0