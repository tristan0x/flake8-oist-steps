# -*- coding: utf-8 -*-
import ast
import inspect
import sys


try:
    from flake8.engine import pep8 as stdin_utils
except ImportError:
    from flake8 import utils as stdin_utils


WHITE_LIST = [
    '__name__',
    '__doc__',
    'credits',
    '_',
]

FUNC_RETURNING_ID = [
    'findTetByPoint',
]


function_nodes = [ast.FunctionDef]
if getattr(ast, 'AsyncFunctionDef', None):
    function_nodes.append(ast.AsyncFunctionDef)
function_nodes = tuple(function_nodes)

for_nodes = [ast.For]
if getattr(ast, 'AsyncFor', None):
    for_nodes.append(ast.AsyncFor)
for_nodes = tuple(for_nodes)

with_nodes = [ast.With]
if getattr(ast, 'AsyncWith', None):
    with_nodes.append(ast.AsyncWith)
with_nodes = tuple(with_nodes)


if sys.version_info >= (3, 0):
    import builtins
    BUILTINS = [
        a[0]
        for a in inspect.getmembers(builtins)
        if a[0] not in WHITE_LIST
    ]
    PY3 = True
else:
    import __builtin__
    BUILTINS = [
        a[0]
        for a in inspect.getmembers(__builtin__)
        if a[0] not in WHITE_LIST
    ]
    PY3 = False


class IdChecker(object):
    name = 'flake8_oist_steps'
    version = '0.0.1'
    id_mesg = 'A001 consider using steps.UNKNOWN_TET or steps.UNKNOWN_TRI' \
              ' constant instead of -1'
    assign_msg = 'A004 "{0}" is a python builtin and is being shadowed, ' \
                 'consider renaming the variable'
    argument_msg = 'A002 "{0}" is used as an argument and thus shadows a ' \
                   'python builtin, consider renaming the argument'
    class_attribute_msg = 'A003 "{0}" is a python builtin, consider ' \
                          'renaming the class attribute'

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

    def run(self):
        tree = self.tree

        if self.filename == 'stdin':
            lines = stdin_utils.stdin_get_value()
            tree = ast.parse(lines)

        for statement in ast.walk(tree):
            for child in ast.iter_child_nodes(statement):
                child.__flake8_builtins_parent = statement

        class PrintVisitor(ast.NodeTransformer):
            def __init__(self):
                self.steps_ids = set()
                self.errors = []
                super(PrintVisitor, self).__init__()

            def visit_Assign(self, node):
                self.visit(node.value)
                steps_id = getattr(node.value, '_steps_id', False)
                for target in node.targets:
                    self.visit(target)
                    #target.id._steps_id = steps_id
                    if steps_id:
                        self.steps_ids.add(target.id)

            def visit_Compare(self, node):
                self.visit(node.left)
                for op in node.ops:
                    if isinstance(op, (ast.Eq, ast.NotEq)):
                        for n in node.comparators:
                            self.visit(n)
                        if node.left.id in self.steps_ids:
                            if len(node.comparators) == 1:
                                if getattr(node.comparators[0], '_is_minus_one'):
                                    self.errors.append([
                                        node.lineno, node.col_offset,
                                        IdChecker.id_mesg, IdChecker
                                    ])

            def visit_UnaryOp(self, node):
                if isinstance(node.op, ast.USub):
                    if isinstance(node.operand, ast.Num):
                        if node.operand.n == 1:
                            node._is_minus_one = True

            def visit_Call(self, node):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in FUNC_RETURNING_ID:
                        node._steps_id = True

            def generic_visit(self, node):
                #print(node)
                super(PrintVisitor, self).generic_visit(node)
        v = PrintVisitor()
        v.visit(tree)
        for error in v.errors:
            yield error
