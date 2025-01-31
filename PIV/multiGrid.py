import numpy as np
import PIV.distribution as distribution
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.collections as collections
import scipy.interpolate as interp
import PIV.corr_window as corr_window
import PIV.distribution as distribution
import numpy as np
import PIV


class MultiGrid(distribution.Distribution):

    def __init__(self, img_dim, spacing, WS):
        """Defines a multigrid object with an initial grid spacing

        Args:
            img_dim (tuple): The dimensions of the image to be sampled.
                             (n_rows, n_cols)
            spacing (int): The initial spacing between samples
        """

        self.img_dim = img_dim
        self.spacing = spacing

        # create the coordinate grid
        x_vec = np.arange(0, img_dim[1], spacing)
        y_vec = np.arange(0, img_dim[0], spacing)
        xx, yy = np.meshgrid(x_vec, y_vec)
        ws_grid = np.ones_like(xx) * WS

        # turn each of the coordinates into a corrwindow object
        # note that this flattens the grid row by row

        self.windows = list(map(corr_window.CorrWindow,
                                xx.ravel(),
                                yy.ravel(),
                                ws_grid.ravel()))

        # create a new grid for the base tier
        self.grids = [Grid(img_dim, spacing)]
        for ii in range(len(y_vec)):
            for jj in range(len(x_vec)):
                self.grids[0]._array[ii][jj] = self.windows[jj + ii*len(x_vec)]

        # now go through and create the cells, identifying the coordinates for
        # each corner
        self.cells = []
        self.max_tier = 0
        # this refers to the number of grid points, there will be 1 less cell
        # in each direction
        n_rows, n_cols = np.shape(xx)
        n_rc, n_cc = n_rows - 1, n_cols - 1  # number of cells each direction

        # loop over each row and column of 'cells'
        # note that cells are 0 index and range does not include the last value
        for rr in range(n_rc):
            for cc in range(n_cc):
                # as above, the grid has been flattened row by row
                # bl, br, tl, tr correspond to the index of the grid point
                # (i.e. corr window) within the list self.windows
                bl = rr * n_cols + cc
                br = bl + 1
                tl = bl + n_cols
                tr = tl + 1
                gc = GridCell(self, bl, br, tl, tr)
                # define this as the first tier
                gc.tier = 0
                # define the bottom left CorrWindow index
                gc.ix, gc.iy = cc, rr
                self.cells.append(gc)

        # loop over and set the neighbours of each of the cells,
        # we need to do this after, since not all of the cells will exist if
        # we run during the loop
        for rr in range(n_rc):
            for cc in range(n_cc):
                # define the cells neighbours
                # north is cell number + num cells per row, unless on top row
                # east is cell number + 1, unless on right most col
                # south is cell number - num cells per row, unless on bottom row
                # west is cell number - 1 , unless on left most col
                # cell num
                cn = rr * n_cc + cc
                if rr != (n_rc - 1):
                    self.cells[cn].north = self.cells[cn + n_cc]

                if cc != (n_cc - 1):
                    self.cells[cn].east = self.cells[cn + 1]

                if rr != 0:
                    self.cells[cn].south = self.cells[cn - n_cc]

                if cc != 0:
                    self.cells[cn].west = self.cells[cn - 1]

        self.cells_in_top_tier = len(self.cells)

    @property
    def n_windows(self):
        return len(self.windows)

    @property
    def n_cells(self):
        return len(self.cells)

    def new_tier(self):
        """
        Adds a new tier to the multigrid. 

        This method first checks that a new tier can be added - the spacing 
        must be halved and must still result in integer locations

        The method then creates a new grid for the required level

        """

        # determine what the current spacing is
        h_curr = int(self.spacing / (2**self.max_tier))
        h_new = h_curr / 2
        # check if we can split the tier anymore
        if int(h_new) == h_new:
            # update the max tier setting
            self.max_tier += 1
            # create a new grid
            self.grids.append(Grid(self.img_dim, int(h_new)))
        else:
            raise ValueError("Grid refinement not possible")

    def split_all_cells(self):
        """Split all cells, each into 4 new cells
        """

        n = self.n_cells
        for i in range(n):
            self.cells[i].split()

    def interp_to_densepred(self, method='cubic'):
        """
        Interpolate the multigrid onto a pixelwise densepredictor using 
        multi-level interpolation

        Works by interpolating the coarse mesh to obtain the baseline. 
        Refinements are then treated as a delta to the coarse interpolant.        

        Args:
             method (string): Either linear or cubic
                              Cubic represents a cubic spline which is 
                              c2 continuous

        Returns:
            interpolation (DensePredictor): solution interpolated onto a 
                                            densepredictor

        """

        # define evaluation domain
        xe, ye = np.arange(self.img_dim[1]), np.arange(self.img_dim[0])

        # get coarse interpolation
        u0, v0 = self.grids[0].get_values()
        f0_u = interp.interp2d(self.grids[0].x_vec,
                               self.grids[0].y_vec,
                               u0, kind=method)
        f0_v = interp.interp2d(self.grids[0].x_vec,
                               self.grids[0].y_vec,
                               v0, kind=method)
        u0_eval, v0_eval = f0_u(xe, ye), f0_v(xe, ye)
        u_soln, v_soln = u0_eval, v0_eval

        # loop over number of tiers
        for tn in range(1, self.max_tier+1):

            # get the interpolated values at each of the finer grid points
            h = self.grids[tn].spacing
            u_int = u_soln[::h, ::h]
            v_int = v_soln[::h, ::h]

            # get the delta to the assumed solution
            u1, v1 = self.grids[tn].get_values()
            u_delta = u1 - u_int
            v_delta = v1 - v_int
            u_delta[np.isnan(u_delta)] = 0
            v_delta[np.isnan(v_delta)] = 0

            # interpolate the delta
            f_u = interp.interp2d(self.grids[tn].x_vec,
                                  self.grids[tn].y_vec,
                                  u_delta, kind=method)
            f_v = interp.interp2d(self.grids[tn].x_vec,
                                  self.grids[tn].y_vec,
                                  v_delta, kind=method)

            # evaluate the interpolant over the domain and update solution
            u_eval, v_eval = f_u(xe, ye), f_v(xe, ye)
            u_soln += u_eval
            v_soln += v_eval

        return PIV.dense_predictor.DensePredictor(u_soln, v_soln)

    def splint(self):
        """Calculates the objective function by subtracting the linear 
        interpolant from the cubic interpolant
        """

        dp_cub = self.interp_to_densepred(method='cubic')
        dp_lin = self.interp_to_densepred(method='linear')
        dp_splint = dp_cub - dp_lin

        return dp_splint.magnitude()

    def adaptive_split_peak_value_cells(self, obj_func):
        """Split cells according to the input objective function.

        Considers the peak value of the objective function within a cell
        """

        # get the leaf cells
        leaf_cells = np.array(self.get_all_leaf_cells())

        peak_values = []
        # get peak value within cells
        for cell in leaf_cells:
            bl, tr = cell.coordinates[0], cell.coordinates[2]
            # get view into splint
            sub_region = obj_func[bl[1]:tr[1], bl[0]:tr[0]]
            peak_values.append(np.max(sub_region))

        I = np.argsort(peak_values)
        # pv = peak_values[I[::-1]]
        lc = leaf_cells[I[::-1]]

        split_counter = 0
        max_splits = len(I)//2

        for cell in lc:
            try:
                cell.split()
                # assume that is split, otherwise an error would be thrown
                split_counter += 1
                if split_counter == max_splits:
                    break
            except:
                continue

    def get_all_leaf_cells(self):
        """Returns a list of leaf cells in the domain, 
            i.e cells without any children

            loop over top cells, if the cell has no children then add to 
            the list. if it has children then recursively progress down the 
            cells adding those which have no children
        """

        out_list = []

        def add_children(cell, out_list):
            """Allow for recursion
            """
            if not cell.has_children():
                out_list.append(cell)
            else:
                for child_cell in cell.children.values():
                    add_children(child_cell, out_list)

        for cell in self.cells[0:self.cells_in_top_tier]:
            add_children(cell, out_list)

        return out_list

    def plot_grid(self, ax=None):
        """Plots the grid in the conventional manner
        """

        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)

        rects = []
        for cell in self.get_all_leaf_cells():
            # rectangle for the bottom level cell
            bl, tr = cell.coordinates[0], cell.coordinates[2]
            height, width = tr[1] - bl[1], tr[0] - bl[0]
            rects.append(patches.Rectangle(bl, width, height, fill=False))

        rect_collection = collections.PatchCollection(
            rects, match_original=True)
        ax.add_collection(rect_collection)
        ax.set_xlim([0, self.img_dim[1]])
        ax.set_ylim([0, self.img_dim[0]])
        fig.show()


