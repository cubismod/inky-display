import logging
from typing import Optional

from PIL import ImageFont

logger = logging.getLogger("fonts")


class FontContainer:
    fonts = dict[str, Optional[ImageFont.FreeTypeFont]]

    def __init__(self):
        self.fonts = dict()

    def retrieve(self, style: str, size: float, icon: bool = False):
        hash = f"{style}{size}"
        font = self.fonts.get(hash, None)
        if not font:
            try:
                if icon:
                    self.fonts[hash] = ImageFont.truetype(
                        "./fonts/MaterialSymbolsSharp.ttf"
                    )
                else:
                    self.fonts[hash] = ImageFont.truetype(
                        f"./fonts/IBMPlexSans-{style}.ttf", size
                    )
            except OSError as err:
                logger.error("unable to load font", exc_info=err)
                return None

        return font
