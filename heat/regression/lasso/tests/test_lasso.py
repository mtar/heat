import os
import unittest
import numpy as np
import torch
import heat as ht

ht_device, torch_device, _ = ht.use_envar_device()


if ht.io.supports_hdf5():

    class TestLasso(unittest.TestCase):
        def test_lasso(self):
            # ToDo: add additional tests
            # get some test data
            X = ht.load_hdf5(
                os.path.join(os.getcwd(), "heat/datasets/data/diabetes.h5"),
                dataset="x",
                device=ht_device,
            )
            y = ht.load_hdf5(
                os.path.join(os.getcwd(), "heat/datasets/data/diabetes.h5"),
                dataset="y",
                device=ht_device,
            )

            # normalize dataset
            X = X / ht.sqrt((ht.mean(X ** 2, axis=0)))
            m, n = X.shape
            # HeAT lasso instance
            estimator = ht.regression.lasso.HeatLasso(max_iter=100, tol=None)
            # check whether the results are correct
            self.assertEqual(estimator.lam, 0.1)
            self.assertTrue(estimator.theta is None)
            self.assertTrue(estimator.n_iter is None)
            self.assertEqual(estimator.max_iter, 100)
            self.assertEqual(estimator.coef_, None)
            self.assertEqual(estimator.intercept_, None)

            estimator.fit(X, y)

            # check whether the results are correct
            self.assertEqual(estimator.lam, 0.1)
            self.assertIsInstance(estimator.theta, ht.DNDarray)
            self.assertEqual(estimator.n_iter, 100)
            self.assertEqual(estimator.max_iter, 100)
            self.assertEqual(estimator.coef_.shape, (n - 1, 1))
            self.assertEqual(estimator.intercept_.shape, (1,))

            yest = estimator.predict(X)

            # check whether the results are correct
            self.assertIsInstance(yest, ht.DNDarray)
            self.assertEqual(yest.shape, (m,))

            X = ht.load_hdf5(
                os.path.join(os.getcwd(), "heat/datasets/data/diabetes.h5"),
                dataset="x",
                device=ht_device,
            )
            y = ht.load_hdf5(
                os.path.join(os.getcwd(), "heat/datasets/data/diabetes.h5"),
                dataset="y",
                device=ht_device,
            )

            # Now the same stuff again in PyTorch
            X = torch.tensor(X._DNDarray__array, device=torch_device)
            y = torch.tensor(y._DNDarray__array, device=torch_device)

            # normalize dataset
            X = X / torch.sqrt((torch.mean(X ** 2, 0)))
            m, n = X.shape

            estimator = ht.regression.lasso.PytorchLasso(max_iter=100, tol=None)
            # check whether the results are correct
            self.assertEqual(estimator.lam, 0.1)
            self.assertTrue(estimator.theta is None)
            self.assertTrue(estimator.n_iter is None)
            self.assertEqual(estimator.max_iter, 100)
            self.assertEqual(estimator.coef_, None)
            self.assertEqual(estimator.intercept_, None)

            estimator.fit(X, y)

            # check whether the results are correct
            self.assertEqual(estimator.lam, 0.1)
            self.assertIsInstance(estimator.theta, torch.Tensor)
            self.assertEqual(estimator.n_iter, 100)
            self.assertEqual(estimator.max_iter, 100)
            self.assertEqual(estimator.coef_.shape, (n - 1, 1))
            self.assertEqual(estimator.intercept_.shape, (1,))

            yest = estimator.predict(X)

            # check whether the results are correct
            self.assertIsInstance(yest, torch.Tensor)
            self.assertEqual(yest.shape, (m,))

            X = ht.load_hdf5(
                os.path.join(os.getcwd(), "heat/datasets/data/diabetes.h5"),
                dataset="x",
                device=ht_device,
            )
            y = ht.load_hdf5(
                os.path.join(os.getcwd(), "heat/datasets/data/diabetes.h5"),
                dataset="y",
                device=ht_device,
            )

            # Now the same stuff again in PyTorch
            X = X._DNDarray__array.cpu().numpy()
            y = y._DNDarray__array.cpu().numpy()

            # normalize dataset
            X = X / np.sqrt((np.mean(X ** 2, axis=0, keepdims=True)))
            m, n = X.shape

            estimator = ht.regression.lasso.NumpyLasso(max_iter=100, tol=None)
            # check whether the results are correct
            self.assertEqual(estimator.lam, 0.1)
            self.assertTrue(estimator.theta is None)
            self.assertTrue(estimator.n_iter is None)
            self.assertEqual(estimator.max_iter, 100)
            self.assertEqual(estimator.coef_, None)
            self.assertEqual(estimator.intercept_, None)

            estimator.fit(X, y)

            # check whether the results are correct
            self.assertEqual(estimator.lam, 0.1)
            self.assertIsInstance(estimator.theta, np.ndarray)
            self.assertEqual(estimator.n_iter, 100)
            self.assertEqual(estimator.max_iter, 100)
            self.assertEqual(estimator.coef_.shape, (n - 1, 1))
            self.assertEqual(estimator.intercept_.shape, (1,))

            yest = estimator.predict(X)

            # check whether the results are correct
            self.assertIsInstance(yest, np.ndarray)
            self.assertEqual(yest.shape, (m,))
