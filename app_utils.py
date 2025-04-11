import base64
from enum import Enum, auto


def img_to_bytes(img_path):
    with open(img_path, "rb") as image_file:
        return base64.b64encode(image_file.read())


class Page(Enum):
    MAPS = auto()
    FLATS = auto()
    TEXTURES = auto()
    SPRITES = auto()
    MUSICS = auto()
    SOUNDS = auto()


def page_to_path(page: Page) -> str:
    mapping = {
        Page.MAPS: "st_pages/maps.py",
        Page.FLATS: "st_pages/flats.py",
        Page.TEXTURES: "st_pages/textures.py",
        Page.SPRITES: "st_pages/sprites.py",
        Page.TEXTURES: "st_pages/textures.py",
        Page.MUSICS: "st_pages/musics.py",
    }

    return mapping[page]


def page_to_icon(page: Page) -> str:
    mapping = {
        Page.MAPS: "media/doom-small_maps.png",
        Page.FLATS: "media/doom-small_flats.png",
        Page.TEXTURES: "media/doom-small_textures.png",
        Page.SPRITES: "media/doom-small_sprites.png",
        Page.TEXTURES: "media/doom-small_textures.png",
        Page.MUSICS: "media/doom-small_musics.png",
    }

    return mapping[page]
