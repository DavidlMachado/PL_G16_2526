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

    def declare(self, name, type_val, is_array=False, line=None):
        # Vai buscar o scope
        scope = self.scopes[self.current_scope]
        
        # Verifica se a variável existe
        if name in scope:
            msg = Errors.get('sem', line, 'VAR_EXISTE', nome=name)
            raise SemanticError(msg)

        # Adiciona à tabela 
        scope[name] = {'type': type_val, 'is_array': is_array, 'used': False}
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

        self.labels_declarados = set()   # Ex: todos os números antes do CONTINUE
        self.labels_esperados_do = set() # Ex: os números que os DOs dizem que vão fechar

    def add_error(self, error):
        if error:
            self.errors.append(error)
            print(error)

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
        """Recebe um nodo do tipo ('+', ('CONST', 'INT', 2), ('CONST', 'INT', 3)) 
        e verifica se as variavéis sao compativeis para a operação"""
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