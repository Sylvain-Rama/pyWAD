import struct
import re
from collections import defaultdict
import numpy as np
from loguru import logger


def filter_flags_by_bit(flags: np.array, bit_position: int) -> np.array:
    """
    Returns the indices of flags where the given bit_position is set to 1.
    """
    mask = (flags & (1 << bit_position)) != 0
    return np.where(mask)[0]


def parse_old_format(wad, map_name: str) -> dict:

    map_info = defaultdict(list)
    metadata = {}

    lump = wad._lump_data(*wad._maps_lumps[map_name]["VERTEXES"])
    vertices = np.array([struct.unpack("<hh", lump[i : i + 4]) for i in range(0, len(lump), 4)])

    map_lims = (vertices[:, 0].min(), vertices[:, 0].max(), vertices[:, 1].min(), vertices[:, 1].max())
    metadata["map_lims"] = map_lims
    metadata["map_size"] = (map_lims[1] - map_lims[0], map_lims[3] - map_lims[2])
    metadata["map_name"] = map_name

    lump = wad._lump_data(*wad._maps_lumps[map_name]["LINEDEFS"])

    if wad.game_type in ["DOOM", "HERETIC"]:

        linedefs = np.array([struct.unpack("<HHHHHHH", lump[i : i + 14]) for i in range(0, len(lump), 14)])

    elif wad.game_type in ["HEXEN"]:
        linedefs = np.array([struct.unpack("<HHHBBBBBBHH", lump[i : i + 16]) for i in range(0, len(lump), 16)])

    else:
        logger.error("Unable to parse map linedefs.")
        return None
    linecoords = [[int(k), int(v)] for k, v in zip(linedefs[:, 0], linedefs[:, 1])]

    lines = vertices[linecoords]
    flags = linedefs[:, 2]
    specials = linedefs[:, 3]

    map_info["block"] = lines[filter_flags_by_bit(flags, 0)]  # Impassable bit is 0th bit (1 << 0)

    # Some WADs don't have all their linedefs flags properly set.
    # We consider the value of 0 as blocking (it should be 1).
    no_flags = lines[np.where(flags == 0)[0]]
    map_info["block"] = np.concatenate((map_info["block"], no_flags), axis=0)

    map_info["two-sided"] = lines[filter_flags_by_bit(flags, 2)]  # Two-sided
    map_info["secret"] = lines[filter_flags_by_bit(flags, 5)]  # Secrets
    map_info["special"] = lines[np.where(specials != 0)[0]]  # specials

    lump = wad._lump_data(*wad._maps_lumps[map_name]["THINGS"])
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

    map_info["things"] = things_dict
    map_info["metadata"] = metadata

    return map_info
