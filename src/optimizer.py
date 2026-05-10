class Optimizer:
    def __init__(self, symbol_table):
        """
        Recebe a symbol_table já preenchida pelo SemanticAnalyzer.
        Assim sabemos quais variáveis e funções foram marcadas como 'used'.
        """
        self.symbol_table = symbol_table
        # Lista de otimizações feitas
        self.optimizations = []
        # Lista de Binops para redirecionar no optimize_node
        self.BINOPS = {'+', '-', '*', '/', '**', 'LT', 'LE', 'EQ', 'NE', 'GT', 'GE', 'AND', 'OR'}

    def log(self, msg):
        # regista as otimizações feitas
        self.optimizations.append(msg)
        print(f"[OPTIMIZER] {msg}")

    # -------------------------------------------------------------------------
    # Ponto de entrada
    # -------------------------------------------------------------------------

    def optimize(self, ast):
        """
        Recebe uma ast não otimizada e percorre-a procurando por otimizações que possam ser feitas, 
        devolvendo uma nova ast com as otimizações implementadas.
        """
        new_ast = []
        
        for node in ast:
            optimized = self.optimize_node(node)
            
            if optimized is not None:
                new_ast.append(optimized)

        return new_ast

    def optimize_node(self, node):
        """Direciona cada nodo para o método correto."""
        if node is None:
            return None

        # Operadores binários têm tags que não geram nomes de métodos válidos
        if node[0] in self.BINOPS:
            return self.optimize_BINOP(node)

        # Vai buscar o method name a partir da tag do nodo
        method_name = f"optimize_{node[0]}"

        optimizer = getattr(self, method_name, None)

        if optimizer is None:
            return node

        return optimizer(node)

    # -------------------------------------------------------------------------
    # Otimização de nodes do programa
    # -------------------------------------------------------------------------

    def optimize_PROGRAM(self, node):
        """Recebe um nodo do tipo ('PROGRAM', nome, declarações, statements) e otimiza as declarações e statements."""
        name = node[1]
        decls = node[2]
        stmts = node[3]

        # Visita as declarações e statements para as otimizar
        new_decls = self.optimize_declarations(decls)
        new_stmts = self.optimize_statements(stmts)

        return ('PROGRAM', name, new_decls, new_stmts)

    def optimize_subprogram(self, node, is_function):
        """Lógica comum entre FUNCTION e SUBROUTINE."""
        name = node[1]

        if is_function:
            return_type = node[2]
            params = node[3]
            decls = node[4]
            stmts = node[5]
            line  = node[-1]
        else:
            params = node[2]
            decls = node[3]
            stmts = node[4]
            line = node[-1]

        global_scope = self.symbol_table.scopes.get('global')
        info = global_scope.get(name)

        if not info['used']:
            kind = 'Função' if is_function else 'Subrotina'
            self.log(f"{kind} '{name}' removida (nunca chamada).")
            return None

        new_decls = self.optimize_declarations(decls, name)
        new_stmts = self.optimize_statements(stmts)

        if is_function:
            return ('FUNCTION', name, return_type, params, new_decls, new_stmts, line)
        else:
            return ('SUBROUTINE', name, params, new_decls, new_stmts, line)

    def optimize_FUNCTION(self, node):
        """
        Recebe um nodo do tipo('FUNCTION', nome, tipo_retorno, params, declarações, statements, line)
        e verifica se a função é utilizada. Se n for remove a função para otimizar o programa, mas se ela
        for utilizada ele percorre as suas declarações e statements e otimiza-os.
        """
        return self.optimize_subprogram(node, True)

    def optimize_SUBROUTINE(self, node):
        """
        Recebe um nodo do tipo('SUBROUTINE', nome, params, declarações, statements, line)
        e verifica se a função é utilizada. Se n for remove a função para otimizar o programa, mas se ela
        for utilizada ele percorre as suas declarações e statements e otimiza-os.
        """
        return self.optimize_subprogram(node, False)

    # -------------------------------------------------------------------------
    # Otimização de statements e declarações
    # -------------------------------------------------------------------------

    def optimize_declarations(self, decls, scope='global'):
        """
        Recebe um nodo do tipo ('DECLARE', tipo, [('SCALAR'/'ARRAY', nome, ...), ...])
        e remove declarações de variáveis que nunca foram usadas.
        """
        # Vamos buscar o scope
        scope_vars = self.symbol_table.scopes.get(scope)
        new_decls = []

        for decl in decls:
            type_val = decl[1]
            var_list = decl[2]

            new_var_list = []
            for var in var_list:
                # Percorremos cada variável da declaração e verificamos se ela foi usada indo buscar a sua informação à symbol table
                var_name = var[1]
                var_info = scope_vars.get(var_name)

                if not var_info['used']:
                    self.log(f"Variável '{var_name}' removida do scope '{scope}' (nunca usada).")
                else:
                    new_var_list.append(var)

            # Apenas mantemos a declaração se houver variáveis utilizadas
            if new_var_list:
                new_decls.append(('DECLARE', type_val, new_var_list))

        return new_decls

    def optimize_statements(self, stmts):
        """
        Percorre a lista de statements e aplica Dead Code Elimination.
        Quando encontra um GOTO incondicional, descarta tudo o que vem
        a seguir até ao próximo LABEL (que pode ser destino de outro salto).
        """
        new_stmts = []
        # Contador manual para percorrer os statements
        i = 0

        """
        Usamos um contador pq se encontrarmos um GOTO 
        temos que verificar se ele tem deadcode a seguir a ele
        incrementando manualmente o contador
        """

        while i < len(stmts):
            stmt = stmts[i]

            # verifica se chegou a um GOTO se chegar, ele é incondicional e o codigo até a proxima label é dead code
            if stmt[0] == 'GOTO':
                new_stmts.append(stmt) # Mantem o GOTO
                line = stmt[-1]
                skipped = [] # Regista se houve dead code para poder ter um log
                i += 1 # avançamos o contador
                while i < len(stmts):
                    next_stmt = stmts[i]
                    # Se chega a uma label para a procura
                    if next_stmt[0] == 'LABEL':
                        break
                    # Se for codigo que nao seja uma label adiciona ao skipped
                    skipped.append(next_stmt)
                    i += 1

                if skipped:
                    # Da log do número de instruções removidas e do OOTO em questão
                    self.log(f"Dead code removido: {len(skipped)} instruções removidas após GOTO incondicional na linha {line}")

                continue

            # Só otimiza os internos se o statement não for eliminado
            optimized = self.optimize_node(stmt)
            if optimized is not None:
                if isinstance(optimized, list):  # IF(.TRUE.) ou IF(.FALSE.) devolveu lista
                    new_stmts.extend(optimized)
                else:
                    new_stmts.append(optimized)

            i += 1
        
        return new_stmts

    def optimize_IF(self, node):
        """Recebe um nodo do tipo ('IF', condition, then_block, else_block, line) e otimiza os blocos internos."""
        condition = node[1]
        then_block = node[2]
        else_block = node[3]
        line = node[-1]
        
        # Otimiza primeiro a condição
        new_condition = self.optimize_node(condition)

        # Verifica se a condição é uma constante booleana estática
        if new_condition[0] == 'CONST' and new_condition[1] == 'BOOL':
            is_true = new_condition[2]
            
            if is_true:
                self.log(f"IF (.TRUE.) detetado na linha {line}. Ramo ELSE removido.")
                # Como é TRUE, o else é lixo. Só otimizamos e devolvemos o then.
                # Devolvemos a lista de statements diretamente!
                return self.optimize_statements(then_block)
            else:
                self.log(f"IF (.FALSE.) detetado na linha {line}. Ramo THEN removido.")
                # Como é FALSE, o then é lixo. Só otimizamos e devolvemos o else.
                if not else_block:
                    return None # Se não havia else, o if inteiro desaparece!
                return self.optimize_statements(else_block)

        # Otimiza recursivamente cada um dos blocos 
        new_then_block = self.optimize_statements(then_block)
        new_else_block = self.optimize_statements(else_block)

        return ('IF', new_condition, new_then_block, new_else_block, line)

    def optimize_LABEL(self, node):
        """Recebe um nodo do tipo ('LABEL', num, instrução, line) e otimiza a instrução dentro do label."""
        label_num = node[1]
        instruction = node[2]
        line = node[-1]

        # Otimiza a instrução
        new_instruction = self.optimize_node(instruction)

        return ('LABEL', label_num, new_instruction, line)

    def optimize_DO(self, node):
        """Recebe um nodo ('DO', label, var, start, end, step, line) e otimiza as expressões de controlo."""
        label = node[1]
        var   = node[2]
        start = node[3]
        end   = node[4]
        step  = node[5]
        line  = node[-1]

        # Otimiza as expressões de início, fim e passo
        new_start = self.optimize_node(start)
        new_end   = self.optimize_node(end)
        new_step  = self.optimize_node(step)

        return ('DO', label, var, new_start, new_end, new_step, line)

    def optimize_ASSIGN(self, node):
        """Recebe um nodo ('ASSIGN', target, expression, line) e otimiza a expressão do lado direito."""
        target     = node[1]
        expression = node[2]
        line       = node[-1]

        # Otimiza a expressão do lado direito
        new_expression = self.optimize_node(expression)

        return ('ASSIGN', target, new_expression, line)

    def optimize_PRINT(self, node):
        """Recebe um nodo ('PRINT', expression_list) e otimiza cada expressão da lista."""
        new_expression_list = [self.optimize_node(expr) for expr in node[1]]
        return ('PRINT', new_expression_list)

    def optimize_CALL_STMT(self, node):
        """Recebe um nodo ('CALL_STMT', name, args_list) e otimiza os argumentos."""
        name = node[1]
        new_args_list = [self.optimize_node(arg) for arg in node[2]]
        return ('CALL_STMT', name, new_args_list)

    def optimize_CALL(self, node):
        """Recebe um nodo ('CALL', name, args_list, line) e otimiza os argumentos."""
        name = node[1]
        line = node[-1]
        new_args_list = [self.optimize_node(arg) for arg in node[2]]
        return ('CALL', name, new_args_list, line)

    def optimize_ARRAY_ACCESS(self, node):
        """Recebe um nodo ('ARRAY_ACCESS', name, index_expr, line) e otimiza o índice."""
        name = node[1]
        line = node[-1]
        new_index = self.optimize_node(node[2])
        return ('ARRAY_ACCESS', name, new_index, line)

    # -------------------------------------------------------------------------
    # Otimização de operações matemáticas
    # -------------------------------------------------------------------------

    def optimize_BINOP(self, node):
        """
        Recebe um nodo do tipo (op, left, right, line) e verifica se ambos os operandos
        são constantes. Se forem, calcula o resultado em tempo de compilação (constant folding)
        e substitui o nodo por uma constante com o resultado. Caso contrário, devolve o nodo
        sem alterações.
        """
        # Dicionário que mapeia as operações
        ops = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b,
            '**': lambda a, b: a ** b,
            'AND': lambda a, b: a and b,
            'OR':  lambda a, b: a or b,
            'LT': lambda a, b: a < b,
            'LE': lambda a, b: a <= b,
            'EQ': lambda a, b: a == b,
            'NE': lambda a, b: a != b,
            'GT': lambda a, b: a > b,
            'GE': lambda a, b: a >= b,
        }

        op = node[0]
        left = node[1]
        right = node[2]
        line = node[-1]

        # Simplifica cada lado primeiro
        optimized_left = self.optimize_node(left)
        optimized_right = self.optimize_node(right)
        
        # Só aplica constant folding se ambos forem constantes e o op estiver no dicionário
        if optimized_left[0] == 'CONST' and optimized_right[0] == 'CONST' and op in ops:
            try:
                # Regra especial para a divisão de dois inteiros no Fortran
                if op == '/' and optimized_left[1] == 'INT' and optimized_right[1] == 'INT':
                    res = optimized_left[2] // optimized_right[2]
                else:
                    res = ops[op](optimized_left[2], optimized_right[2])

                res_type = 'REAL' if isinstance(res, float) else ('BOOL' if isinstance(res, bool) else 'INT')
                self.log(f"Constant folding: {optimized_left[2]} {op} {optimized_right[2]} → {res} (linha {line})")
                return ('CONST', res_type, res, line)

            except ZeroDivisionError:
                self.log(f"Aviso: Divisão por zero detetada na linha {line}. Constant folding abortado.")

        # Se não for possível simplificar ou a operação não estiver no dicionario, 
        # devolve o nodo com os filhos já otimizados
        return (op, optimized_left, optimized_right, line)

    def optimize_unary(self, node, result_type, operation):
        """Lógica comum entre UMINUS e NOT."""
        line = node[-1]
        operand = self.optimize_node(node[1])

        # Se é uma constante simplifica a expressão
        if operand[0] == 'CONST':
            # executa a operação no operando
            res = operation(operand[2])
            # regista o tipo final
            final_type = result_type if result_type else operand[1]
            self.log(f"Constant folding: {node[0]} {operand[2]} → {res} (linha {line})")
            return ('CONST', final_type, res, line)

        # Se não retorna o operando otimizado
        return (node[0], operand, line)

    def optimize_UMINUS(self, node):
        """Recebe um nodo ('UMINUS', expression, line) e nega o valor se for uma constante numérica."""
        return self.optimize_unary(node, None, lambda x: -x)

    def optimize_NOT(self, node):
        """Recebe um nodo ('NOT', expression, line) e inverte o valor se for uma constante booleana."""
        return self.optimize_unary(node, 'BOOL', lambda x: not x)

    # -------------------------------------------------------------------------
    # Relatório final
    # -------------------------------------------------------------------------
 
    def report(self):
        print("\n--- Relatório do Optimizer ---")
        if not self.optimizations:
            print("Nenhuma otimização aplicada.")
        else:
            for i, opt in enumerate(self.optimizations, 1):
                print(f"  {i}. {opt}")
        print(f"Total: {len(self.optimizations)} otimização(ões).\n")



    






        

    