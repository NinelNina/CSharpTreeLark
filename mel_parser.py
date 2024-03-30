from collections.abc import Iterable
from contextlib import suppress

from lark import Lark, Transformer
from lark.lexer import Token

from mel_ast import *


parser = Lark('''
    %import common.NUMBER
    %import common.ESCAPED_STRING
    %import common.CNAME
    %import common.NEWLINE
    %import common.WS

    %ignore WS

    COMMENT: "/*" /(.|\\n|\\r)+/ "*/"
        |  "//" /(.)+/ NEWLINE
    %ignore COMMENT

    num: NUMBER  -> literal
    str: ESCAPED_STRING  -> literal
    ident: CNAME

    ADD:     "+"
    SUB:     "-"
    MUL:     "*"
    DIV:     "/"
    INC:     "++"
    DEC:     "--"
    NOT:     "!"
    AND:     "&&"
    OR:      "||"
    BIT_AND: "&"
    BIT_OR:  "|"
    GE:      ">="
    LE:      "<="
    NEQUALS: "!="
    EQUALS:  "=="
    GT:      ">"
    LT:      "<"
    QMARK:   "?"
    COLON:   ":"

    call: ident "(" ( expr ( "," expr )* )? ")"

    ?group: num | str
        | ident
        | call
        | "(" expr ")"

    ?mult: group
        | mult ( MUL | DIV ) group  -> bin_op

    ?add: mult
        | add ( ADD | SUB ) mult  -> bin_op

    ?compare1: add
        | add ( GT | LT | GE | LE ) add  -> bin_op

    ?compare2: compare1
        | compare1 ( EQUALS | NEQUALS ) compare1  -> bin_op

    ?logical_and: compare2
        | logical_and AND compare2  -> bin_op

    ?logical_or: logical_and
        | logical_or OR logical_and  -> bin_op
        
    ?logical_not: NOT logical_or -> unar_op

    ?expr: logical_or
        | logical_not

    ?var_decl_inner: ident
        | ident "=" expr  -> assign
        | ident "=" ternary_expr -> assign

    vars_decl: ident var_decl_inner ( "," var_decl_inner )*

    ?simple_stmt: ident "=" expr -> assign
        | call

    ?for_stmt_list: vars_decl
        | ( simple_stmt ( "," simple_stmt )* )?  -> stmt_list
    ?for_cond: expr
        |   -> stmt_list
    ?for_body: stmt
        | ";"  -> stmt_list
        
    ?while_cond: expr
    ?while_body: stmt
        | ";"  -> stmt_list

    ?ternary_expr: vars_decl
        | expr QMARK group COLON group -> ternary

    ?stmt: vars_decl ";"
        | simple_stmt ";"
        | "if" "(" expr ")" stmt ("else" stmt)?  -> if
        | ternary_expr ";"
        | "for" "(" for_stmt_list ";" for_cond ";" for_stmt_list ")" for_body  -> for
        | "while" "(" while_cond ")" while_body  -> while
        | "do" while_body "while" "(" while_cond ")" ";" -> do_while
        | "{" stmt_list "}"

    stmt_list: ( stmt ";"* )*
    
    func_decl: ident "(" params ")" "{" stmt_list "}" -> func
    
    ?params: vars_decl

    ?prog: stmt_list

    ?start: prog
''', start='start')  # , parser='lalr')


class MelASTBuilder(Transformer):
    def _call_userfunc(self, tree, new_children=None):
        # Assumes tree is already transformed
        children = new_children if new_children is not None else tree.children
        try:
            f = getattr(self, tree.data)
        except AttributeError:
            return self.__default__(tree.data, children, tree.meta)
        else:
            return f(*children)

    def __getattr__(self, item):
        if isinstance(item, str) and item.upper() == item:
            return lambda x: x

        if item in ('bin_op', ):
            def get_bin_op_node(*args):
                op = BinOp(args[1].value)
                return BinOpNode(op, args[0], args[2],
                                 **{'token': args[1], 'line': args[1].line, 'column': args[1].column})
            return get_bin_op_node

        if item in ('unar_op',):
            def get_unar_op_node(*args):
                op = UnarOp(args[0].value)
                return UnarOpNode(op, args[1],
                                  **{'token': args[0], 'line': args[0].line, 'column': args[0].column})

            return get_unar_op_node

        if item in ('ternary',):
            def get_ternary_node(*args):
                return TernaryNode(args[0], args[2], args[4],
                                   **{'token': args[1], 'line': args[1].line, 'column': args[1].column})

            return get_ternary_node

        if item in ('func',):
            def get_func_node(*args):
                print(args)
                name = args[0]
                params = [param for param in args[2] if isinstance(param, VarsDeclNode)]
                func_body = args[4]
                return FuncNode(name, params, func_body)
            return get_func_node

        if item in ('stmt_list', ):
            def get_node(*args):
                return StmtListNode(*sum(([*n] if isinstance(n, Iterable) else [n] for n in args), []))

            return get_node

        else:
            def get_node(*args):
                props = {}
                if len(args) == 1 and isinstance(args[0], Token):
                    props['token'] = args[0]
                    props['line'] = args[0].line
                    props['column'] = args[0].column
                    args = [args[0].value]
                with suppress(NameError):
                    cls = eval(''.join(x.capitalize() for x in item.split('_')) + 'Node')
                    return cls(*args, **props)
                return args
            return get_node


def parse(prog: str) -> StmtListNode:
    prog = parser.parse(str(prog))
    prog = MelASTBuilder().transform(prog)
    return prog
