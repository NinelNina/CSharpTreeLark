from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Callable, Tuple, Optional, Union, List
from enum import Enum
from semantic_base import TypeDesc, SemanticException, TYPE_CONVERTIBILITY, \
    IdentScope, IdentDesc


class AstNode(ABC):
    init_action: Callable[['AstNode'], None] = None

    def __init__(self, row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__()
        self.row = row
        self.col = col
        for k, v in props.items():
            setattr(self, k, v)
        if AstNode.init_action is not None:
            AstNode.init_action(self)
        self.node_type: Optional[TypeDesc] = None
        self.node_ident: Optional[IdentDesc] = None

    @property
    def childs(self) -> Tuple['AstNode', ...]:
        return ()

    @abstractmethod
    def __str__(self) -> str:
        pass

    def to_str(self):
        return str(self)

    def to_str_full(self):
        r = ''
        if self.node_ident:
            r = str(self.node_ident)
        elif self.node_type:
            r = str(self.node_type)
        return self.to_str() + (' : ' + r if r else '')

    def semantic_error(self, message: str):
        raise SemanticException(message, self.row, self.col)

    def semantic_check(self, checker, scope: IdentScope) -> None:
        checker.semantic_check(self, scope)

    @property
    def tree(self) -> [str, ...]:
        r = [self.to_str_full()]
        childs = self.childs
        for i, child in enumerate(childs):
            ch0, ch = '├', '│'
            if i == len(childs) - 1:
                ch0, ch = '└', ' '
            r.extend(((ch0 if j == 0 else ch) + ' ' + s for j, s in enumerate(child.tree)))
        return tuple(r)

    def __getitem__(self, index):
        return self.childs[index] if index < len(self.childs) else None

    def visit(self, func: Callable[['AstNode'], None]) -> None:
        func(self)
        map(func, self.childs)

    def __getitem__(self, index):
        return self.childs[index] if index < len(self.childs) else None


class ExprNode(AstNode):
    pass


class LiteralNode(ExprNode):
    def __init__(self, literal: str,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.literal = literal
        if literal in ('true', 'false'):
            self.value = bool(literal)
        else:
            self.value = eval(literal)

    def __str__(self) -> str:
        return self.literal


class IdentNode(ExprNode):
    def __init__(self, name: str,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.name = str(name)
        self.type = None
        with suppress(SemanticException):
           self.type = TypeDesc.from_str(self.name)

    def __str__(self) -> str:
        return str(self.name)


class BinOp(Enum):
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    QMARK = '?'
    COLON = ':'
    GE = '>='
    LE = '<='
    NEQUALS = '!='
    EQUALS = '=='
    GT = '>'
    LT = '<'
    BIT_AND = '&'
    BIT_OR = '|'
    LOGICAL_AND = '&&'
    LOGICAL_OR = '||'

    def __str__(self):
        return self.value


class CombEqOp(Enum):
    ADD_EQ = '+='
    SUB_EQ = '-='
    MULT_EQ = '*='
    DIV_EQ = '/='

    def __str__(self):
        return self.value


class BinOpNode(ExprNode):
    def __init__(self, op: BinOp, arg1: ExprNode, arg2: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2

    @property
    def childs(self) -> Tuple[ExprNode, ExprNode]:
        return self.arg1, self.arg2

    def __str__(self) -> str:
        return str(self.op.value)


class CombEqNode(ExprNode):
    def __init__(self, op: CombEqOp, arg1: ExprNode, arg2: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2

    @property
    def childs(self) -> Tuple[ExprNode, ExprNode]:
        return self.arg1, self.arg2

    def __str__(self) -> str:
        return str(self.op.value)


class UnarOp(Enum):
    INC = '++'
    DEC = '--'
    NOT = '!'
    RETURN = 'return'

    def __str__(self):
        return self.value


class UnarOpNode(ExprNode):
    def __init__(self, op: UnarOp, arg: ExprNode, string: Optional[str], row: Optional[int] = None,
                 col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.op = op
        self.arg = arg
        self.string = string

    @property
    def childs(self) -> Tuple[ExprNode]:
        return (self.arg,)

    def __str__(self) -> str:
        return str(self.op.value) + self.string


class StmtNode(ExprNode):
    pass


class VarsDeclNode(StmtNode):
    def __init__(self, type_: StmtNode, *vars: Tuple[AstNode, ...],
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.type = type_
        self.vars = vars

    @property
    def childs(self) -> Tuple[ExprNode, ...]:
        # return self.vars_type, (*self.vars_list)
        return (self.type,) + self.vars

    def __str__(self) -> str:
        return 'var'


class FuncParamsNode(StmtNode):
    def __init__(self, type_: IdentNode, name: AstNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.type = type_
        self.name = name

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return (self.name,)

    def __str__(self) -> str:
        return self.type.__str__()


class CallNode(StmtNode):
    def __init__(self, func: IdentNode, *params: Tuple[ExprNode],
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.func = func
        self.params = params

    @property
    def childs(self) -> Tuple[IdentNode, ...]:
        # return self.func, (*self.params)
        return (self.func,) + self.params

    def __str__(self) -> str:
        return 'call'


class AssignNode(StmtNode):
    def __init__(self, var: IdentNode, val: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.var = var
        self.val = val

    @property
    def childs(self) -> Tuple[IdentNode, ExprNode]:
        return self.var, self.val

    def __str__(self) -> str:
        return '='


class IfNode(StmtNode):
    def __init__(self, cond: ExprNode, then_stmt: StmtNode, else_stmt: Optional[StmtNode] = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.cond = cond
        self.then_stmt = then_stmt
        self.else_stmt = else_stmt

    @property
    def childs(self) -> Tuple[ExprNode, StmtNode, Optional[StmtNode]]:
        return (self.cond, self.then_stmt) + ((self.else_stmt,) if self.else_stmt else tuple())

    def __str__(self) -> str:
        return 'if'


class TernaryNode(StmtNode):
    def __init__(self, cond: ExprNode, true_expr: ExprNode, false_expr: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.cond = cond
        self.true_expr = true_expr
        self.false_expr = false_expr

    @property
    def childs(self) -> Tuple[ExprNode, ExprNode, ExprNode]:
        return self.cond, self.true_expr, self.false_expr

    def __str__(self) -> str:
        return '?:'


class CatchBlockNode(StmtNode):
    def __init__(self, exception_type: IdentNode, exception_var: IdentNode, block: Union[StmtNode, None] = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.exception_type = exception_type
        self.exception_var = exception_var
        self.block = block

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return (self.exception_type, self.exception_var, self.block)

    def __str__(self) -> str:
        return 'catch'


class FinallyBlockNode(StmtNode):
    def __init__(self, block: Union[StmtNode, None] = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.block = block

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return (self.block,)

    def __str__(self) -> str:
        return 'finally'


class TryBlockNode(StmtNode):
    def __init__(self, block: Union[StmtNode, None] = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.block = block

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return (self.block,)

    def __str__(self) -> str:
        return 'try'


class TryNode(StmtNode):
    def __init__(self, try_block: Union[StmtNode, None] = None, catch_clauses: CatchBlockNode = None,
                 finally_block: Union[StmtNode, None] = None, row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.try_block = try_block
        self.catch_clauses = catch_clauses if catch_clauses else EMPTY_STMT
        self.finally_block = finally_block if finally_block else EMPTY_STMT

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return self.try_block, self.catch_clauses, self.finally_block

    def __str__(self) -> str:
        result = 'try'
        if self.catch_clauses:
            result += '-catch'
        if self.finally_block:
            result += '-finally'
        return result


class ForNode(StmtNode):
    def __init__(self, init: Union[StmtNode, None], cond: Union[ExprNode, StmtNode, None],
                 step: Union[StmtNode, None], body: Union[StmtNode, None] = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.init = init if init else EMPTY_STMT
        self.cond = cond if cond else EMPTY_STMT
        self.step = step if step else EMPTY_STMT
        self.body = body if body else EMPTY_STMT

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return self.init, self.cond, self.step, self.body

    def __str__(self) -> str:
        return 'for'


class WhileNode(StmtNode):
    def __init__(self, cond: Union[ExprNode, StmtNode, None],
                 body: Union[StmtNode, None] = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.cond = cond if cond else EMPTY_STMT
        self.body = body if body else EMPTY_STMT

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return self.cond, self.body

    def __str__(self) -> str:
        return 'while'


class DoWhileNode(StmtNode):
    def __init__(self, cond: Union[ExprNode, StmtNode, None],
                 body: Union[StmtNode, None] = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.cond = cond if cond else EMPTY_STMT
        self.body = body if body else EMPTY_STMT

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return self.cond, self.body

    def __str__(self) -> str:
        return 'do-while'


class StmtListNode(StmtNode):
    def __init__(self, *exprs: StmtNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.exprs = exprs
        self.program = False

    @property
    def childs(self) -> Tuple[StmtNode, ...]:
        return self.exprs

    def __str__(self) -> str:
        return '...'


class FuncDeclInnerNode(StmtNode):
    def __init__(self, vars_type: StmtNode, *vars_list: Tuple[AstNode, ...],
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.vars_type = vars_type
        self.vars_list = vars_list

    @property
    def childs(self) -> Tuple[ExprNode, ...]:
        # return self.vars_type, (*self.vars_list)
        return (self.vars_type,) + self.vars_list

    def __str__(self) -> str:
        return 'type'


class ReturnOpNode(ExprNode):
    def __init__(self, op: UnarOp, arg: Optional[ExprNode] = None, row: Optional[int] = None,
                 col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.op = op
        self.arg = arg

    @property
    def childs(self) -> Tuple[ExprNode]:
        return (self.arg,)

    def __str__(self) -> str:
        return str(self.op.value)


class FuncDeclNode(StmtNode):
    def __init__(self, type: IdentNode, name: IdentNode, *params_and_body: Union[FuncParamsNode, StmtListNode],
                 row: Optional[int] = None, col: Optional[int] = None, **props):
        super().__init__(row=row, col=col, **props)
        self.type = type
        self.name = name
        self.params = params_and_body[:-1]
        if len(self.params) > 0 and isinstance(self.params[0], Tuple):
            self.params = self.params[0]
        self.body = params_and_body[-1]

    @property
    def childs(self) -> Tuple[StmtNode]:
        return *self.params, self.body

    def __str__(self) -> str:
        return f'{self.type} {self.name}()'


class TypeConvertNode(ExprNode):
    def __init__(self, expr: ExprNode, type_: TypeDesc,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.expr = expr
        self.type = type_
        self.node_type = type_

    def __str__(self) -> str:
        return 'convert'

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return (_GroupNode(str(self.type), self.expr), )


class _GroupNode(AstNode):
    def __init__(self, name: str, *childs: AstNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.name = name
        self._childs = childs

    def __str__(self) -> str:
        return self.name

    @property
    def childs(self) -> Tuple['AstNode', ...]:
        return self._childs


def type_convert(expr: ExprNode, type_: TypeDesc, except_node: Optional[AstNode] = None, comment: Optional[str] = None) -> ExprNode:
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


EMPTY_STMT = StmtListNode()
EMPTY_IDENT = IdentDesc('', TypeDesc.VOID)
