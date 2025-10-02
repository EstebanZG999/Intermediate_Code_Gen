import unittest
from program.ir.tac_ir import TACProgram, Const
from program.ir.temp_alloc import TempAllocator
from program.ir.label_mgr import LabelManager

class TestTACCore(unittest.TestCase):
    def test_emit_and_dump(self):
        p = TACProgram()
        p.emit('print', Const(1))
        self.assertIn('print 1', p.dump())

    def test_temp_recycle(self):
        tmps = TempAllocator()
        t0 = tmps.new()
        t1 = tmps.new()
        tmps.free(t0)
        t2 = tmps.new()
        self.assertEqual(t2.name, t0.name)

    def test_labels_unique(self):
        ls = LabelManager()
        L0 = ls.new()
        L1 = ls.new()
        self.assertNotEqual(L0.name, L1.name)

if __name__ == '__main__':
    unittest.main()