import unittest
import os
import heat as ht
import torch

if os.environ.get("DEVICE") == "gpu" and torch.cuda.is_available():
    ht.use_device("gpu")
    torch.cuda.set_device(torch.device(ht.get_device().torch_device))
else:
    ht.use_device("cpu")
device = ht.get_device().torch_device
ht_device = None
if os.environ.get("DEVICE") == "lgpu" and torch.cuda.is_available():
    device = ht.gpu.torch_device
    ht_device = ht.gpu
    torch.cuda.set_device(device)


class TestIndexing(unittest.TestCase):
    def test_nonzero(self):
        # cases to test:
        # not split
        a = ht.array([[1, 2, 3], [4, 5, 2], [7, 8, 9]], split=None, device=ht_device)
        cond = a > 3
        nz = ht.nonzero(cond)
        self.assertEqual(nz.gshape, (5, 2))
        self.assertEqual(nz.dtype, ht.int64)
        self.assertEqual(nz.split, None)

        # split
        a = ht.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], split=1, device=ht_device)
        cond = a > 3
        nz = cond.nonzero()
        self.assertEqual(nz.gshape, (6, 2))
        self.assertEqual(nz.dtype, ht.int64)
        self.assertEqual(nz.split, 0)
        a[nz] = 10.0
        self.assertEqual(ht.all(a[nz] == 10), 1)

    def test_where(self):
        # cases to test
        # no x and y
        a = ht.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], split=None, device=ht_device)
        cond = a > 3
        wh = ht.where(cond)
        self.assertEqual(wh.gshape, (6, 2))
        self.assertEqual(wh.dtype, ht.int64)
        self.assertEqual(wh.split, None)
        # split
        a = ht.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], split=1, device=ht_device)
        cond = a > 3
        wh = ht.where(cond)
        self.assertEqual(wh.gshape, (6, 2))
        self.assertEqual(wh.dtype, ht.int64)
        self.assertEqual(wh.split, 0)

        # not split cond
        a = ht.array(
            [[0.0, 1.0, 2.0], [0.0, 2.0, 4.0], [0.0, 3.0, 6.0]], split=None, device=ht_device
        )
        res = ht.array(
            [[0.0, 1.0, 2.0], [0.0, 2.0, -1.0], [0.0, 3.0, -1.0]], split=None, device=ht_device
        )
        wh = ht.where(a < 4.0, a, -1.0)
        self.assertTrue(
            ht.equal(
                a[ht.nonzero(a < 4)],
                ht.array([0.0, 1.0, 2.0, 0.0, 2.0, 0.0, 3.0], device=ht_device),
            )
        )
        self.assertTrue(ht.equal(wh, res))
        self.assertEqual(wh.gshape, (3, 3))
        self.assertEqual(wh.dtype, ht.float)

        # split cond
        a = ht.array([[0.0, 1.0, 2.0], [0.0, 2.0, 4.0], [0.0, 3.0, 6.0]], split=0, device=ht_device)
        res = ht.array(
            [[0.0, 1.0, 2.0], [0.0, 2.0, -1.0], [0.0, 3.0, -1.0]], split=0, device=ht_device
        )
        wh = ht.where(a < 4.0, a, -1)
        print(wh._DNDarray__array.dtype)
        self.assertTrue(ht.all(wh[ht.nonzero(a >= 4)], -1))
        self.assertTrue(ht.equal(wh, res))
        self.assertEqual(wh.gshape, (3, 3))
        self.assertEqual(wh.dtype, ht.float)
        self.assertEqual(wh.split, 0)

        a = ht.array([[0.0, 1.0, 2.0], [0.0, 2.0, 4.0], [0.0, 3.0, 6.0]], split=1, device=ht_device)
        res = ht.array(
            [[0.0, 1.0, 2.0], [0.0, 2.0, -1.0], [0.0, 3.0, -1.0]], split=1, device=ht_device
        )
        wh = ht.where(a < 4.0, a, -1)
        self.assertTrue(ht.equal(wh, res))
        self.assertEqual(wh.gshape, (3, 3))
        self.assertEqual(wh.dtype, ht.float)
        self.assertEqual(wh.split, 1)

        with self.assertRaises(TypeError):
            ht.where(cond, a)

        with self.assertRaises(NotImplementedError):
            ht.where(
                cond,
                ht.ones((3, 3), split=0, device=ht_device),
                ht.ones((3, 3), split=1, device=ht_device),
            )
