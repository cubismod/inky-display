import logging
import os
import shutil
import tempfile
from asyncio import Runner
from pathlib import Path
from zipfile import ZipFile

from aiohttp import ClientConnectionError, ClientSession

FONT_VERSION = "1.1.0"
ICON_VERSION = "6.7.1"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def download(session: ClientSession, tmpdir: tempfile.TemporaryDirectory):
    material_path = Path(tmpdir) / "fontawesome.zip"
    ibm_path = Path(tmpdir) / "ibm-plex-sans.zip"
    try:
        with open(material_path, "wb") as fd:
            async with session.get(
                f"https://use.fontawesome.com/releases/v{ICON_VERSION}/fontawesome-free-{ICON_VERSION}-web.zip"
            ) as resp:
                logger.info(f"{resp.status} {resp.reason} {resp.method} {resp.url}")
                async for chunk in resp.content.iter_chunked(1024):
                    fd.write(chunk)
        with open(ibm_path, "wb") as fd:
            async with session.get(
                f"https://github.com/IBM/plex/releases/download/@ibm/plex-sans@{FONT_VERSION}/ibm-plex-sans.zip"
            ) as resp:
                logger.info(f"{resp.status} {resp.reason} {resp.method} {resp.url}")
                async for chunk in resp.content.iter_chunked(1024):
                    fd.write(chunk)
        with ZipFile(material_path, "r") as zip:
            zip.extractall(
                Path(tmpdir),
                [f"fontawesome-free-{ICON_VERSION}-web/webfonts/fa-solid-900.ttf"],
            )
        with ZipFile(ibm_path, "r") as zip:
            pre = "ibm-plex-sans/fonts/complete/ttf/IBMPlexSans-"
            post = ".ttf"
            styles = [
                "Bold",
                "ExtraLight",
                "Light",
                "Medium",
                "Regular",
                "SemiBold",
                "Text",
                "Thin",
            ]
            memberlist = [f"{pre}{style}{post}" for style in styles]
            zip.extractall(Path(tmpdir), memberlist)
        os.remove(ibm_path)
        os.remove(material_path)
        for file in Path(tmpdir).glob("**/*.ttf"):
            shutil.move(file, Path(tmpdir))

    except ClientConnectionError as err:
        logger.error("Unable to connect to github", exc_info=err)


def move(tmpdir: tempfile.TemporaryDirectory):
    fonts_path = Path.cwd() / "fonts"
    os.makedirs(fonts_path, exist_ok=True)
    shutil.copytree(tmpdir, fonts_path, dirs_exist_ok=True)


async def __main__():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info(f"saving to tmpdir: {tmpdir}")
        async with ClientSession() as session:
            await download(session, tmpdir)
            move(tmpdir)


with Runner() as runner:
    runner.run(__main__())