class GridCell():
    def __init__(self, multigrid, id_bl, id_br, id_tl, id_tr):
        """Initialise a grid cell, given a parent multigrid and the ids of 
        the 4 windows which makes up the 'cell'

        Arguments:
            multigrid {MultiGrid} -- The parent multigrid
            id_bl {int} -- index into multigrid.windows for the bottom left 
                           window
            id_br {int} -- index into multigrid.windows for the bottom right 
                           window
            id_tl {int} -- index into multigrid.windows for the top left 
                           window
            id_tr {int} -- index into multigrid.windows for the top right 
                           window
        """
        # cwList will act as a pointer to the list of corr windows and hence
        # shouldn't impose too much of a memory overhead.
        self.multigrid = multigrid
        self.cw_list = multigrid.windows

        self.id_bl = id_bl
        self.id_br = id_br
        self.id_tl = id_tl
        self.id_tr = id_tr
        self.bl_win = self.cw_list[id_bl]
        self.br_win = self.cw_list[id_br]
        self.tl_win = self.cw_list[id_tl]
        self.tr_win = self.cw_list[id_tr]

        self.tier = 0
        self.children, self.parent = None, None
        self.north = None
        self.east = None
        self.south = None
        self.west = None

    def has_children(self):
        return False if self.children is None else True

    def split_neighbs_if_needed(self):
        """This function is intended to be called when a cell is requested to
        be split.

        It will check in the neighbours of the parent cell and
        split them if needed.
        """

        # if the neighbour exists at this level then we don't need to split
        # anything
        if self.north is None:
            # test if the parent's north neighbour exists
            # it might not if it is at a border
            if self.parent.north is not None:
                self.parent.north.split()

        if self.east is None:
            # test if the parent's east neighbour exists
            # it might not if it is at a border
            if self.parent.east is not None:
                self.parent.east.split()

        if self.south is None:
            # test if the parent's south neighbour exists
            # it might not if it is at a border
            if self.parent.south is not None:
                self.parent.south.split()

        if self.west is None:
            # test if the parent's west neighbour exists
            # it might not if it is at a border
            if self.parent.west is not None:
                self.parent.west.split()

    def create_new_corrWindows(self):
        """This method creates 5 new correlation windows at the midpoints and
        centre of the 4 existing windows.

        Checks for existing cells in neighbours

        Returns:
            CorrWindow: All 5 CorrWindows
                        left_mid, ctr_btm, ctr_mid, ctr_top, right_mid
        """

        # create the new windows at mid-points
        ctr_x = (self.bl_win.x + self.br_win.x) / 2
        ctr_y = (self.bl_win.y + self.tl_win.y) / 2

        # check left
        if self.west is not None and self.west.has_children():
            left_mid = self.west.children['br'].id_tr
        else:
            win = corr_window.CorrWindow(self.bl_win.x, ctr_y,
                                         self.bl_win.WS)
            self.cw_list.append(win)
            left_mid = self.multigrid.n_windows - 1

        # check down
        if self.south is not None and self.south.has_children():
            ctr_btm = self.south.children['tl'].id_tr
        else:
            win = corr_window.CorrWindow(ctr_x, self.bl_win.y,
                                         self.bl_win.WS)
            self.cw_list.append(win)
            ctr_btm = self.multigrid.n_windows - 1

        # ctr_mid is the only window which is the only window guaranteed
        # to not already exist
        win = corr_window.CorrWindow(ctr_x, ctr_y, self.bl_win.WS)
        self.cw_list.append(win)
        ctr_mid = self.multigrid.n_windows - 1

        # check up
        if self.north is not None and self.north.has_children():
            ctr_top = self.north.children['br'].id_bl
        else:
            win = corr_window.CorrWindow(ctr_x, self.tl_win.y,
                                         self.bl_win.WS)
            self.cw_list.append(win)
            ctr_top = self.multigrid.n_windows - 1

        # check right
        if self.east is not None and self.east.has_children():
            right_mid = self.east.children['bl'].id_tl
        else:
            win = corr_window.CorrWindow(self.br_win.x, ctr_y,
                                         self.bl_win.WS)
            self.cw_list.append(win)
            right_mid = self.multigrid.n_windows - 1

        return left_mid, ctr_btm, ctr_mid, ctr_top, right_mid

    def split(self):
        """Split a cell into 4 child cells. At the same time, update the
        neighbour list of surrounding cells
        """

        # check the cell has not already been split
        if self.has_children():
            raise ValueError("This cell has already been split")

        # if the cell is tier 0 then we definitely don't need to split neighbs
        if self.tier > 0:
            self.split_neighbs_if_needed()

        # create the 5 new correlation windows, if needed, and add
        # new ones to the list
        # return the ids of the new cw's for adding in the new cells
        lm, cb, cm, ct, rm = self.create_new_corrWindows()

        # now create the cells
        bl = GridCell(self.multigrid, self.id_bl, cb, lm, cm)
        br = GridCell(self.multigrid, cb, self.id_br, cm, rm)
        tl = GridCell(self.multigrid, lm, cm, self.id_tl, ct)
        tr = GridCell(self.multigrid, cm, rm, ct, self.id_tr)
        self.children = {'bl': bl, 'br': br, 'tl': tl, 'tr': tr}

        # define the new cells tiers
        bl.tier, br.tier, tl.tier, tr.tier = (self.tier + 1,
                                              self.tier + 1,
                                              self.tier + 1,
                                              self.tier + 1)

        # set the parents
        bl.parent, br.parent, tl.parent, tr.parent = (self,
                                                      self,
                                                      self,
                                                      self)

        # set the bottom left index for each of the new cells
        bl.ix, bl.iy = self.ix*2, self.iy*2
        br.ix, br.iy = self.ix*2+1, self.iy*2
        tl.ix, tl.iy = self.ix*2, self.iy*2+1
        tr.ix, tr.iy = self.ix*2+1, self.iy*2+1

        # Create a new tier if it is needed
        if bl.tier > self.multigrid.max_tier:
            self.multigrid.new_tier()

        # Add the references of the newly created windows to the grids
        ix_bl, iy_bl = self.ix*2, self.iy*2
        tmp_grid = self.multigrid.grids[bl.tier]
        tmp_grid._array[iy_bl + 1][ix_bl] = self.cw_list[lm]
        tmp_grid._array[iy_bl + 0][ix_bl+1] = self.cw_list[cb]
        tmp_grid._array[iy_bl + 1][ix_bl+1] = self.cw_list[cm]
        tmp_grid._array[iy_bl + 2][ix_bl+1] = self.cw_list[ct]
        tmp_grid._array[iy_bl + 1][ix_bl+2] = self.cw_list[rm]

        # set known neigbours
        # -----------
        # | tl | tr |
        # -----------
        # | bl | br |
        # -----------
        bl.north, bl.east = tl, br
        br.north, br.west = tr, bl
        tl.south, tl.east = bl, tr
        tr.south, tr.west = br, tl

        # look for neighbours of the newly created cells
        self.update_child_neighbours()

        # finally, add the cells into the multigrid object
        self.multigrid.cells.append(bl)
        self.multigrid.cells.append(br)
        self.multigrid.cells.append(tl)
        self.multigrid.cells.append(tr)

    @property
    def coordinates(self):
        """Return the coordinates of the current cell going anti clockwise
        from the bottom left
        """
        return [(self.bl_win.x, self.bl_win.y),
                (self.br_win.x, self.br_win.y),
                (self.tr_win.x, self.tr_win.y),
                (self.tl_win.x, self.tl_win.y), ]

    def update_child_neighbours(self):
        """
        Updates the neighbours of the children of the current cell

        This method searches the neighbours of the current (i.e. parent) cell
        It then updates the childrens neighbours along the shared edge. 

        For example, 
        1. Check cell to north exists, and has children
        3.    set north.children['bl'].south =  self.children['tl']

        """

        bl, br, tl, tr = (self.children['bl'],
                          self.children['br'],
                          self.children['tl'],
                          self.children['tr'],)

        if self.north is not None:
            ney_child = self.north.children
            if ney_child is not None:
                tl.north = ney_child['bl']
                tr.north = ney_child['br']
                ney_child['bl'].south = tl
                ney_child['br'].south = tr

        # check east
        if self.east is not None:
            ney_child = self.east.children
            if ney_child is not None:
                br.east = ney_child['bl']
                tr.east = ney_child['tl']
                ney_child['bl'].west = br
                ney_child['tl'].west = tr

        # check south
        if self.south is not None:
            ney_child = self.south.children
            if ney_child is not None:
                bl.south = ney_child['tl']
                br.south = ney_child['tr']
                ney_child['tl'].north = bl
                ney_child['tr'].north = br

        # check west
        if self.west is not None:
            ney_child = self.west.children
            if ney_child is not None:
                bl.west = ney_child['br']
                tl.west = ney_child['tr']
                ney_child['br'].east = bl
                ney_child['tr'].east = tl

    def print_locations(self):
        print("bl", self.bl_win)
        print("br", self.br_win)
        print("tl", self.tl_win)
        print("tr", self.tr_win)


