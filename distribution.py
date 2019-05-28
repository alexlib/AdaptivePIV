import corr_window
import numpy as np
import time
from sklearn.neighbors import NearestNeighbors


class Distribution:
    def __init__(self, init_locations=None):
        """
        Initialises the distribution object with 0, 1, or many correlation
        window objects

        Args:
            init_locations ([list] CorrWindow, optional): list of correlation
                                                          windows to initialise
                                                          the distribution with
        """

        # if there is nothing passed, then initialise empty list
        if init_locations is None:
            self.windows = []
        elif type(init_locations) == list:
            # if it is only a single or multiple inputs we need to add
            self.windows = init_locations.copy()
        else:
            self.windows = [init_locations]

    def n_windows(self):
        """
        Returns the number of windows currently stored in the distribution
        """
        return len(self.windows)

    def get_values(self, prop):
        """
        Returns a list of property values from the list of CorrWindows
        corresponding to the requested property 'prop'

        Args:
            prop (str): The property of self.windows to retrieve

        Returns:
            list: list of properties 'prop' from self.windows

        Example:
            >>> import corr_window
            >>> x = [10, 20, 30]
            >>> y = [15, 25, 35]
            >>> WS = [31, 41, 51]
            >>> cwList = []
            >>> for i in range(3)
            >>>     cwList.append(corr_window.CorrWindow(x[i], y[i], WS[i]))
            >>> dist = Distribution(cwList)
            >>> x_vals = dist.values("x")
            >>> print(x_vals)
            ... [10, 20, 30]
        """
        return [cw.__dict__[prop] for cw in self.windows]




def NMT_detection(u, v, nb_ind, eps=0.1):
    """
    Detects outliers according to the normalised median threshold test of
    Westerweel and Scarano
    Returns the norm value

    Args:
        u (list, float): list of the u displacement values
        v (list, float): list of the v displacement values
        nb_ind (ndarray, int): list of neighbour indices for each location
        eps (float, optional): background noise level, in px
        thr (int, optional): threshold for an outlier
    """

    norm = np.empty(np.shape(u))
    for row in nb_ind:
        # get the median of u and v from the neighbours
        # ignore first element (itself)
        u_nb, v_nb = u[row[1:]], v[row[1:]]
        u_med, v_med = np.median(u_nb), np.median(v_nb)

        # difference of all vectors to median
        u_fluct, v_fluct = u[row] - u_med, v[row] - v_med

        # difference of central vector
        u_ctr_fluct, v_ctr_fluct = u_fluct[0], v_fluct[0]

        # calculate norm
        u_norm, v_norm = (np.abs(u_ctr_fluct /
                                 (np.median(np.abs(u_fluct[1:])) + eps)),
                          np.abs(v_ctr_fluct /
                                 (np.median(np.abs(v_fluct[1:])) + eps)), )
        norm[row[0]] = np.sqrt(u_norm**2 + v_norm**2)

    return norm


if __name__ == '__main__':
    # create long list of corrWindows
    cwList = []
    for i in range(10):
        cwList.append(corr_window.CorrWindow(i, 2 * i, 31))

    dist = Distribution(cwList)
    print(dist.get_values('x'))
    # print(dist.get_values('WrongKey'))

    start = time.time()
    for i in range(100):
        dist.get_values('x')
    print("plain list", time.time() - start)
