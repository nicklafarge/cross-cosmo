# Standard
from configparser import ConfigParser
from typing import Tuple

# Third-party
import arcade
import logging
import numpy as np

# Local
import crosscosmos as xc
from crosscosmos.grid import CellStatus

logger = logging.getLogger("gui")

UPDATES_PER_FRAME = 100


class Curser(arcade.SpriteSolidColor):

    def __init__(self, width: int, height: int, color: arcade.Color):

        # Set up parent class
        super().__init__(width, height, color)

        # Used for flipping between image sequences
        self.blink_timer = 0

    def update_animation(self, delta_time: float = 1 / 60):

        self.blink_timer += 1
        if self.blink_timer > 7 * UPDATES_PER_FRAME:
            self.blink_timer = 0

        frame = self.blink_timer // UPDATES_PER_FRAME
        if frame % 2 == 0:

            if self.color == arcade.color.BLACK:
                print("Curser white")
                self.color = arcade.color.WHITE
            else:
                print("Curser black")
                self.color = arcade.color.BLACK


class CrossCosmosGame(arcade.Window):
    def __init__(self, config_in: ConfigParser, grid_in: xc.grid.Grid):
        super().__init__(config_in.getint('window', 'width'),
                         config_in.getint('window', 'height'),
                         config_in['window']['title'])

        self.grid = grid_in

        # Frame counter
        self.n_frames = 0

        self.inner_margin = config_in.getint('grid', 'inner_margin')
        self.outer_margin = config_in.getint('grid', 'outer_margin')
        total_inner_margin = (grid.row_count - 1) * self.inner_margin
        self.grid_height = self.height - (2 * self.outer_margin) - total_inner_margin
        self.square_size = int(self.grid_height // grid.row_count)

        # Set the background color of the window
        self.background_color = arcade.color.BLACK

        # One dimensional list of all sprites in the two-dimensional sprite list
        self.grid_sprite_list = arcade.SpriteList()

        # This will be a two-dimensional grid of sprites to mirror the two
        # dimensional grid of numbers. This points to the SAME sprites that are
        # in grid_sprite_list, just in a 2d manner.
        # self.grid_sprites = []
        self.grid_sprites = np.empty(grid.grid_size, dtype=arcade.Sprite)
        self.grid_sprites2 = np.empty(grid.grid_size, dtype=arcade.Sprite)
        self.text_labels = np.empty(grid.grid_size, dtype=arcade.Text)

        self.text_curser_blink_frequency = 30
        text_curser = arcade.SpriteSolidColor(2, int(self.square_size * 0.45), arcade.color.WHITE)
        self.text_curser = text_curser
        self.curser_visible = True

        # Create a list of solid-color sprites to represent each grid location
        for row in range(grid.row_count):
            for column in range(grid.col_count):
                # Create grid
                x = column * (self.square_size + self.inner_margin) + (self.square_size / 2 + self.outer_margin)
                y = row * (self.square_size + self.inner_margin) + (self.square_size / 2 + self.outer_margin)
                sprite = arcade.SpriteSolidColor(self.square_size, self.square_size, arcade.color.WHITE)
                sprite.center_x = x
                sprite.center_y = y
                self.grid_sprites[row, column] = sprite
                self.grid_sprite_list.append(sprite)

                # Store the location in the grid
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(row, column)
                self.grid[grid_row, grid_col].gui_coordinates = (x, y)
                self.grid[grid_row, grid_col].gui_row = row
                self.grid[grid_row, grid_col].gui_col = column

                # Cursor
                if row == grid.row_count - 1 and column == 0:
                    self.grid_sprite_list.append(text_curser)
                    self.move_cursor(grid_row, grid_col)
                # text_curser = arcade.SpriteSolidColor(3, int(self.square_size * 0.45), arcade.color.WHITE)
                # text_curser.center_x = x
                # text_curser.center_y = y
                # self.grid_sprites2[row, column] = text_curser

                # Create text labels
                half_square = self.square_size / 2
                t = arcade.Text(text="",
                                start_x=x - half_square * 0.7,
                                start_y=y + half_square * 0.7,
                                color=arcade.color.BLACK,
                                anchor_x='center',
                                anchor_y='center',
                                font_size=10)
                self.text_labels[row, column] = t

    def on_draw(self):
        """
        Render the screen.
        """
        # We should always start by clearing the window pixels
        self.clear()

        # Batch draw the grid sprites
        self.grid_sprite_list.draw()

        # Render the text_curser
        # self.text_curser.draw()

        # Draw the text labels
        for t in self.text_labels.flatten():
            t.draw()

    def on_update(self, delta_time: float):
        self.n_frames += 1
        # print(self.n_frames)
        # self.text_curser.update_animation()
        if self.curser_visible and self.n_frames % self.text_curser_blink_frequency == 0:
            if self.text_curser.color == arcade.color.BLACK:
                self.text_curser.color = arcade.color.WHITE
            else:
                self.text_curser.color = arcade.color.BLACK

        self.draw_answer_numbers()

    def draw_answer_numbers(self):
        # Draw grid numbers
        for gui_row in range(self.grid.row_count):
            for gui_col in range(self.grid.col_count):
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
                cell = self.grid[grid_row, grid_col]
                self.text_labels[gui_row, gui_col].text = "" if not cell.answer_number else str(cell.answer_number)

    def on_mouse_press(self, x_grid: float, y_grid: float, button, modifiers):
        """ Called when the user presses a mouse button.
        """

        # See which row/col was clicked
        success, gui_row, gui_column = self.gui_xy_to_gui_row_col(x_grid, y_grid)
        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_column)

        if not success:
            return

        # Toggle black square
        with_shift = modifiers & arcade.key.MOD_SHIFT
        with_cmd = modifiers & arcade.key.MOD_COMMAND
        with_win = modifiers & arcade.key.MOD_WINDOWS
        if with_shift and (with_cmd or with_win):
            self.toggle_black_square(gui_row, gui_column)
            return

        # Lock / unlock
        elif modifiers & arcade.key.MOD_SHIFT:
            pass

        # Select square)
        self.move_cursor(grid_row, grid_col)

        # No modifier - add text

    # def on_key_press(self, symbol, modifiers):
    #
    #     if modifiers & arcade.key.MOD_ES:
    #         print("The shift key is held down")

    def toggle_black_square(self, gui_row: int, gui_column: int):
        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_column)

        grid_cell_is_black = self.grid[grid_row, grid_col].status == CellStatus.BLACK
        gui_is_black = self.grid_sprites[gui_row][gui_column].color == arcade.color.BLACK

        if grid_cell_is_black != gui_is_black:
            raise RuntimeError("grid/gui black cells have fallen out of sync")

        if grid_cell_is_black:
            self.grid.set_grid(grid_row, grid_col, "")
            self.grid_sprites[gui_row][gui_column].color = arcade.color.WHITE
            self.text_curser.color = arcade.color.BLUE
        else:
            self.grid.set_grid(grid_row, grid_col, None)
            self.grid_sprites[gui_row][gui_column].color = arcade.color.BLACK
            self.text_curser.color = arcade.color.RED

        self.draw_answer_numbers()

    def hide_curser(self):
        self.curser_visible = False

    def show_curser(self):
        self.curser_visible = True

    def move_cursor(self, grid_row: int, grid_col: int):
        x, y = self.grid[grid_row, grid_col].gui_coordinates
        self.text_curser.center_x = x - self.square_size / 5
        self.text_curser.center_y = y
        self.show_curser()

    def gui_row_col_to_grid_row_col(self, gui_row: int, gui_col: int) -> Tuple[int, int]:
        return self.grid.row_count - gui_row - 1, gui_col

    def gui_xy_to_gui_row_col(self, x_grid: float, y_grid: float) -> Tuple[bool, int, int]:
        # Adjust for outer margins
        x = x_grid - self.outer_margin
        y = y_grid - self.outer_margin

        # Convert the clicked mouse position into grid coordinates
        col = int(x // (self.square_size + self.inner_margin))
        row = int(y // (self.square_size + self.inner_margin))

        # Make sure we are on-grid. It is possible to click in the upper right
        # corner in the margin and go to a grid location that doesn't exist
        if row >= self.grid.row_count or col >= self.grid.col_count:
            # Simply return from this method since nothing needs updating
            return False, 0, 0

        return True, row, col


# def on_mouse_press(self, x, y, button, modifiers):
#     """
#     Called when the user presses a mouse button.
#     """
#
#     # Ignore if in margins
#     if x < self.outer_margin or x > (self.width - self.outer_margin):
#         return
#
#     if y < self.outer_margin or y > (self.height - self.outer_margin):
#         return
#
#     # Convert the clicked mouse position into grid coordinates
#     column = int((x + self.outer_margin) // (self.square_size + self.inner_margin))
#     row = int((y + self.outer_margin) // (self.square_size + self.inner_margin))
#
#     print(f"Click coordinates: ({x}, {y}). Grid coordinates: ({row}, {column})")
#
#     # Make sure we are on-grid. It is possible to click in the upper right
#     # corner in the margin and go to a grid location that doesn't exist
#     if row >= self.grid.row_count or column >= self.grid.col_count:
#         # Simply return from this method since nothing needs updating
#         return
#
#     # Flip the color of the sprite
#     if self.grid_sprites[row][column].color == arcade.color.WHITE:
#         self.grid_sprites[row][column].color = arcade.color.GREEN
#     else:
#         self.grid_sprites[row][column].color = arcade.color.WHITE


# def main():


if __name__ == "__main__":
    # Parse config file
    config_path = xc.crosscosmos_root / "gui" / "gui_config.ini"
    config = ConfigParser()
    config.read(config_path)

    size = 6, 6
    # size = 14, 14
    lc = xc.corpus.Corpus.from_test()
    grid = xc.grid.Grid(size, lc)

    CrossCosmosGame(config, grid)
    arcade.run()
    # main()
