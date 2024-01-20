"""
Defines a Grid class, interfacing between the data and gui laters

"""

# Standard library
import copy
from enum import Enum
import random
import string
from typing import Tuple, Union

# Third-party
from matplotlib import pyplot as plt
import logging
import numpy as np

# Local
import crosscosmos as xc
from crosscosmos.data_models.pydantic_model import Letter, Word

logger = logging.getLogger(__name__)


class CellStatus(Enum):
    EMPTY = 0
    SET = 1
    LOCKED = 2
    BLACK = 3


class Cell(object):
    def __init__(self,
                 x: int, y: int,
                 status: CellStatus = CellStatus.EMPTY,
                 value: str = "",
                 gui_coordinates: Union[Tuple[float, float], None] = None
                 ):
        self.status = status
        self.value = value
        self.matrix_index = (x, y)
        self.x = x
        self.y = y
        self.gui_coordinates = gui_coordinates

        self.is_h_start = False
        self.is_h_end = False
        self.is_v_start = False
        self.is_v_end = False

        # Kep track of any word that have been removed from consideration due to this cell
        self.removed_words = []

        self.queue_order = list(reversed(string.ascii_uppercase))
        # self.queue = list(string.ascii_uppercase)
        # random.shuffle(self.queue)

        self.queue = copy.deepcopy(self.queue_order)
        random.shuffle(self.queue)
        self.excluded = []

    def update(self, value: str):
        if value == " " or value == "":
            self.status = CellStatus.EMPTY
            self.value = ""
        elif value is None:
            self.status = CellStatus.BLACK
            self.value = None
        elif isinstance(value, str) and len(value) == 1:
            self.status = CellStatus.SET
            self.value = value.upper()
        else:
            raise ValueError(f"Invalid input: {value}")

    def reset_cell(self):
        self.status = CellStatus.EMPTY
        self.value = ""
        self.queue = copy.deepcopy(self.queue_order)
        self.excluded = []

        # Return the word (if any) that is now valid again
        removed_words = self.removed_words
        self.removed_words = []
        return removed_words

    def __repr__(self):
        return f"Cell(val='{self.value}', loc={self.matrix_index})"


