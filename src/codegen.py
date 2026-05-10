def find_nodes(ast, tag):
    # procura recursivamente todos os nós com uma certa tag
    nodes = []
    def _finder(node):
        if not isinstance(node, (list, tuple)):
            return
        if isinstance(node, tuple) and node[0] == tag:
            nodes.append(node)
        for item in node if isinstance(node, list) else node[1:]:
            _finder(item)
    _finder(ast)
    return nodes

def find_unit(ast, tag, name=None):
    # saca o primeiro PROGRAM, FUNCTION ou SUBROUTINE que aparecer
    for node in ast:
        if node[0] == tag:
            if name is None or node[1] == name:
                return node
    return None

class CodeGenerator:
    def __init__(self, symbol_table):
        self.symbol_table = symbol_table
        self.vm_code = []
        self.label_counter = 0
        self.current_scope = 'global'

        # controlo de fluxo
        self.fortran_labels = {}  # mapeia labels fortran -> labels vm
        self.do_loops = {}        # contexto dos ciclos DO

        # map de operadores da AST para a VM
        self.op_map = {
            '+': 'add', '-': 'sub', '*': 'mul', '/': 'div',
            'LT': 'inf', 'LE': 'infeq', 'EQ': 'equal', 'NE': 'nequal',
            'GT': 'sup', 'GE': 'supeq', 'AND': 'and', 'OR': 'or',
            'POW': 'pow'
        }

    def new_label(self, prefix="L"):
        self.label_counter += 1
        return f"{prefix}{self.label_counter}"

    def add_instruction(self, instr, *args):
        self.vm_code.append(f"{instr} " + ' '.join(map(str, args)))

    def add_label(self, label):
        self.vm_code.append(f"{label}:")

    def generate(self, ast):
        # alocar memória global (endereços)
        current_address = 0
        global_scope = self.symbol_table.scopes['global']
        for name, info in global_scope.items():
            if info.get('is_array') is not None:
                info['address'] = current_address
                info['scope_type'] = 'global'
                # arrays ocupam N, variáveis normais 1
                size = info.get('size', 1) if info.get('is_array') else 1
                current_address += size

        # offsets para variáveis locais e params
        for scope_name, scope_vars in self.symbol_table.scopes.items():
            if scope_name == 'global':
                continue
            current_offset = 0
            for name, info in scope_vars.items():
                info['address'] = current_offset
                info['scope_type'] = 'local'
                size = info.get('size', 1) if info.get('is_array') else 1
                current_offset += size

        # mapear labels do fortran
        for l_node in find_nodes(ast, 'LABEL'):
            f_label = l_node[1]
            if f_label not in self.fortran_labels:
                self.fortran_labels[f_label] = self.new_label(f"L{f_label}_")

        # start up
        main_program_node = find_unit(ast, 'PROGRAM')
        main_label = f"prog_{main_program_node[1]}" if main_program_node and main_program_node[1] else "prog_main"

        self.add_instruction("start")
        self.add_instruction("jump", main_label)

        # processar funções e subrotinas primeiro
        for node in ast:
            if node[0] in ['FUNCTION', 'SUBROUTINE']:
                self.visit(node)

        # agora o main
        self.add_label(main_label)
        if main_program_node:
            self.visit(main_program_node)

        self.add_instruction("stop")
        return self.vm_code

    def visit(self, node):
        if node is None:
            return

        tag = node[0]
        # junta tudo o que é operador binário no mesmo visitor
        if tag in self.op_map or tag in ['UMINUS', 'NOT']:
            method_name = "visit_BINOP"
        else:
            method_name = f"visit_{tag}"
        
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        if isinstance(node, list):
            for item in node:
                self.visit(item)
        elif isinstance(node, tuple):
            for item in node[1:]:
                self.visit(item)

    def _get_expression_type(self, node):
        # adivinha o tipo da expressão sem gerar código (versão simplificada da analise semântica)
        if node is None: return 'UNKNOWN'
        tag = node[0]

        if tag == 'CONST':
            type_map = {'INT': 'INTEGER', 'REAL': 'REAL', 'BOOL': 'LOGICAL', 'STRING': 'CHARACTER'}
            return type_map.get(node[1], 'UNKNOWN')
        
        if tag in ('VAR', 'CALL', 'ARRAY_ACCESS'):
            info = self.symbol_table.lookup(node[1], self.current_scope)
            return info.get('type', 'UNKNOWN')

        if tag in ['+', '-', '*', '/', 'POW', 'UMINUS']:
            # assume que real manda no pedaço
            type_left = self._get_expression_type(node[1])
            if len(node) > 2:
                type_right = self._get_expression_type(node[2])
                if 'REAL' in (type_left, type_right):
                    return 'REAL'
            return 'INTEGER'

        if tag in ['LT', 'LE', 'EQ', 'NE', 'GT', 'GE', 'AND', 'OR', 'NOT']:
            return 'LOGICAL'
        
        return 'UNKNOWN'

    # --- VISITORS ---

    def visit_PROGRAM(self, node):
        statements = node[3]
        for stmt in statements:
            self.visit(stmt)

    def visit_ASSIGN(self, node):
        target = node[1]
        
        # avalia exp -> fica na stack
        self.visit(node[2])

        if target[0] == 'VAR':
            var_info = self.symbol_table.lookup(target[1], self.current_scope)
            instr = "storeg" if var_info['scope_type'] == 'global' else "storel"
            self.add_instruction(instr, var_info['address'])

        elif target[0] == 'ARRAY_ACCESS':
            # stack: [val] -> calcular addr -> stack: [val, addr]
            self.visit(target) 
            self.add_instruction("swap") # VM precisa de [addr, val]
            self.add_instruction("storei")

    def visit_ARRAY_ACCESS(self, node):
        # deixa o endereço da cena na stack
        var_info = self.symbol_table.lookup(node[1], self.current_scope)
        index_expr = node[2]
        
        if var_info['scope_type'] == 'global':
            self.add_instruction("pushi", var_info['address'])
        else:
            self.add_instruction("pushfp")
            self.add_instruction("pushi", var_info['address'])
            self.add_instruction("add")
            
        self.visit(index_expr)
        self.add_instruction("pushi", 1)
        self.add_instruction("sub")
        self.add_instruction("add")

    def visit_IF(self, node):
        else_label = self.new_label("if_else")
        endif_label = self.new_label("if_end")

        self.visit(node[1])
        self.add_instruction("jz", else_label)

        # block then
        for stmt in node[2]:
            self.visit(stmt)
        
        self.add_instruction("jump", endif_label)
        self.add_label(else_label)

        # block else (se houver)
        if node[3]:
            for stmt in node[3]:
                self.visit(stmt)

        self.add_label(endif_label)

    def visit_BINOP(self, node):
        op = node[0]
        if op == 'UMINUS':
            self.visit(node[1])
            self.add_instruction('neg')
        elif op == 'NOT':
            self.visit(node[1])
            self.add_instruction('not')
        else:
            self.visit(node[1])
            self.visit(node[2])
            self.add_instruction(self.op_map[op])

    def visit_CONST(self, node):
        t, v = node[1], node[2]
        if t == 'INT':
            self.add_instruction("pushi", v)
        elif t == 'REAL':
            self.add_instruction("pushf", v)
        elif t == 'BOOL':
            self.add_instruction("pushi", 1 if v else 0)
        elif t == 'STRING':
            self.add_instruction("pushs", f'"{v}"')

    def visit_VAR(self, node):
        var_info = self.symbol_table.lookup(node[1], self.current_scope)
        instr = "pushg" if var_info['scope_type'] == 'global' else "pushl"
        self.add_instruction(instr, var_info['address'])

    def visit_LABEL(self, node):
        f_label, statement = node[1], node[2]
        
        self.add_label(self.fortran_labels[f_label])
        self.visit(statement)

        # se for um label de fecho de ciclo DO
        if f_label in self.do_loops:
            loop = self.do_loops[f_label]
            var_info = loop['var_info']
            
            store_instr = "storeg" if var_info['scope_type'] == 'global' else "storel"
            push_instr = "pushg" if var_info['scope_type'] == 'global' else "pushl"

            # i = i + step
            self.add_instruction(push_instr, var_info['address'])
            self.visit(loop['step_expr'])
            self.add_instruction("add")
            self.add_instruction(store_instr, var_info['address'])

            self.add_instruction("jump", loop['start_label'])
            self.add_label(loop['end_label'])

    def visit_GOTO(self, node):
        self.add_instruction("jump", self.fortran_labels[node[1]])

    def visit_DO(self, node):
        f_label, var_name = node[1], node[2]
        var_info = self.symbol_table.lookup(var_name, self.current_scope)

        self.do_loops[f_label] = {
            'start_label': self.new_label("do_start"),
            'end_label': self.new_label("do_end"),
            'var_info': var_info,
            'step_expr': node[5],
            'end_expr': node[4]
        }
        loop = self.do_loops[f_label]
        
        # init (var = start)
        self.visit(node[3])
        store_instr = "storeg" if var_info['scope_type'] == 'global' else "storel"
        self.add_instruction(store_instr, var_info['address'])

        self.add_label(loop['start_label'])

        # stop condition: var > end -> break
        push_instr = "pushg" if var_info['scope_type'] == 'global' else "pushl"
        self.add_instruction(push_instr, var_info['address'])
        self.visit(loop['end_expr'])
        self.add_instruction("sup")
        self.add_instruction("jp", loop['end_label'])

    def visit_CONTINUE(self, node):
        pass # sem ação

    def visit_PRINT(self, node):
        for expr in node[1]:
            self.visit(expr)
            t = self._get_expression_type(expr)
            
            if t == 'INTEGER': self.add_instruction("writei")
            elif t == 'REAL': self.add_instruction("writef")
            elif t == 'LOGICAL': self.add_instruction("writeb")
            elif t == 'CHARACTER': self.add_instruction("writes")
            else: self.add_instruction("writei") # fallback

    def visit_READ(self, node):
        for item in node[1]:
            var_info = self.symbol_table.lookup(item[1], self.current_scope)
            var_type = var_info.get('type')

            if var_type == 'REAL':
                self.add_instruction("readf")
            else:
                self.add_instruction("readi") # fallback inteiro
            
            if item[0] == 'VAR':
                instr = "storeg" if var_info['scope_type'] == 'global' else "storel"
                self.add_instruction(instr, var_info['address'])
            elif item[0] == 'ARRAY_ACCESS':
                self.visit(item) # empilha o address
                self.add_instruction("storei")

    def visit_CALL(self, node):
        name, args = node[1], node[2]
        info = self.symbol_table.lookup(name, self.current_scope)

        if info.get('is_array'):
            # X = ARR(I) - o parser às vezes confunde call com array access, trata-se aqui
            self.visit(('ARRAY_ACCESS', name, args[0], node[3]))
            self.add_instruction("loadi")
        else:
            # right to left para a stack
            for arg_expr in reversed(args):
                self.visit(arg_expr)
            self.add_instruction("call", f"f_{name}", len(args))

    def visit_CALL_STMT(self, node):
        args = node[2]
        for arg_expr in reversed(args):
            self.visit(arg_expr)
        self.add_instruction("call", f"f_{node[1]}", len(args))

    def _setup_subprogram(self, name, params):
        self.add_label(f"f_{name}")
        local_scope = self.symbol_table.scopes[name]
        
        # enter só precisa do espaço para os locals, o caller já tratou dos params
        num_locals_and_params = sum((info.get('size') or 1) for info in local_scope.values() if info.get('scope_type') == 'local')
        self.add_instruction("enter", num_locals_and_params - len(params))

    def visit_SUBROUTINE(self, node):
        name, params, statements = node[1], node[2], node[4]
        self.current_scope = name
        
        self._setup_subprogram(name, params)
        for stmt in statements: self.visit(stmt)

        # safety net de retorno implícito
        self.add_instruction("leave")
        self.add_instruction("ret")
        self.current_scope = 'global'

    def visit_FUNCTION(self, node):
        name, params, statements = node[1], node[3], node[5]
        self.current_scope = name

        self._setup_subprogram(name, params)
        for stmt in statements: self.visit(stmt)

        self.add_instruction("leave")
        self.add_instruction("ret")
        self.current_scope = 'global'

    def visit_RETURN(self, node):
        # se tiver um valor de retorno, está guardado na var local com o nome da func
        if self.current_scope != 'global' and self.symbol_table.scopes['global'][self.current_scope].get('type'):
            self.visit(('VAR', self.current_scope, node[1]))

        self.add_instruction("leave")
        self.add_instruction("ret")