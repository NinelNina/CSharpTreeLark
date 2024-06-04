from typing import Any, Dict, Optional, Tuple
from enum import Enum


class BinOp(Enum):
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    MOD = '%'
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
    MOD_EQ = '%='

    def __str__(self):
        return self.value


class UnarOp(Enum):
    INC = '++'
    DEC = '--'
    NOT = '!'
    RETURN = 'return'

    def __str__(self):
        return self.value


class BaseType(Enum):
    VOID = 'void'
    INT = 'int'
    FLOAT = 'float'
    BOOL = 'bool'
    STR = 'string'
    EXCEPTION = 'Exception'

    def __str__(self):
        return self.value


VOID, INT, FLOAT, BOOL, STR, EXCEPTION = BaseType.VOID, BaseType.INT, BaseType.FLOAT, BaseType.BOOL, BaseType.STR, BaseType.EXCEPTION


class TypeDesc:
    VOID: 'TypeDesc'
    INT: 'TypeDesc'
    FLOAT: 'TypeDesc'
    BOOL: 'TypeDesc'
    STR: 'TypeDesc'
    EXCEPTION: 'TypeDesc'

    def __init__(self, base_type_: Optional[BaseType] = None,
                 return_type: Optional['TypeDesc'] = None, params: Optional[Tuple['TypeDesc']] = None) -> None:
        self.base_type = base_type_
        self.return_type = return_type
        self.params = params

    @property
    def func(self) -> bool:
        return self.return_type is not None

    @property
    def is_simple(self) -> bool:
        return not self.func

    def __eq__(self, other: 'TypeDesc'):
        if self.func != other.func:
            return False
        if not self.func:
            return self.base_type == other.base_type
        else:
            if self.return_type != other.return_type:
                return False
            if len(self.params) != len(other.params):
                return False
            for i in range(len(self.params)):
                if self.params[i] != other.params[i]:
                    return False
            return True

    @staticmethod
    def from_base_type(base_type_: BaseType) -> 'TypeDesc':
        return getattr(TypeDesc, base_type_.name)

    @staticmethod
    def from_str(str_decl: str) -> 'TypeDesc':
        try:
            base_type_ = BaseType(str_decl)
            return TypeDesc.from_base_type(base_type_)
        except:
            raise SemanticException('Неизвестный тип {}'.format(str_decl))

    def __str__(self) -> str:
        if not self.func:
            return str(self.base_type)
        else:
            res = str(self.return_type)
            res += ' ('
            for param in self.params:
                if res[-1] != '(':
                    res += ', '
                res += str(param)
            res += ')'
        return res


for base_type in BaseType:
    setattr(TypeDesc, base_type.name, TypeDesc(base_type))


class ScopeType(Enum):
    GLOBAL = 'global'
    GLOBAL_LOCAL = 'global.local'
    PARAM = 'param'
    LOCAL = 'local'

    def __str__(self):
        return self.value


class IdentDesc:
    def __init__(self, name: str, type_: TypeDesc, scope: ScopeType = ScopeType.GLOBAL, index: int = 0) -> None:
        self.name = name
        self.type = type_
        self.scope = scope
        self.index = index
        self.built_in = False

    def __str__(self) -> str:
        return '{}, {}, {}'.format(self.type, self.scope, 'built-in' if self.built_in else self.index)


class IdentScope:
    def __init__(self, parent: Optional['IdentScope'] = None) -> None:
        self.idents: Dict[str, IdentDesc] = {}
        self.func: Optional[IdentDesc] = None
        self.parent = parent
        self.var_index = 0
        self.param_index = 0

    @property
    def is_global(self) -> bool:
        return self.parent is None

    @property
    def curr_global(self) -> 'IdentScope':
        curr = self
        while curr.parent:
            curr = curr.parent
        return curr

    @property
    def curr_func(self) -> Optional['IdentScope']:
        curr = self
        while curr and not curr.func:
            curr = curr.parent
        return curr

    def add_ident(self, ident: IdentDesc) -> IdentDesc:
        func_scope = self.curr_func
        global_scope = self.curr_global

        if ident.scope != ScopeType.PARAM:
            ident.scope = ScopeType.LOCAL if func_scope else \
                ScopeType.GLOBAL if self == global_scope else ScopeType.GLOBAL_LOCAL

        old_ident = self.get_ident(ident.name)
        if old_ident:
            error = False
            if ident.scope == ScopeType.PARAM:
                if old_ident.scope == ScopeType.PARAM:
                    error = True
            elif ident.scope == ScopeType.LOCAL:
                if old_ident.scope not in (ScopeType.GLOBAL, ScopeType.GLOBAL_LOCAL):
                    error = True
            else:
                error = True
            if error:
                raise SemanticException('Идентификатор {} уже объявлен'.format(ident.name))

        if not ident.type.func:
            if ident.scope == ScopeType.PARAM:
                ident.index = func_scope.param_index
                func_scope.param_index += 1
            else:
                ident_scope = func_scope if func_scope else global_scope
                ident.index = ident_scope.var_index
                ident_scope.var_index += 1

        self.idents[ident.name] = ident
        return ident

    def get_ident(self, name: str) -> Optional[IdentDesc]:
        scope = self
        ident = None
        while scope:
            ident = scope.idents.get(name)
            if ident:
                break
            scope = scope.parent
        return ident


