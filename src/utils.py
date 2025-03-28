import re


EXMY_REGEX = re.compile(r"^E(?P<episode>[0-9])M(?P<number>[0-9])$")
MAPXY_REGEX = re.compile(r"^MAP(?P<number>[0-9]{2})$")
TEX_REGEX = re.compile(r"^TEXTURE[0-9]$")

MAPS_ATTRS = {
    "DOOM": [
        "THINGS",
        "LINEDEFS",
        "SIDEDEFS",
        "VERTEXES",
        "SEGS",
        "SSECTORS",
        "NODES",
        "SECTORS",
        "REJECT",
        "BLOCKMAP",
    ],
    "HERETIC": [
        "THINGS",
        "LINEDEFS",
        "SIDEDEFS",
        "VERTEXES",
        "SEGS",
        "SSECTORS",
        "NODES",
        "SECTORS",
        "REJECT",
        "BLOCKMAP",
    ],
    "HEXEN": [
        "THINGS",
        "LINEDEFS",
        "SIDEDEFS",
        "VERTEXES",
        "SEGS",
        "SSECTORS",
        "NODES",
        "SECTORS",
        "REJECT",
        "BLOCKMAP",
        "BEHAVIOR",
    ],
}
