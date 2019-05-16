import unittest
import numpy as np
import dense_predictor


class TestImageInfo(unittest.TestCase):
    def test_initialisation_with_mask(self):
        """
        checks the initialisation using u, v, and mask
        checks that the stored object values are correct
        """

        u = np.random.rand(100, 100)
        v = np.random.rand(100, 100)
        mask = np.random.randint(0, 2, (100, 100))
        dp = dense_predictor.DensePredictor(u, v, mask)

        # check the saved u, v, mask
        self.assertTrue(np.alltrue(dp.u == u))
        self.assertTrue(np.alltrue(dp.v == v))
        self.assertTrue(np.alltrue(dp.mask == mask))

    def test_initialisation_without_mask(self):
        """
        Checks that u and v are stored correctly, and that a mask of
        ones is created with the same shape as u and v
        """
        u = np.random.rand(100, 100)
        v = np.random.rand(100, 100)
        dp = dense_predictor.DensePredictor(u, v)

        # check the saved u, v, mask. mask should be ones
        self.assertTrue(np.alltrue(dp.u == u))
        self.assertTrue(np.alltrue(dp.v == v))
        self.assertTrue(np.alltrue(dp.mask == np.ones((100, 100))))

    def test_initialisation_with_mask_checks_size(self):
        """
        u, v, mask must have the same shape
        """
        u = np.random.rand(100, 100)
        v = np.random.rand(110, 110)
        mask = np.random.randint(0, 2, (100, 100))

        # check u vs v
        with self.assertRaises(ValueError):
            dp = dense_predictor.DensePredictor(u, v, mask)

        # check mask
        with self.assertRaises(ValueError):
            dp = dense_predictor.DensePredictor(v, v, mask)

    def test_initialisation_without_mask_checks_size(self):
        """
        checks that u and v sizes are still compared even if mask isn't passed
        """
        u = np.random.rand(100, 100)
        v = np.random.rand(110, 110)

        # check u vs v
        with self.assertRaises(ValueError):
            dp = dense_predictor.DensePredictor(u, v)

    def test_initialisation_saves_mask_status(self):
        """
        If there has been a mask passed we want to save this information as
        an easily checkable bool
        """
        u = np.random.rand(100, 100)
        v = np.random.rand(100, 100)
        mask = np.random.randint(0, 2, (100, 100))
        dp = dense_predictor.DensePredictor(u, v)
        self.assertFalse(dp.has_mask)
        dp2 = dense_predictor.DensePredictor(u, v, mask)
        self.assertTrue(dp2.has_mask)

    def test_image_dimensions_are_captured(self):
        """check that the size of the image is captured into the variables
        n_rows
        n_cols
        img_dim
        """

        # use non-square images so we are sure that we are capturing the
        # correct dimensions
        u = np.random.rand(50, 100)
        v = np.random.rand(50, 100)
        mask = np.random.randint(0, 2, (50, 100))
        dp = dense_predictor.DensePredictor(u, v, mask)
        self.assertEqual(dp.n_rows, 50)
        self.assertEqual(dp.n_cols, 100)
        self.assertEqual(dp.img_dim, [50, 100])

    def test_get_region_returns_correct_region(self):
        """
        The region returned should be ctr-rad:ctr+rad in both x and y
        Can test this by creating an image with known displacements

        [[ 1,  2,  3,  4,  5,  6],
         [ 7,  8,  9, 10, 11, 12],
         [13, 14, 15, 16, 17, 18],
         [19, 20, 21, 22, 23, 24],
         [25, 26, 27, 28, 29, 30],
         [31, 32, 33, 34, 35, 36]]

        """

        size_of_img = (6, 6)
        u = np.arange(1, size_of_img[0] * size_of_img[1] + 1)
        u = np.reshape(u, size_of_img)
        v = np.array(u)
        mask = np.array(u)
        dp = dense_predictor.DensePredictor(u, v, mask)
        u, v, mask = dp.get_region(3, 3, 2)

        # manually determine the expected array
        exp_arr = np.array([[8, 9, 10, 11, 12],
                            [14, 15, 16, 17, 18],
                            [20, 21, 22, 23, 24],
                            [26, 27, 28, 29, 30],
                            [32, 33, 34, 35, 36]])
        print(u)
        self.assertTrue(np.allclose(u, exp_arr))
        self.assertTrue(np.allclose(v, exp_arr))
        self.assertTrue(np.allclose(mask, exp_arr))

        # what happens if we truncate to the top left:
        u, v, mask = dp.get_region(1, 1, 2, truncate=True)
        exp_arr = np.array([[1, 2, 3, 4],
                            [7, 8, 9, 10],
                            [13, 14, 15, 16],
                            [19, 20, 21, 22]])
        self.assertTrue(np.allclose(u, exp_arr))
        self.assertTrue(np.allclose(v, exp_arr))
        self.assertTrue(np.allclose(mask, exp_arr))

        # if we pad with 0's instead
        u, v, mask = dp.get_region(1, 1, 2, truncate=False)
        exp_arr = np.array([[0, 0, 0, 0, 0],
                            [0, 1, 2, 3, 4],
                            [0, 7, 8, 9, 10],
                            [0, 13, 14, 15, 16],
                            [0, 19, 20, 21, 22]])
        print(u)
        self.assertTrue(np.allclose(u, exp_arr))
        self.assertTrue(np.allclose(v, exp_arr))
        self.assertTrue(np.allclose(mask, exp_arr))

        # what happens if we truncate to the bottom right:
        u, v, mask = dp.get_region(4, 4, 2, truncate=True)
        exp_arr = np.array([[15, 16, 17, 18],
                            [21, 22, 23, 24],
                            [27, 28, 29, 30],
                            [33, 34, 35, 36]])
        print(u)
        self.assertTrue(np.allclose(u, exp_arr))
        self.assertTrue(np.allclose(v, exp_arr))
        self.assertTrue(np.allclose(mask, exp_arr))

        # if we pad with 0's
        u, v, mask = dp.get_region(4, 4, 2, truncate=False)
        exp_arr = np.array([[15, 16, 17, 18, 0],
                            [21, 22, 23, 24, 0],
                            [27, 28, 29, 30, 0],
                            [33, 34, 35, 36, 0],
                            [0, 0, 0, 0, 0]])
        print(u)
        self.assertTrue(np.allclose(u, exp_arr))
        self.assertTrue(np.allclose(v, exp_arr))
        self.assertTrue(np.allclose(mask, exp_arr))


if __name__ == '__main__':
    unittest.main()