class Grid():
    def __init__(self, img_dim, spacing):
        """A grid stores references to the relavent CorrWindows for given image
        dimensions and window spacing

        Arguments:
            img_dim {tuple, ints} -- (height, width) of the total grid domain
            spacing {int} -- Spacing between windows
        """

        self.img_dim = img_dim
        self.spacing = spacing
        self.x_vec = np.arange(0, self.img_dim[1], self.spacing)
        self.y_vec = np.arange(0, self.img_dim[0], self.spacing)

        # determine how many 'entries' we need to be able to accomodate
        self.ny = len(self.y_vec)
        self.nx = len(self.x_vec)

        self._array = [[None for j in range(self.nx)]
                       for i in range(self.ny)]

    def get_meshgrid(self):
        """Returns the x and y coordinates in meshgrid form
        """
        return np.meshgrid(self.x_vec, self.y_vec)

    def get_values(self):
        """Returns the u and v displacement values for all the windows in the 
        domain. 
        Returns 0 if there is no CorrWindow available

        Returns:
            nd_array, nd_array: array of u and v values, respectively
        """
        # allocate space for 2 arrays of values
        u_out, v_out = (np.empty((self.ny, self.nx)),
                        np.empty((self.ny, self.nx)))
        u_out[:], v_out[:] = np.nan, np.nan
        for yy in range(self.ny):
            for xx in range(self.nx):
                try:
                    u_out[yy][xx] = self._array[yy][xx].u
                    v_out[yy][xx] = self._array[yy][xx].v
                except AttributeError:
                    pass

        return u_out, v_out


if __name__ == "__main__":
    pass
