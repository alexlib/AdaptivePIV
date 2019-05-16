import numpy as np


class DensePredictor(object):

    def __init__(self, u, v, mask=None):
        """
        constructs the densepredictor object from the input displacement fields
        u, v, mask must all be the same size

        Args:
            u (ndarray): The horizontal displacement field
            v (ndarray): The vertical displacement field
            mask (ndarry, optional): mask flag array. 0 is no mask, 1 is mask
                                     If not specified then an array of 0's is
                                     created

        Examples:
            >>> uIn = np.random.rand(100, 100)
            >>> vIn = np.random.rand(100, 100)
            >>> mask = np.random.randint(0, 2, (100, 100))
            >>> dp = dense_predictor.DensePredictor(uIn, vIn, mask)

        Raises:
            ValueError: If the sizes of u, v, or mask are not consistent

        """

        # check that the inputs are the same size
        if np.shape(u) != np.shape(v):
            raise ValueError("shape of u must match the shape of v")

        if mask is not None:
            if np.shape(u) != np.shape(mask):
                raise ValueError("The shape of the mask must match u and v")
            self.has_mask = True
        else:
            mask = np.ones(np.shape(u))
            self.has_mask = False

        self.u = u
        self.v = v
        self.mask = mask
        self.n_rows = np.shape(u)[0]
        self.n_cols = np.shape(u)[1]
        self.img_dim = [self.n_rows, self.n_cols]

    def get_region(self, x, y, rad, truncate=True):
        """
        Retrieves the displacements for the region requested.
        If the region requested extends beyond the image dimensions then the
        values are either truncated or padded with 0's

        Matrix access is base 0 and is ROW major:
            | 0| 1| 2| 3|
            -------------
            | 4| 5| 6| 7|
            -------------
            | 8| 9|10|11|
            -------------

        Args:
            x (int): x coord of the centre of the region to be extracted
            y (int): y coord of the centre of the region to be extracted
            rad (int): the number of pixels to extend in each directions
            truncate (bool, optional): True - truncates the returned values
                                       outside of the domain
                                       False - pads with zeros beyong the domain

        Returns:
            u (ndarray): Horizontal displacement values around (x, y)+-rad
            v (ndarray): Vertical displacement values around (x, y)+-rad
            mask (ndarray): Mask flag values around (x, y)+-rad

        Examples:
            >>> uIn = np.random.rand(100, 100)
            >>> dp = dense_predictor.DensePredictor(uIn, uIn)
            >>> u, v, mask = dense_predictor.DensePredictor(3, 3, 2)
            >>> np.shape(u)
            ... (5, 5)
            >>> np.allclose(uIn[0:5, 0:5], u)
            ... True
        """

        """
        extract what region we can within the image.
        to do this we need to know where we are with respect to the limits
        of the image
        """
        # if x - rad is < 0, set to 0, if > n_cols, set to n_cols - 1
        # the minus 1 is because of 0 indexing
        left = max(min(x - rad, self.n_cols - 1), 0)
        right = max(min(x + rad, self.n_cols - 1), 0)
        bottom = max(min(y - rad, self.n_rows - 1), 0)
        top = max(min(y + rad, self.n_rows - 1), 0)

        # extract this region out of the images/mask
        # note the +1 is because left:right is not inclusive of right
        u = self.u[bottom:top + 1, left:right + 1]
        v = self.v[bottom:top + 1, left:right + 1]

        # decide whether to pad or truncate
        if truncate:
            if self.has_mask:
                mask = self.mask[bottom:top + 1, left:right + 1]
            else:
                mask = np.ones(np.shape(u))
        else:
            # now pad the image with 0's if ctr +- rad overlaps the edge
            pl = max(rad - x, 0)
            pr = max(x + rad - self.n_cols + 1, 0)
            pb = max(rad - y, 0)
            pt = max(y + rad - self.n_rows + 1, 0)
            pad = ((pb, pt), (pl, pr))

            u = np.pad(u, pad, 'constant', constant_values=0)
            v = np.pad(v, pad, 'constant', constant_values=0)
            if self.has_mask:
                mask = np.pad(
                    self.mask[bottom:top + 1, left:right + 1], pad,
                    'constant', constant_values=0)

        return u, v, mask
