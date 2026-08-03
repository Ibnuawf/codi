import ast
import unittest

from codi.complexity import complexity_grade, function_complexity


def _cc(source: str) -> int:
    tree = ast.parse(source)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    return function_complexity(fn)


class TestComplexity(unittest.TestCase):
    def test_straight_line_is_one(self):
        self.assertEqual(_cc("def f():\n    return 1"), 1)

    def test_if_adds_one(self):
        self.assertEqual(_cc("def f(x):\n    if x:\n        return 1\n    return 0"), 2)

    def test_elif_chain(self):
        src = (
            "def f(x):\n"
            "    if x == 1: return 1\n"
            "    elif x == 2: return 2\n"
            "    elif x == 3: return 3\n"
            "    return 0\n"
        )
        self.assertEqual(_cc(src), 4)

    def test_loops(self):
        src = "def f(xs):\n    for x in xs:\n        while x:\n            x -= 1\n"
        self.assertEqual(_cc(src), 3)

    def test_boolean_operators(self):
        self.assertEqual(_cc("def f(a, b, c):\n    return a and b and c"), 3)

    def test_ternary_and_except(self):
        src = (
            "def f(x):\n"
            "    try:\n"
            "        return 1 if x else 2\n"
            "    except ValueError:\n"
            "        return 3\n"
        )
        self.assertEqual(_cc(src), 3)

    def test_comprehension_condition(self):
        self.assertEqual(_cc("def f(xs):\n    return [x for x in xs if x > 0]"), 3)

    def test_nested_function_not_counted(self):
        src = (
            "def f(x):\n"
            "    def g(y):\n"
            "        if y: return 1\n"
            "        return 0\n"
            "    return g(x)\n"
        )
        self.assertEqual(_cc(src), 1)

    def test_match_case(self):
        src = (
            "def f(x):\n"
            "    match x:\n"
            "        case 1: return 'a'\n"
            "        case 2: return 'b'\n"
        )
        self.assertEqual(_cc(src), 3)

    def test_grades(self):
        self.assertEqual(complexity_grade(1), "A")
        self.assertEqual(complexity_grade(5), "A")
        self.assertEqual(complexity_grade(10), "B")
        self.assertEqual(complexity_grade(20), "C")
        self.assertEqual(complexity_grade(30), "D")
        self.assertEqual(complexity_grade(31), "F")


if __name__ == "__main__":
    unittest.main()
