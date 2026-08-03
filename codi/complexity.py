"""Cyclomatic complexity measurement via AST traversal."""

from __future__ import annotations

import ast


class ComplexityVisitor(ast.NodeVisitor):
    """Counts decision points inside a single function body.

    Complexity starts at 1 (the single entry path) and each branching
    construct adds one path: if/elif, loops, except handlers, boolean
    operators, ternaries, comprehension conditions, assert, and
    match cases.
    """

    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        """Each if/elif branch adds a path."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """A for loop adds a path."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """An async for loop adds a path."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """A while loop adds a path."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Each except clause adds a path."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Chained boolean operators add one path per extra operand."""
        # `a and b and c` is two extra decision points
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        """A ternary expression adds a path."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        """An assert adds a failure path."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        """Each comprehension generator and filter adds a path."""
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_match_case(self, node: ast.match_case) -> None:
        """Each match case adds a path."""
        self.complexity += 1
        self.generic_visit(node)

    # Nested functions are measured separately; don't double-count them.
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Skip nested functions; they are measured separately."""

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Skip nested async functions; they are measured separately."""

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Skip lambdas; treated as separate trivial functions."""


def function_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Cyclomatic complexity of one function, excluding nested defs."""
    visitor = ComplexityVisitor()
    for child in ast.iter_child_nodes(node):
        visitor.visit(child)
    return visitor.complexity


def complexity_grade(score: int) -> str:
    """Letter grade for a complexity score, radon-style bands."""
    if score <= 5:
        return "A"
    if score <= 10:
        return "B"
    if score <= 20:
        return "C"
    if score <= 30:
        return "D"
    return "F"
