import struct
import re
from collections import defaultdict
import numpy as np
from loguru import logger
from typing import Union
from dataclasses import dataclass


@dataclass
class ParsedMap:
    map_lims: tuple[float, float, float, float]
    map_dims: tuple[float, float]
    map_name: str
    block: np.array
    twosided: np.array
    special: np.array
    things: dict[int, list[float, float]]
    grouped_things: np.array


def filter_flags_by_bit(flags: np.array, bit_position: int, bit_value=1) -> np.array:
    """
    Returns the indices of flags where the given bit_position is set to value.
    """
    mask = (flags & (1 << bit_position)) == bit_value
    return np.where(mask)[0]


def get_map_dims(vertices, parsed_map: ParsedMap) -> dict[str, float]:

    map_lims = (vertices[:, 0].min(), vertices[:, 0].max(), vertices[:, 1].min(), vertices[:, 1].max())
    parsed_map.map_lims = map_lims
    parsed_map.map_size = (map_lims[1] - map_lims[0], map_lims[3] - map_lims[2])

    return parsed_map


def parse_old_format(wad, parsed_map: ParsedMap) -> ParsedMap:

    map_dict = wad._maps_lumps[parsed_map.map_name]

    lump = wad._lump_data(*map_dict["VERTEXES"])
    vertices = np.array([struct.unpack("<hh", lump[i : i + 4]) for i in range(0, len(lump), 4)])

    parsed_map = get_map_dims(vertices, parsed_map)

    lump = wad._lump_data(*map_dict["LINEDEFS"])

    if wad.game_type in ["DOOM", "HERETIC"]:

        linedefs = np.array([struct.unpack("<HHHHHHH", lump[i : i + 14]) for i in range(0, len(lump), 14)])

    elif wad.game_type in ["HEXEN", "UDMF"]:
        linedefs = np.array([struct.unpack("<HHHBBBBBBHH", lump[i : i + 16]) for i in range(0, len(lump), 16)])

    else:
        logger.error("Unable to parse map linedefs.")
        return None
    linecoords = [[int(k), int(v)] for k, v in zip(linedefs[:, 0], linedefs[:, 1])]

    lines = vertices[linecoords]
    flags = linedefs[:, 2]
    specials = linedefs[:, 3]

    # Some WADs don't have all their linedefs flags properly set.
    # We consider every lines that are not two-sided are blocking
    parsed_map.block = lines[filter_flags_by_bit(flags, 2, bit_value=0)]

    parsed_map.twosided = lines[filter_flags_by_bit(flags, 2)]  # Two-sided
    parsed_map.special = lines[np.where(specials != 0)[0]]  # specials

    lump = wad._lump_data(*map_dict["THINGS"])
    things = np.array([struct.unpack("<HHHHH", lump[i : i + 10]) for i in range(0, len(lump), 10)]).astype(np.int16)

    things_dict = {}
    for thing in things:
        thing_name = wad.id2sprites.get(thing[3], "NONE")
        if thing_name in ["NONE", "none", "none-"]:
            continue
        if thing_name not in things_dict:
            things_dict[thing_name] = {"x": [int(thing[0])], "y": [int(thing[1])]}
        else:
            things_dict[thing_name]["x"].append(int(thing[0]))
            things_dict[thing_name]["y"].append(int(thing[1]))

    # Simple way to get everything for plotting in the maps, but will keep the NONE keys.
    things_dict["all_things"] = {"x": things[:, 0], "y": things[:, 1]}

    parsed_map.things = things_dict

    return parsed_map


def parse_value(value: str) -> Union[str, float, bool]:

    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        return value  # fallback


def parse_udmf_format(wad, parsed_map: ParsedMap) -> ParsedMap:
    # See https://github.com/ZDoom/gzdoom/blob/master/specs/udmf.txt
    # Thanks ChatGPT for the regexes.

    vertices = []
    blocking = []
    twosided = []
    special = []
    things = []

    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    block_re = re.compile(r"(\w+)\s*\{(.*?)\}", re.DOTALL)
    prop_re = re.compile(r"(\w+)\s*=\s*(.*?);")

    for block_match in block_re.finditer(text):
        block_type, content = block_match.groups()
        props = {}
        for prop_match in prop_re.finditer(content):
            key, value = prop_match.groups()
            props[key] = parse_value(value)

        if block_type == "vertex":
            x = props.pop("x", 0.0)
            y = props.pop("y", 0.0)

            vertices.append([x, y])

        elif block_type == "linedef":
            v1 = props.pop("v1", 0)
            v2 = props.pop("v2", 0)

            if "blocking" in props.keys():
                blocking.append([v1, v2])
            if "twosided" in props.keys():
                twosided.append([v1, v2])
            if "special" in props.keys():
                special.append([v1, v2])

        elif block_type == "thing":
            x = props.pop("x", 0.0)
            y = props.pop("y", 0.0)
            type = props.pop("type", 0.0)

            things.append([x, y, type])

        else:
            pass

    blocking = np.array(blocking)
    twosided = np.array(twosided)
    special = np.array(special)
    verts = np.array(vertices)

    parsed_map.things = things

    parsed_map.block = verts[blocking]
    parsed_map.twosided = verts[twosided]
    parsed_map.special = verts[special]

    return parsed_map


def parse_map(wad, map_name: str):
    parsed_map = ParsedMap()
    parsed_map.map_name = map_name
    map_dict = wad.maps[map_name]
    if "TEXTMAP" in map_dict.keys():
        parsed_map = parse_udmf_format(wad, parsed_map)

    elif "LINEDEF" in map_dict.keys():
        parsed_map = parse_old_format(wad, parsed_map)

    else:
        logger.error(f"{map_name} map format is not recognised.")
        return None

    return parsed_map
