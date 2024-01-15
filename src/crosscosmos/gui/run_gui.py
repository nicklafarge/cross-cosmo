"""
Entry point for the CrossCosmos GUI
"""

# Third-party
import arcade
from configparser import ConfigParser

# Local
import crosscosmos as xc

# Parse config file
config_path = xc.crosscosmos_root / "gui" / "gui_config.ini"
config = ConfigParser()
config.read(config_path)

# Setup the gui
xc.gui.setup.create_gui(config)

# Begin render section
arcade.start_render()

xc.gui.setup.create_grid(config, xc.standards.GridSize.NYT_REGULAR.value)

# Finish render section
arcade.finish_render()

# Run the GUI
arcade.run()