class SemanticException(Exception):
    def __init__(self, message, row: int = None, col: int = None, **kwargs: Any) -> None:
        if row or col:
            message += " ("
            if row:
                message += 'строка: {}'.format(row)
                if col:
                    message += ', '
            if row:
                message += 'позиция: {}'.format(col)
            message += ")"
        self.message = message


TYPE_CONVERTIBILITY = {
    INT: (FLOAT, BOOL, STR),
    FLOAT: (STR,),
    BOOL: (STR,)
}


def can_type_convert_to(from_type: TypeDesc, to_type: TypeDesc) -> bool:
    if not from_type.is_simple or not to_type.is_simple:
        return False
    return from_type.base_type in TYPE_CONVERTIBILITY and to_type.base_type in TYPE_CONVERTIBILITY[to_type.base_type]


BIN_OP_TYPE_COMPATIBILITY = {
    BinOp.ADD: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT,
        (STR, STR): STR
    },
    BinOp.SUB: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT
    },
    BinOp.MUL: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT
    },
    BinOp.DIV: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT
    },
    BinOp.MOD: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT
    },
    BinOp.GT: {
        (INT, INT): BOOL,
        (FLOAT, FLOAT): BOOL,
        (STR, STR): BOOL,
    },
    BinOp.LT: {
        (INT, INT): BOOL,
        (FLOAT, FLOAT): BOOL,
        (STR, STR): BOOL,
    },
    BinOp.GE: {
        (INT, INT): BOOL,
        (FLOAT, FLOAT): BOOL,
        (STR, STR): BOOL,
    },
    BinOp.LE: {
        (INT, INT): BOOL,
        (FLOAT, FLOAT): BOOL,
        (STR, STR): BOOL,
    },
    BinOp.EQUALS: {
        (INT, INT): BOOL,
        (FLOAT, FLOAT): BOOL,
        (STR, STR): BOOL,
        (BOOL, BOOL): BOOL,
    },
    BinOp.NEQUALS: {
        (INT, INT): BOOL,
        (FLOAT, FLOAT): BOOL,
        (STR, STR): BOOL,
        (BOOL, BOOL): BOOL,
    },
    BinOp.BIT_AND: {
        (INT, INT): INT,
    },
    BinOp.BIT_OR: {
        (INT, INT): INT,
    },
    BinOp.LOGICAL_AND: {
        (BOOL, BOOL): BOOL,
    },
    BinOp.LOGICAL_OR: {
        (BOOL, BOOL): BOOL,
    },
}

COMB_EQ_OP_TYPE_COMPATIBILITY = {
    CombEqOp.ADD_EQ: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT,
        (STR, STR): STR
    },
    CombEqOp.SUB_EQ: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT
    },
    CombEqOp.MULT_EQ: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT
    },
    CombEqOp.DIV_EQ: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT
    },
    CombEqOp.MOD_EQ: {
        (INT, INT): INT,
        (FLOAT, FLOAT): FLOAT
    }
}

UNAR_OP_TYPE_COMPATIBILITY = {
    UnarOp.INC: {
        INT: INT,
        FLOAT: FLOAT,
    },
    UnarOp.DEC: {
        INT: INT,
        FLOAT: FLOAT
    },
    UnarOp.NOT: {
        BOOL: BOOL,
    },
    UnarOp.RETURN: {
        INT: INT,
        FLOAT: FLOAT,
        BOOL: BOOL,
        STR: STR,
        EXCEPTION: EXCEPTION
    }
}
