from pathlib import Path
from pixelme import Pixelate

PADDING = 200
GRID_LINES = True
BLOCK_SIZE = 25


def pixelate(img: Path):
    pix = Pixelate(img, padding=PADDING, grid_lines=GRID_LINES,
                   block_size=BLOCK_SIZE)
    pix.resize((8,8))
    return pix.base64
