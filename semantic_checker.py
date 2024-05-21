from typing import List, Optional

import visitor
from semantic_base import TypeDesc, ScopeType, SemanticException, BIN_OP_TYPE_COMPATIBILITY, TYPE_CONVERTIBILITY, \
    IdentScope, IdentDesc, BinOp, COMB_EQ_OP_TYPE_COMPATIBILITY, CombEqOp, UNAR_OP_TYPE_COMPATIBILITY, UnarOp
from mel_ast import AstNode, LiteralNode, IdentNode, BinOpNode, ExprNode, CallNode, \
    VarsDeclNode, FuncDeclNode, FuncParamsNode, AssignNode, ReturnOpNode, IfNode, WhileNode, ForNode, StmtListNode, \
    TypeConvertNode, EMPTY_STMT, EMPTY_IDENT, CombEqNode, UnarOpNode, TernaryNode, TryNode, CatchBlockNode, \
    FinallyBlockNode, TryBlockNode

BUILT_IN_OBJECTS = '''
    string read() { }
    void print(string p0) { }
    void println(string p0) { }
    int to_int(string p0) { }
    float to_float(string p0) { }
'''


def type_convert(expr: ExprNode, type_: TypeDesc, except_node: Optional[AstNode] = None, comment: Optional[str] = None) -> ExprNode:
    """Метод преобразования ExprNode узла AST-дерева к другому типу
    :param expr: узел AST-дерева
    :param type_: требуемый тип
    :param except_node: узел, о которого будет исключение
    :param comment: комментарий
    :return: узел AST-дерева c операцией преобразования
    """

    if expr.node_type is None:
        except_node.semantic_error('Тип выражения не определен')
    if expr.node_type == type_:
        return expr
    if expr.node_type.is_simple and type_.is_simple and \
            expr.node_type.base_type in TYPE_CONVERTIBILITY and type_.base_type in TYPE_CONVERTIBILITY[expr.node_type.base_type]:
        return TypeConvertNode(expr, type_)
    else:
        (except_node if except_node else expr).semantic_error('Тип {0}{2} не конвертируется в {1}'.format(
            expr.node_type, type_, ' ({})'.format(comment) if comment else ''
        ))


