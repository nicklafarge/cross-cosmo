"""
Set up functions for creating the GUI/grid
"""

# Standard
from configparser import ConfigParser
from typing import Tuple

# Third party
import arcade


def create_gui(config: ConfigParser):
    window_width = config.getint('window', 'width')
    window_height = config.getint('window', 'height')

    arcade.open_window(window_width, window_height, "CrossCosmos")
    arcade.set_background_color(arcade.csscolor.WHITE_SMOKE)


def create_grid(config: ConfigParser, gridsize: Tuple):
    bottom = config.getint('grid', 'bottom')
    left = config.getint('grid', 'left')
    x = config.getint('grid', 'square_size')

    for i in range(gridsize[0]):
        dx = i * x
        for j in range(gridsize[1]):
            dy = j * x
            arcade.draw_lrtb_rectangle_outline(left + dx,
                                               left + dx + x,
                                               bottom + dy + x,
                                               bottom + dy,
                                               arcade.csscolor.BLACK)
