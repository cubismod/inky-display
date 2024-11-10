import logging

from PIL import ImageFont

logger = logging.getLogger("fonts")


class FontContainer:
    def retrieve(style: str, size: float):
        try:
            return ImageFont.truetype(f"./fonts/IBMPlexSans-{style}.ttf", size)
        except OSError as err:
            logger.error("unable to load font", exc_info=err)
            return None
