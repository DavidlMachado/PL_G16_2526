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
    # devolve o primeiro PROGRAM, FUNCTION ou SUBROUTINE que aparecer
    for node in ast:
        if node[0] == tag:
            if name is None or node[1] == name:
                return node
    return None

class CodeGenerator:
    def __init__(self, symbol_table, goto_labels):
        self.symbol_table = symbol_table
        self.vm_code = []
        self.goto_labels = goto_labels
        self.label_counter = 0
        self.heap_counter = 0
        self.current_scope = 'global'

        # controlo de fluxo
        self.fortran_labels = {}  # mapeia labels fortran -> labels vm
        self.do_loops = {}        # contexto dos ciclos DO

        # map de operadores da AST para a VM
        self.op_map = {
            '+': 'add', '-': 'sub', '*': 'mul', '/': 'div',
            '**': 'pow', 'POW': 'pow',
            # Versões diretas do Fortran (com pontos)
            '.LT.': 'inf', '.LE.': 'infeq', '.EQ.': 'equal', '.NE.': 'nequal',
            '.GT.': 'sup', '.GE.': 'supeq', '.AND.': 'and', '.OR.': 'or',
            # Versões limpas (para segurança)
            'LT': 'inf', 'LE': 'infeq', 'EQ': 'equal', 'NE': 'nequal',
            'GT': 'sup', 'GE': 'supeq', 'AND': 'and', 'OR': 'or'
        }

    def new_label(self, prefix="L"):
        self.label_counter += 1
        return f"{prefix}{self.label_counter}"

    def add_instruction(self, instr, *args):
        parts = [instr] + [str(a) for a in args]
        self.vm_code.append(' '.join(parts))

    def add_label(self, label):
        self.vm_code.append(f"{label}:")

    def generate(self, ast):
        # alocar memória global (endereços)
        current_address = 0
        global_scope = self.symbol_table.scopes['global']
        # Ordenar por nome para garantir atribuição de endereços determinística
        for name, info in sorted(global_scope.items()):
            if info.get('line') is None:  # builtins têm line=None, salta-os
                continue
            if info.get('is_array') is not None:
                info['address'] = current_address
                info['scope_type'] = 'global'
                size = info.get('size', 1) if info.get('is_array') else 1
                current_address += size

        # mapear labels do fortran
        for l_node in find_nodes(ast, 'LABEL'):
            f_label = l_node[1]
            if f_label not in self.fortran_labels:
                self.fortran_labels[f_label] = self.new_label(f"L{f_label}")

        # start up
        main_program_node = find_unit(ast, 'PROGRAM')
        main_label = f"prog{main_program_node[1]}" if main_program_node and main_program_node[1] else "progmain"

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

        if not isinstance(node, (list, tuple)):
            return

        tag = node[0]

        if tag in self.op_map or tag in ['UMINUS', 'NOT']:
            method_name = "visit_BINOP"
        elif tag == 'ARRAY_ACCESS':
            # Em expressões, ARRAY_ACCESS quer o VALOR não o endereço
            method_name = "visit_ARRAY_ACCESS_value"
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
            info = self.symbol_table.lookup(node[1])
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
        global_scope = self.symbol_table.scopes['global']
        for name, info in sorted(global_scope.items()):
            if info.get('is_array') and info.get('scope_type') == 'global':
                self.add_instruction("pushi", info['size'])
                self.add_instruction("allocn")
                info['heap_index'] = self.heap_counter
                self.heap_counter += 1

        statements = node[3]
        for stmt in statements:
            self.visit(stmt)

    def visit_ASSIGN(self, node):
        target = node[1]

        if target[0] == 'ARRAY_ACCESS':
            self.visit(target)   # stack: [ponteiro_heap, índice]
            self.visit(node[2])  # stack: [ponteiro_heap, índice, valor]
            self.add_instruction("storen")  # guarda heap[índice] = valor

        else:
            self.visit(node[2]) # Avalia a expressão: [Valor]
            var_info = self.symbol_table.lookup(target[1])
            instr = "storeg" if var_info['scope_type'] == 'global' else "storel"
            self.add_instruction(instr, var_info['address'])

    def visit_ARRAY_ACCESS(self, node):
        var_info = self.symbol_table.lookup(node[1])
        index_expr = node[2]

        self.add_instruction("pushst", var_info['heap_index'])
        self.visit(index_expr)
        self.add_instruction("pushi", 1)
        self.add_instruction("sub")

    def visit_ARRAY_ACCESS_value(self, node):
        self.visit_ARRAY_ACCESS(node)   # stack: [ponteiro_heap, índice]
        self.add_instruction("loadn")   # lê heap[índice] como inteiro

    def visit_IF(self, node):
        else_label = self.new_label("ifelse")
        endif_label = self.new_label("ifend")

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
            operand_type = self._get_expression_type(node[1])
            self.visit(node[1])
            if operand_type == 'REAL':
                self.add_instruction('pushf', -1.0)
                self.add_instruction('fmul')
            else:
                self.add_instruction('pushi', -1)
                self.add_instruction('mul')
        elif op == 'NOT':
            self.visit(node[1])
            self.add_instruction('not')
        else:
            # tipos para decidir o tipo das operações
            left_type = self._get_expression_type(node[1])
            right_type = self._get_expression_type(node[2])
            is_float_op = 'REAL' in (left_type, right_type)

            self.visit(node[1])
            self.visit(node[2])

            # apenas estas operações têm float counterparts
            FLOAT_OPS = {'+', '-', '*', '/', '.LT.', '.LE.', '.GT.', '.GE.', 'LT', 'LE', 'GT', 'GE'}

            base_instr = self.op_map[op]
            if is_float_op and op in FLOAT_OPS:
                instr = f"f{base_instr}"
            else:
                instr = base_instr
            self.add_instruction(instr)

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
        var_info = self.symbol_table.lookup(node[1])
        instr = "pushg" if var_info['scope_type'] == 'global' else "pushl"
        self.add_instruction(instr, var_info['address'])

    def visit_LABEL(self, node):
        f_label, statement = node[1], node[2]
        
        if f_label in self.goto_labels:
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
        var_info = self.symbol_table.lookup(var_name)

        self.do_loops[f_label] = {
            'start_label': self.new_label("dostart"),
            'end_label': self.new_label("doend"),
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
        self.add_instruction("infeq") # Verifica se a variável <= end (1 se sim, 0 se não)
        self.add_instruction("jz", loop['end_label']) # Se for 0 (falso), significa que passou o limite, logo salta para o fim

    def visit_CONTINUE(self, node):
        pass # sem ação

    def visit_PRINT(self, node):
        for expr in node[1]:
            self.visit(expr)
            t = self._get_expression_type(expr)
            
            if t == 'INTEGER': self.add_instruction("writei")
            elif t == 'REAL': self.add_instruction("writef")
            elif t == 'LOGICAL': self.add_instruction("writei")
            elif t == 'CHARACTER': self.add_instruction("writes")
            else: self.add_instruction("writei") # fallback
        
        self.add_instruction("writeln")  # newline no fim de cada PRINT

    def visit_READ(self, node):
        for item in node[1]:
            var_info = self.symbol_table.lookup(item[1])
            var_type = var_info.get('type')
            
            if item[0] == 'ARRAY_ACCESS':
                self.visit_ARRAY_ACCESS(item)  # endereço

            self.add_instruction("read")

            if var_type == 'REAL':
                self.add_instruction("atof")
            elif var_type == 'INTEGER' or var_type == 'LOGICAL':
                self.add_instruction("atoi")

            if item[0] == 'VAR':
                instr = "storeg" if var_info['scope_type'] == 'global' else "storel"
                self.add_instruction(instr, var_info['address'])
            elif item[0] == 'ARRAY_ACCESS':
                self.add_instruction("storen")

    def visit_CALL(self, node):
        name, args = node[1], node[2]
        info = self.symbol_table.lookup(name)

        if info.get('is_array'):
            # X = ARR(I) - o parser às vezes confunde call com array access, trata-se aqui
            self.visit_ARRAY_ACCESS_value(('ARRAY_ACCESS', name, args[0], node[3]))
            return
        else:
            if name == 'MOD':
                # O MOD(A, B) precisa do A e depois do B na stack. A instrução da VM é 'mod'
                self.visit(args[0])
                self.visit(args[1])
                self.add_instruction("mod")
                return
            # right to left para a stack
            for arg_expr in reversed(args):
                self.visit(arg_expr)
            self.add_instruction("pusha", f"f{name}")
            self.add_instruction("call")

    def visit_CALL_STMT(self, node):
        args = node[2]
        for arg_expr in reversed(args):
            self.visit(arg_expr)
        self.add_instruction("pusha", f"f{node[1]}")
        self.add_instruction("call")

    def _setup_subprogram(self, name, params):
        self.add_label(f"f{name}")
        local_scope = self.symbol_table.scopes[name]
        
        # Atribui índices negativos aos parâmetros (chegam antes do fp)
        for i, param_name in enumerate(params):
            if param_name in local_scope:
                local_scope[param_name]['address'] = -(i + 1)
                local_scope[param_name]['scope_type'] = 'local'
        
        # Conta só as variáveis locais (não parâmetros)
        n_locals = sum(
            (info.get('size') or 1)
            for name2, info in local_scope.items()
            if info.get('scope_type') == 'local' and name2 not in params
        )
        
        if n_locals > 0:
            self.add_instruction("pushn", n_locals)
    
        # Reatribui offsets positivos às locais (começando em 0)
        current_offset = 0
        for name2, info in local_scope.items():
            if name2 not in params:
                info['address'] = current_offset
                info['scope_type'] = 'local'
                size = info.get('size', 1) if info.get('is_array') else 1
                current_offset += size

    def visit_SUBROUTINE(self, node):
        name, params, statements = node[1], node[2], node[4]
        self.current_scope = name
        self.symbol_table.enter_scope(name)
        
        self._setup_subprogram(name, params)
        for stmt in statements: self.visit(stmt)

        # safety net de retorno implícito
        self.add_instruction("return")

        self.current_scope = 'global'
        self.symbol_table.leave_scope()

    def visit_FUNCTION(self, node):
        name, params, statements = node[1], node[3], node[5]
        self.current_scope = name
        self.symbol_table.enter_scope(name)

        self._setup_subprogram(name, params)
        for stmt in statements: self.visit(stmt)

        self.add_instruction("return")

        self.current_scope = 'global'
        self.symbol_table.leave_scope()

    def visit_RETURN(self, node):
        """
        Se estiver numa FUNCTION, empurra o valor de retorno (variável local
        com o nome da função) para o topo da stack antes do return.
        """
        if self.current_scope != 'global':
            global_info = self.symbol_table.scopes['global'].get(self.current_scope)
            # Só empurra se for FUNCTION (tem tipo de retorno), não SUBROUTINE
            if global_info and global_info.get('type') is not None:
                local_scope = self.symbol_table.scopes[self.current_scope]
                ret_var = local_scope.get(self.current_scope)
                if ret_var:
                    self.add_instruction("pushl", ret_var['address'])

        self.add_instruction("return")