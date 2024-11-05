import logging
from inky import YELLOW
from inky.auto import auto
from PIL import Image, ImageDraw

logging.basicConfig(
    format="%(levelname)-8s %(message)s"
)

logger = logging.getLogger(__name__)

def __main__():
    display = auto()

    with Image.open("./display.png") as img:
        display.set_image(img)
        display.show()

__main__()