class Grid(object):

    def __init__(self, grid_size: Tuple[int, int], corpus: xc.corpus.Corpus):

        if grid_size[0] % 2 != 0 or grid_size[1] % 2 != 0:
            raise ValueError("Currently only even numbers are supported for grids")

        self.grid_size = grid_size
        self.row_count = self.grid_size[0]
        self.col_count = self.grid_size[1]
        self.h_heads = []
        self.v_heads = []

        self.corpus = corpus

        # self.grid = np.full(self.grid_size, ' ', dtype='U1')
        self.grid = np.full(self.grid_size, None, dtype=object)
        for i in range(self.row_count):
            for j in range(self.col_count):
                self.grid[i, j] = Cell(x=i, y=j)
        self.center = [((self.grid_size[0] - 1) / 2), ((self.grid_size[1] - 1) / 2)]

        # Update the heads for horizontal and vertical clues
        self.update_grid_data()

    def __repr__(self):
        return f"Grid(dim=({self.grid_size[0]}, {self.grid_size[1]})"

    def __getitem__(self, x: Tuple[int, int]) -> Cell:
        # Check index
        if (x[0] < 0 or x[0] > self.grid_size[0]) or (x[1] < 0 or x[1] > self.grid_size[1]):
            raise IndexError(f"Index outside grid bounds:({self.grid_size[0]}, {self.grid_size[1]})")

        return self.grid[*x]

    def __setitem__(self, x: Tuple[int, int], value: str):
        self.set_grid(x[0], x[1], value)

    def set_grid(self, x: int, y: int, value: str):
        # Check index
        if (x < 0 or x > self.grid_size[0]) or (y < 0 or y > self.grid_size[1]):
            raise IndexError(f"Index outside grid bounds:({self.grid_size[0]}, {self.grid_size[1]})")

        # Set value
        self.grid[x][y].update(value)

        # Set symmetry
        coord_center = self.corner2center(x, y)
        coord_rot_center = -coord_center[0], -coord_center[1]
        cr1, cr2 = self.center2corner(*coord_rot_center)

        if self.grid[x][y].status != CellStatus.BLACK and self.grid[cr1][cr2].status == CellStatus.BLACK:
            # If the rotated state is black, then reset that black square to default
            self.grid[cr1][cr2].update("")
        elif self.grid[x][y].status == CellStatus.BLACK:
            # Set the rotated state to black
            self.grid[cr1][cr2].update(None)

        # Update heads
        self.update_grid_data()

    def corner2center(self, x: int, y: int) -> Tuple[float, float]:
        """ Convert coordinate measured form corner, to coordinate measured from center of grid

        a: Corner -> Pt         [x,y]
        b: Corner -> Center     self.center
        c: Center -> Pt         [c1,c2]

        a = (b + c)    ->    C = (a - b)
        [c1,c2] = [x,y] - self.center
        """
        return x - self.center[0], y - self.center[1]

    def center2corner(self, c1: float, c2: float) -> Tuple[int, int]:
        """ Convert coordinate measured form center, to coordinate measured from corner

        A: Corner -> Pt         [x,y]
        B: Corner -> Center     self.center
        C: Center -> Pt         [c1,c2]

        A = (B + C)
        self.center + [c1,c2] = [x,y]
        """
        return int(self.center[0] + c1), int(self.center[1] + c2)

    def update_grid_data(self):

        # Update horizontal / vertical heads
        self.h_heads = []
        self.v_heads = []
        for i in range(self.row_count):
            for j in range(self.col_count):

                # Update lists of head nodes
                if self.is_h_start(i, j):
                    self.h_heads.append((i, j))

                if self.is_v_start(i, j):
                    self.v_heads.append((i, j))

                # Update start/end data
                self[i, j].is_h_start = self.is_h_start(i, j)
                self[i, j].is_h_end = self.is_h_end(i, j)
                self[i, j].is_v_start = self.is_v_start(i, j)
                self[i, j].is_v_end = self.is_v_end(i, j)

    def get_h_word_up_to(self, i: int, j: int, as_str=True):
        cells = []

        # Move right until it's the beginning of the word
        is_h_start = False
        while not is_h_start:
            c = self[i, j]
            is_h_start = c.is_h_start
            cells.insert(0, c)
            j -= 1

        cell_list = list(cells)
        if as_str:
            return ''.join([c.value for c in cell_list])
        else:
            return cell_list

    def get_v_word_up_to(self, i: int, j: int, as_str: bool = True):
        cells = []

        # Move up until it's the beginning of the word
        is_v_start = False
        while not is_v_start:
            c = self[i, j]
            is_v_start = c.is_v_start
            cells.insert(0, c)
            i -= 1

        cell_list = list(cells)
        if as_str:
            return ''.join([c.value for c in cell_list])
        else:
            return cell_list

    def is_h_start(self, i: int, j: int) -> bool:
        return j == 0 or (self[i, j - 1].status == xc.grid.CellStatus.BLACK and
                          self[i, j].status != xc.grid.CellStatus.BLACK)

    def is_h_end(self, i: int, j: int) -> bool:
        return j == (self.col_count - 1) or (self[i, j + 1].status == xc.grid.CellStatus.BLACK and
                                             self[i, j].status != xc.grid.CellStatus.BLACK)

    def is_v_start(self, i: int, j: int) -> bool:
        return i == 0 or (self[i - 1, j].status == xc.grid.CellStatus.BLACK and
                          self[i, j].status != xc.grid.CellStatus.BLACK)

    def is_v_end(self, i: int, j: int) -> bool:
        return i == (self.row_count - 1) or (self[i + 1, j].status == xc.grid.CellStatus.BLACK and
                                             self[i, j].status != xc.grid.CellStatus.BLACK)

    def print(self):
        self.to_console()

    def to_console(self):
        out_str = ""
        for i in range(self.grid_size[0]):
            grid_vals = []
            for x in self.grid[i]:
                match x.status:
                    case CellStatus.EMPTY:
                        gv = "-"
                    case CellStatus.BLACK:
                        gv = "■"
                    case _:
                        gv = x.value

                grid_vals += gv

            out_str += " ".join(grid_vals)

            if i < self.grid_size[0] - 1:
                out_str += "\n"
        print(out_str)

    def print_boundaries(self):
        out_str = ""
        for i in range(self.row_count):
            grid_vals = []
            for j in range(self.col_count):
                if self.is_h_start(i, j) and self.is_v_start(i, j):
                    gv = "x"
                elif self.is_h_end(i, j) and self.is_v_end(i, j):
                    gv = "X"
                elif self.is_h_start(i, j) and self.is_v_end(i, j):
                    gv = "y"
                elif self.is_h_end(i, j) and self.is_v_start(i, j):
                    gv = "Y"
                elif self.is_h_start(i, j):
                    gv = "h"
                elif self.is_v_start(i, j):
                    gv = "v"
                elif self.is_h_end(i, j):
                    gv = "H"
                elif self.is_v_end(i, j):
                    gv = "V"
                else:
                    gv = "-"

                grid_vals += gv

            out_str += " ".join(grid_vals)

            if i < self.grid_size[0] - 1:
                out_str += "\n"
        print(out_str)


if __name__ == '__main__':
    lc = xc.corpus.Corpus.from_test()
    g = Grid((4, 4), lc)

    x1, x2 = 0, 2
    c1, c2 = g.corner2center(x1, x2)

    g.to_console()

    plt.figure()
    plt.scatter(*g.corner2center(0, 0), c="k")
    plt.scatter(*g.corner2center(0, 4), c="k")
    plt.scatter(*g.corner2center(4, 0), c="k")
    plt.scatter(*g.corner2center(4, 4), c="k")
    plt.scatter(*g.corner2center(0, 2), c="tab:red")
    plt.scatter(-c1, -c2, c="tab:orange")
    plt.grid()
    plt.show(block=False)