class SemanticChecker:
    """Класс для проверки семантики.

       Сейчас поддерживаются только примитивные типы данных и функции.
       Для поддержки сложных типов (массивы и т.п.) должен быть доработан.
    """

    @visitor.on('AstNode')
    def semantic_check(self, AstNode):
        """
        Нужен для работы модуля visitor (инициализации диспетчера)
        """
        pass

    @visitor.when(LiteralNode)
    def semantic_check(self, node: LiteralNode, scope: IdentScope):
        if isinstance(node.value, bool):
            node.node_type = TypeDesc.BOOL
        # проверка должна быть позже bool, т.к. bool наследник от int
        elif isinstance(node.value, int):
            node.node_type = TypeDesc.INT
        elif isinstance(node.value, float):
            node.node_type = TypeDesc.FLOAT
        elif isinstance(node.value, str):
            node.node_type = TypeDesc.STR
        else:
            node.semantic_error('Неизвестный тип {} для {}'.format(type(node.value), node.value))

    @visitor.when(IdentNode)
    def semantic_check(self, node: IdentNode, scope: IdentScope):
        ident = scope.get_ident(node.name)
        if ident is None:
            try:
                node.node_type = TypeDesc.from_str(node.name)
            except SemanticException:
                node.semantic_error('Идентификатор {} не найден и не является верным типом данных'.format(node.name))
        else:
            node.node_type = ident.type
            node.node_ident = ident

    @visitor.when(TernaryNode)
    def semantic_check(self, node: TernaryNode, scope: IdentScope):
        node.cond.semantic_check(self, scope)
        if node.cond.node_type != TypeDesc.BOOL:
            node.semantic_error('Условное выражение должно иметь тип bool')

        node.true_expr.semantic_check(self, scope)
        node.false_expr.semantic_check(self, scope)

        if node.true_expr.node_type != node.false_expr.node_type:
            node.semantic_error('Типы выражений true и false должны быть одинаковыми')

        node.node_type = node.true_expr.node_type

    @visitor.when(BinOpNode)
    def semantic_check(self, node: BinOpNode, scope: IdentScope):
        node.arg1.semantic_check(self, scope)
        node.arg2.semantic_check(self, scope)

        if node.arg1.node_type.is_simple or node.arg2.node_type.is_simple:
            compatibility = BIN_OP_TYPE_COMPATIBILITY[BinOp.__getitem__(node.op.name)]
            args_types = (node.arg1.node_type.base_type, node.arg2.node_type.base_type)
            if args_types in compatibility:
                node.node_type = TypeDesc.from_base_type(compatibility[args_types])
                return

            if node.arg2.node_type.base_type in TYPE_CONVERTIBILITY:
                for arg2_type in TYPE_CONVERTIBILITY[node.arg2.node_type.base_type]:
                    args_types = (node.arg1.node_type.base_type, arg2_type)
                    if args_types in compatibility:
                        node.arg2 = type_convert(node.arg2, TypeDesc.from_base_type(arg2_type))
                        node.node_type = TypeDesc.from_base_type(compatibility[args_types])
                        return
            if node.arg1.node_type.base_type in TYPE_CONVERTIBILITY:
                for arg1_type in TYPE_CONVERTIBILITY[node.arg1.node_type.base_type]:
                    args_types = (arg1_type, node.arg2.node_type.base_type)
                    if args_types in compatibility:
                        node.arg1 = type_convert(node.arg1, TypeDesc.from_base_type(arg1_type))
                        node.node_type = TypeDesc.from_base_type(compatibility[args_types])
                        return

        node.semantic_error("Оператор {} не применим к типам ({}, {})".format(
            node.op, node.arg1.node_type, node.arg2.node_type
        ))

    @visitor.when(CombEqNode)
    def semantic_check(self, node: CombEqNode, scope: IdentScope):
        node.arg1.semantic_check(self, scope)
        node.arg2.semantic_check(self, scope)

        if node.arg1.node_type.is_simple or node.arg2.node_type.is_simple:
            compatibility = COMB_EQ_OP_TYPE_COMPATIBILITY[CombEqOp.__getitem__(node.op.name)]
            args_types = (node.arg1.node_type.base_type, node.arg2.node_type.base_type)
            if args_types in compatibility:
                node.node_type = TypeDesc.from_base_type(compatibility[args_types])
                return

            if node.arg2.node_type.base_type in TYPE_CONVERTIBILITY:
                for arg2_type in TYPE_CONVERTIBILITY[node.arg2.node_type.base_type]:
                    args_types = (node.arg1.node_type.base_type, arg2_type)
                    if args_types in compatibility:
                        node.arg2 = type_convert(node.arg2, TypeDesc.from_base_type(arg2_type))
                        node.node_type = TypeDesc.from_base_type(compatibility[args_types])
                        return
            if node.arg1.node_type.base_type in TYPE_CONVERTIBILITY:
                for arg1_type in TYPE_CONVERTIBILITY[node.arg1.node_type.base_type]:
                    args_types = (arg1_type, node.arg2.node_type.base_type)
                    if args_types in compatibility:
                        node.arg1 = type_convert(node.arg1, TypeDesc.from_base_type(arg1_type))
                        node.node_type = TypeDesc.from_base_type(compatibility[args_types])
                        return

        node.semantic_error("Оператор {} не применим к типам ({}, {})".format(
            node.op, node.arg1.node_type, node.arg2.node_type
        ))

    @visitor.when(UnarOpNode)
    def semantic_check(self, node: UnarOpNode, scope: IdentScope):
        node.arg.semantic_check(self, scope)

        if node.arg.node_type.is_simple:
            compatibility = UNAR_OP_TYPE_COMPATIBILITY[UnarOp.__getitem__(node.op.name)]
            args_type = node.arg.node_type.base_type
            if args_type in compatibility:
                node.node_type = TypeDesc.from_base_type(compatibility[args_type])
                return

        node.semantic_error("Оператор {} не применим к типу {}".format(
            node.op, node.arg.node_type
        ))

    @visitor.when(CallNode)
    def semantic_check(self, node: CallNode, scope: IdentScope):
        func = scope.get_ident(node.func.name)
        if func is None:
            node.semantic_error('Функция {} не найдена'.format(node.func.name))
        if not func.type.func:
            node.semantic_error('Идентификатор {} не является функцией'.format(func.name))
        if len(func.type.params) != len(node.params):
            node.semantic_error('Кол-во аргументов {} не совпадает (ожидалось {}, передано {})'.format(
                func.name, len(func.type.params), len(node.params)
            ))
        params = []
        error = False
        decl_params_str = fact_params_str = ''
        for i in range(len(node.params)):
            param: ExprNode = node.params[i]
            param.semantic_check(self, scope)
            if len(decl_params_str) > 0:
                decl_params_str += ', '
            decl_params_str += str(func.type.params[i])
            if len(fact_params_str) > 0:
                fact_params_str += ', '
            fact_params_str += str(param.node_type)
            try:
                params.append(type_convert(param, func.type.params[i]))
            except:
                error = True
        if error:
            node.semantic_error('Фактические типы ({1}) аргументов функции {0} не совпадают с формальными ({2})\
                                            и не приводимы'.format(
                func.name, fact_params_str, decl_params_str
            ))
        else:
            node.params = tuple(params)
            node.func.node_type = func.type
            node.func.node_ident = func
            node.node_type = func.type.return_type

    @visitor.when(AssignNode)
    def semantic_check(self, node: AssignNode, scope: IdentScope):
        node.var.semantic_check(self, scope)
        node.val.semantic_check(self, scope)
        node.val = type_convert(node.val, node.var.node_type, node, 'присваиваемое значение')
        node.node_type = node.var.node_type

    @visitor.when(VarsDeclNode)
    def semantic_check(self, node: VarsDeclNode, scope: IdentScope):
        node.type.semantic_check(self, scope)
        for var in node.vars:
            var_node: IdentNode = var.var if isinstance(var, AssignNode) else var
            try:
                scope.add_ident(IdentDesc(var_node.name, node.type.type))
            except SemanticException as e:
                var_node.semantic_error(e.message)
            var.semantic_check(self, scope)
        node.node_type = TypeDesc.VOID

    @visitor.when(ReturnOpNode)
    def semantic_check(self, node: ReturnOpNode, scope: IdentScope):
        node.arg.semantic_check(self, IdentScope(scope))
        func = scope.curr_func
        if func is None:
            node.semantic_error('Оператор return применим только к функции')
        node.arg = type_convert(node.arg, func.func.type.return_type, node, 'возвращаемое значение')
        node.node_type = TypeDesc.VOID

    @visitor.when(TryNode)
    def semantic_check(self, node: TryNode, scope: IdentScope):
        if node.catch_clauses == EMPTY_STMT and node.finally_block == EMPTY_STMT:
            node.semantic_error('Оператор try должен иметь хотя бы один из блоков catch или finally')

        node.try_block.semantic_check(self, scope)

        if node.catch_clauses != EMPTY_STMT:
            self.semantic_check(node.catch_clauses, scope)

        if node.finally_block != EMPTY_STMT:
            self.semantic_check(node.finally_block, scope)

        node.node_type = TypeDesc.VOID

    @visitor.when(TryBlockNode)
    def semantic_check(self, node: TryBlockNode, scope: IdentScope):
        node.block.semantic_check(self, scope)
        node.node_type = TypeDesc.VOID

    @visitor.when(CatchBlockNode)
    def semantic_check(self, node: CatchBlockNode, scope: IdentScope):
        node.exception_var.semantic_check(self, scope)
        if node.exception_var.type.type != TypeDesc.EXCEPTION:
            node.exception_var.semantic_error("Параметр catch блока должен быть типа Exception")

        node.block.semantic_check(self, scope)
        node.node_type = TypeDesc.VOID

    @visitor.when(FinallyBlockNode)
    def semantic_check(self, node: FinallyBlockNode, scope: IdentScope):
        node.block.semantic_check(self, scope)
        node.node_type = TypeDesc.VOID

    @visitor.when(IfNode)
    def semantic_check(self, node: IfNode, scope: IdentScope):
        node.cond.semantic_check(self, scope)
        node.cond = type_convert(node.cond, TypeDesc.BOOL, None, 'условие')
        node.then_stmt.semantic_check(self, IdentScope(scope))
        if node.else_stmt:
            node.else_stmt.semantic_check(self, IdentScope(scope))
        node.node_type = TypeDesc.VOID

    @visitor.when(WhileNode)
    def semantic_check(self, node: WhileNode, scope: IdentScope):
        node.cond.semantic_check(self, scope)
        node.cond = type_convert(node.cond, TypeDesc.BOOL, None, 'условие')
        node.body.semantic_check(self, IdentScope(scope))
        node.node_type = TypeDesc.VOID

    @visitor.when(ForNode)
    def semantic_check(self, node: ForNode, scope: IdentScope):
        scope = IdentScope(scope)
        node.init.semantic_check(self, scope)
        if node.cond == EMPTY_STMT:
            node.cond = LiteralNode('true')
        node.cond.semantic_check(self, scope)
        node.cond = type_convert(node.cond, TypeDesc.BOOL, None, 'условие')
        node.step.semantic_check(self, scope)
        node.body.semantic_check(self, IdentScope(scope))
        node.node_type = TypeDesc.VOID

    @visitor.when(FuncParamsNode)
    def semantic_check(self, node: FuncParamsNode, scope: IdentScope):
        node.type.semantic_check(self, scope)
        node.name.node_type = node.type.type
        try:
            node.name.node_ident = scope.add_ident(IdentDesc(node.name.name, node.type.type, ScopeType.PARAM))
        except SemanticException:
            raise node.name.semantic_error('Параметр {} уже объявлен'.format(node.name.name))
        node.node_type = TypeDesc.VOID

    @visitor.when(FuncDeclNode)
    def semantic_check(self, node: FuncDeclNode, scope: IdentScope):
        if scope.curr_func:
            node.semantic_error(
                "Объявление функции ({}) внутри другой функции не поддерживается".format(node.name.name))
        parent_scope = scope
        node.type.semantic_check(self, scope)
        scope = IdentScope(scope)

        # временно хоть какое-то значение, чтобы при добавлении параметров находить scope функции
        scope.func = EMPTY_IDENT
        params: List[TypeDesc] = []
        for param in node.params:
            # при проверке параметров происходит их добавление в scope
            param.semantic_check(self, scope)
            param.node_ident = scope.get_ident(param.name.name)
            params.append(param.type.type)

        type_ = TypeDesc(None, node.type.type, tuple(params))
        func_ident = IdentDesc(node.name.name, type_)
        scope.func = func_ident
        node.name.node_type = type_
        try:
            node.name.node_ident = parent_scope.curr_global.add_ident(func_ident)
        except SemanticException as e:
            node.name.semantic_error("Повторное объявление функции {}".format(node.name.name))
        node.body.semantic_check(self, scope)

        node.node_type = type_.return_type

    @visitor.when(StmtListNode)
    def semantic_check(self, node: StmtListNode, scope: IdentScope):
        if not node.program:
            scope = IdentScope(scope)
        for stmt in node.exprs:
            stmt.semantic_check(self, scope)
        node.node_type = TypeDesc.VOID


def prepare_global_scope() -> IdentScope:
    from mel_parser import parse
    prog = parse(BUILT_IN_OBJECTS)
    checker = SemanticChecker()
    scope = IdentScope()
    checker.semantic_check(prog, scope)
    for name, ident in scope.idents.items():
        ident.built_in = True
    scope.var_index = 0
    return scope
