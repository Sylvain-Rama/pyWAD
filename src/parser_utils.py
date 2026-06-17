import re


EXMY_REGEX = re.compile(r"^E(?P<episode>[0-9])M(?P<number>[0-9])$")
MAPXY_REGEX = re.compile(r"^MAP(?P<number>[0-9]{2}[A-Z]?)$")
TEX_REGEX = re.compile(r"^TEXTURE[0-9]{1}$")

MAPS_LUMPS = [
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
    "TEXTMAP",
    "DIALOGUE",
    "ZNODES",
    "SCRIPTS",
    "ENDMAP",
]
