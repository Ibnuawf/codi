import unittest
from pathlib import Path

from codi.analyzer import analyze_file
from codi.duplication import duplication_ratio, find_clones

CLONE_A = '''
def process_orders(orders):
    total = 0
    for order in orders:
        if order.valid:
            total += order.amount
    return total
'''

# Same structure, different names and constants — a type-2 clone.
CLONE_B = '''
def sum_invoices(invoices):
    result = 0
    for inv in invoices:
        if inv.ok:
            result += inv.value
    return result
'''

DIFFERENT = '''
def unrelated(x):
    if x > 10:
        return x * 2
    while x < 0:
        x += 1
    return x
'''

TINY = '''
def a():
    return 1

def b():
    return 2
'''


class TestDuplication(unittest.TestCase):
    def _analyze(self, mapping):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        files, sources = [], {}
        for name, src in mapping.items():
            p = Path(self.tmp.name) / name
            p.write_text(src, encoding="utf-8")
            fm = analyze_file(p, display_path=name)
            files.append(fm)
            sources[name] = src
        self.addCleanup(self.tmp.cleanup)
        return files, sources

    def test_renamed_copy_detected(self):
        files, sources = self._analyze({"a.py": CLONE_A, "b.py": CLONE_B})
        groups = find_clones(files, sources)
        self.assertEqual(len(groups), 1)
        names = {s.qualname for s in groups[0].sites}
        self.assertEqual(names, {"process_orders", "sum_invoices"})

    def test_different_structure_not_flagged(self):
        files, sources = self._analyze({"a.py": CLONE_A, "c.py": DIFFERENT})
        self.assertEqual(find_clones(files, sources), [])

    def test_tiny_functions_ignored(self):
        files, sources = self._analyze({"t.py": TINY})
        self.assertEqual(find_clones(files, sources), [])

    def test_duplication_ratio(self):
        files, sources = self._analyze({"a.py": CLONE_A, "b.py": CLONE_B})
        groups = find_clones(files, sources)
        self.assertAlmostEqual(duplication_ratio(groups, 2), 1.0)
        self.assertAlmostEqual(duplication_ratio(groups, 8), 0.25)
        self.assertEqual(duplication_ratio([], 0), 0.0)


if __name__ == "__main__":
    unittest.main()
