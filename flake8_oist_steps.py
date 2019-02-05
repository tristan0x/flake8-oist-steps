# -*- coding: utf-8 -*-
import ast


try:
    from flake8.engine import pep8 as stdin_utils
except ImportError:
    from flake8 import utils as stdin_utils


FUNC_RETURNING_TET = {"findTetByPoint", "getTetTetNeighb", "getTetTetNeighb"}
FUNC_RETURNING_TRI = {"getTetTriNeighb", "getTriTriNeighbs"}


function_nodes = [ast.FunctionDef]
if getattr(ast, "AsyncFunctionDef", None):
    function_nodes.append(ast.AsyncFunctionDef)
function_nodes = tuple(function_nodes)

for_nodes = [ast.For]
if getattr(ast, "AsyncFor", None):
    for_nodes.append(ast.AsyncFor)
for_nodes = tuple(for_nodes)

with_nodes = [ast.With]
if getattr(ast, "AsyncWith", None):
    with_nodes.append(ast.AsyncWith)
with_nodes = tuple(with_nodes)


class IdChecker(object):
    name = "flake8_oist_steps"
    version = "0.0.1"
    tet_id_mesg = (
        "E421 consider using steps.geom.UNKNOWN_TET" " constant instead of -1."
    )
    tri_id_mesg = (
        "E421 consider using steps.geom.UNKNOWN_TRI" " constant instead of -1."
    )

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

    def run(self):
        tree = self.tree

        if self.filename == "stdin":
            lines = stdin_utils.stdin_get_value()
            tree = ast.parse(lines)

        for statement in ast.walk(tree):
            for child in ast.iter_child_nodes(statement):
                child.__flake8_builtins_parent = statement

        class PrintVisitor(ast.NodeTransformer):
            def __init__(self):
                self.steps_ids = dict()
                self.errors = []
                super(PrintVisitor, self).__init__()

            def visit_Assign(self, node):
                self.visit(node.value)
                steps_id = getattr(node.value, "_steps_id", False)
                for target in node.targets:
                    if steps_id:
                        if isinstance(target, ast.Name):
                            self.steps_ids[target.id] = steps_id
                        elif isinstance(target, ast.Subscript):
                            if isinstance(target.value, ast.Name):
                                self.steps_ids[target.value.id] = steps_id

            def visit_Compare(self, node):
                self.visit(node.left)
                for op in node.ops:
                    if isinstance(op, (ast.Eq, ast.NotEq)):
                        for n in node.comparators:
                            self.visit(n)
                        if isinstance(node.left, ast.Name):
                            if node.left.id in self.steps_ids:
                                if len(node.comparators) == 1:
                                    if getattr(node.comparators[0], "_is_minus_one", False):
                                        self.errors.append(
                                            [
                                                node.lineno,
                                                node.col_offset,
                                                self.steps_ids[node.left.id],
                                                IdChecker,
                                            ]
                                        )

            def visit_UnaryOp(self, node):
                if isinstance(node.op, ast.USub):
                    if isinstance(node.operand, ast.Num):
                        if node.operand.n == 1:
                            node._is_minus_one = True

            def visit_Call(self, node):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in FUNC_RETURNING_TET:
                        node._steps_id = IdChecker.tet_id_mesg
                    elif node.func.attr in FUNC_RETURNING_TRI:
                        node._steps_id = IdChecker.tri_id_mesg

            def generic_visit(self, node):
                super(PrintVisitor, self).generic_visit(node)

        v = PrintVisitor()
        v.visit(tree)
        for error in v.errors:
            yield error
