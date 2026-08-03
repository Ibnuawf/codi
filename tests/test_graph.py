import unittest

from codi.analyzer import FileMetrics
from codi.graph import DependencyGraph, _module_name


def _fm(path: str, imports: list[str]) -> FileMetrics:
    return FileMetrics(path=path, imports=imports)


class TestGraph(unittest.TestCase):
    def test_module_name_conversion(self):
        self.assertEqual(_module_name("pkg/mod.py"), "pkg.mod")
        self.assertEqual(_module_name("pkg/__init__.py"), "pkg")

    def test_edges_resolve_internal_imports(self):
        files = [
            _fm("app/main.py", ["app.utils", "os"]),
            _fm("app/utils.py", ["json"]),
        ]
        g = DependencyGraph.build(files)
        self.assertEqual(g.edges["app.main"], {"app.utils"})
        self.assertEqual(g.edges["app.utils"], set())

    def test_from_import_resolves_to_module(self):
        # `from app.utils import helper` produces import "app.utils"
        files = [_fm("app/main.py", ["app.utils"]), _fm("app/utils.py", [])]
        g = DependencyGraph.build(files)
        self.assertIn("app.utils", g.edges["app.main"])

    def test_fan_in_out(self):
        files = [
            _fm("a.py", ["b", "c"]),
            _fm("b.py", ["c"]),
            _fm("c.py", []),
        ]
        g = DependencyGraph.build(files)
        self.assertEqual(g.fan_in()["c"], 2)
        self.assertEqual(g.fan_out()["a"], 2)

    def test_cycle_detection(self):
        files = [_fm("a.py", ["b"]), _fm("b.py", ["a"]), _fm("c.py", [])]
        g = DependencyGraph.build(files)
        cycles = g.find_cycles()
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0]), {"a", "b"})

    def test_no_cycles_in_dag(self):
        files = [_fm("a.py", ["b"]), _fm("b.py", ["c"]), _fm("c.py", [])]
        g = DependencyGraph.build(files)
        self.assertEqual(g.find_cycles(), [])


if __name__ == "__main__":
    unittest.main()
