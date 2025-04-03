import os
import csv
import struct
import sys
from collections import defaultdict
from loguru import logger
import re
import numpy as np


sys.path.append("src/")
from utils import EXMY_REGEX, MAPXY_REGEX, MAPS_ATTRS, TEX_REGEX
from palettes import DEFAULT_PALETTE


def open_wad_file(wad_path: str):
    """Open a WAD file and return a WAD_file object."""

    if not os.path.isfile(wad_path):
        raise ValueError(f"No file detected at {wad_path}")

    else:
        return WAD_file(open(wad_path, "rb"))


class WAD_file:
    def __init__(self, byte_string: bytes):
        """This class is used to parse a WAD file and extract its lumps.
        It also provides methods to parse the levels and extract the flats and sprites."""

        self._get_directory(byte_string)

        self.lumps = self._get_lumps()
        self.lump_names = [lump[0] for lump in self.lumps]

        self.game_type = "DOOM"
        if "TINTTAB" in self.lump_names:
            self.game_type = "HERETIC"
        if "BEHAVIOR" in self.lump_names:
            self.game_type = "HEXEN"
        logger.info(f"Found a {self.game_type} {self.wad_type}.")

        self.palette = self._get_palette()
        self._maps_lumps = self._parse_levels()
        if self._maps_lumps is not None:
            self.id2sprites = self._parse_things()
            self.maps = {k: self._parse_map(k) for k in self._maps_lumps.keys()}

        self.flats = self._parse_by_markers("FLATS", "F_START", "F_END")
        self.sprites = self._parse_by_markers("SPRITES", "S_START", "S_END")
        self.spritesheets = self._get_spritesheets() if self.sprites else None

        self.textures = self._gather_textures()
        self.musics = self._gather_musics()

    def _get_directory(self, bytestring: bytes):
        """Get the directory of the WAD file."""
        wad_type, dir_size, dir_offset = struct.unpack("<4sII", bytestring.read(12))
        wad_type = wad_type.decode("ascii")
        if wad_type in ["IWAD", "PWAD"]:
            self.dir_size = dir_size
            self.dir_offset = dir_offset
            self.wad_type = wad_type
            self.bytes = bytestring
        else:
            bytestring = "None"
            raise TypeError("This is not a WAD file.")

    def _get_lumps(self) -> list[tuple[str, int, int]]:
        """Get the list of lumps in the WAD file."""

        # Read number of lumps and directory offset
        self.bytes.seek(4)
        data = self.bytes.read(8)
        num_lumps, dir_offset = struct.unpack("<ii", data)

        # Go to directory start
        self.bytes.seek(dir_offset)
        lumps = []

        # Read each directory entry
        for _ in range(num_lumps):
            lump_data = self.bytes.read(16)
            offset, size, name = struct.unpack("<ii8s", lump_data)
            name = name.rstrip(b"\0").decode("ascii")
            lumps.append((name, offset, size))

        return lumps

    def _lump_data(self, offset: int, size: int) -> bytes:
        self.bytes.seek(offset)
        return self.bytes.read(size)

    def _lump_data_by_name(self, lump_name: str) -> bytes:
        if lump_name not in self.lump_names:
            raise ValueError(f"Unknown lump: {lump_name}.")
        else:
            lump_id = self.lump_names.index(lump_name)
            _, offset, size = self.lumps[lump_id]
            return self._lump_data(offset, size)

    def _get_palette(self) -> np.ndarray:
        if "PLAYPAL" not in self.lump_names:
            logger.info(f"No palette in this {self.wad_type}, loading the default one.")
            pal_b = DEFAULT_PALETTE
        else:
            pal_b = self._lump_data_by_name("PLAYPAL")[:768]

        # 14 Palettes are packed all together by [R, G, B, R...] values.
        # The first one is thus 768 bytes long.
        pal_rgb = np.array(struct.unpack("768B", pal_b), dtype=np.uint8).reshape((256, 3))

        # We will output in RGBA format, so adding an alpha channel with full opacity (255)
        pal_rgba = np.hstack((pal_rgb, np.ones((256, 1)) * 255))

        logger.info("Palette extracted.")
        return pal_rgba

    def _parse_things(self) -> dict[str:str]:
        # Load the THINGS IDs to names mapping
        id2sprite = {}
        with open(f"src/THINGS/{self.game_type}.csv", newline="") as csvfile:
            csvreader = csv.reader(csvfile, delimiter=";", quotechar="|")
            header = next(csvreader)  # Skips the column names
            for row in csvreader:
                id2sprite[int(row[0])] = row[5] + row[6][0]

        logger.info(f"{self.game_type} THINGS loaded.")
        return id2sprite

    def _parse_levels(self) -> dict[str : tuple[int, int]]:
        # retrieving maps lumps in DOOM1 or DOOM2 formats
        maps_idx = [i for i, item in enumerate(self.lump_names) if re.search(EXMY_REGEX, item)]
        if not maps_idx:
            maps_idx = [i for i, item in enumerate(self.lump_names) if re.search(MAPXY_REGEX, item)]
            if not maps_idx:
                logger.info("No levels found in this WAD.")
                return None
        n_map_lumps = len(MAPS_ATTRS[self.game_type])
        map_dict = {}
        for map_id in maps_idx:
            lump_subset = self.lumps[map_id + 1 : map_id + n_map_lumps + 1]
            name_subset = self.lump_names[map_id + 1 : map_id + n_map_lumps + 1]

            map_name = self.lump_names[map_id]
            map_dict[map_name] = {}

            for map_attr in MAPS_ATTRS[self.game_type]:
                if map_attr not in name_subset:
                    logger.warning(f"{map_name} does not have {map_attr} lump.")

                else:
                    lump_id = name_subset.index(map_attr)
                    map_dict[map_name][map_attr] = lump_subset[lump_id][1:]

        logger.info(f"Found {len(maps_idx)} level(s) in this WAD.")
        return map_dict

    def _parse_by_markers(
        self, sequence_name: str = "FLATS", m_start: str = "F_START", m_end: str = "F_END"
    ) -> dict[str : tuple[int, int]]:

        if (m_start in self.lump_names) & (m_end in self.lump_names):
            start_idx = self.lump_names.index(m_start)
            end_idx = self.lump_names.index(m_end)

        else:
            logger.info(f"No {sequence_name} found in this WAD.")
            return None

        if end_idx < start_idx:
            start_idx, end_idx = end_idx, start_idx

        sel_lumps = self.lumps[start_idx : end_idx + 1]

        res_dict = {}
        for name, offset, size in sel_lumps:
            # Some lumps are folder markers, with a size of 0. Ignoring them as they don't have any image data.
            if size > 0:
                # But because of this folder structure, in theory 2 different lumps could have the same name.
                # Adding a warning just in case.
                if name in res_dict.keys():
                    logger.warning(f"{sequence_name} {name} is present multiple times in the lumps structure.")
                res_dict[name] = (offset, size)

        logger.info(f"Found {len(res_dict.keys())} {sequence_name} in this WAD.")
        return res_dict

    def _get_spritesheets(self) -> list[tuple[str, int, int]]:
        """Convenient method to group every sprite by their names, to define the animation sequence."""
        sprite_names = set([x[:4] for x in self.sprites.keys()])

        sprite_dict = {}
        for sprite_name in sprite_names:
            sprite_dict[sprite_name] = [x for x in self.sprites.keys() if x.startswith(sprite_name)]

        res = {}
        for name, sprites in sprite_dict.items():

            res[name] = [self.lumps[self.lump_names.index(sprite)] for sprite in sprites]
            res[name] = sorted(res[name], key=lambda x: x[0])

        return res

    def _parse_map(self, map_name: str):

        def filter_flags_by_bit(flags: np.array, bit_position: int) -> np.array:
            """
            Returns the indices of flags where the given bit_position is set to 1.
            """
            mask = (flags & (1 << bit_position)) != 0  # Check if the selected bit is set
            return np.where(mask)[0]

        map_info = defaultdict(list)
        metadata = {}

        lump = self._lump_data(*self._maps_lumps[map_name]["VERTEXES"])
        vertices = np.array([struct.unpack("<hh", lump[i : i + 4]) for i in range(0, len(lump), 4)])

        map_lims = (vertices[:, 0].min(), vertices[:, 0].max(), vertices[:, 1].min(), vertices[:, 1].max())
        metadata["map_lims"] = map_lims
        metadata["map_size"] = (map_lims[1] - map_lims[0], map_lims[3] - map_lims[2])
        metadata["map_name"] = map_name

        lump = self._lump_data(*self._maps_lumps[map_name]["LINEDEFS"])
        linedefs = np.array([struct.unpack("<hhhhhhh", lump[i : i + 14]) for i in range(0, len(lump), 14)])
        linecoords = [[int(k), int(v)] for k, v in zip(linedefs[:, 0], linedefs[:, 1])]

        lines = vertices[linecoords]
        flags = linedefs[:, 2]

        map_info["block"] = lines[filter_flags_by_bit(flags, 0)]  # Impassable bit is 0th bit (1 << 0)
        map_info["two-sided"] = lines[filter_flags_by_bit(flags, 2)]  # Two-sided
        map_info["secret"] = lines[filter_flags_by_bit(flags, 5)]  # Secret b

        lump = self._lump_data(*self._maps_lumps[map_name]["THINGS"])
        things = np.array([struct.unpack("<hhhhh", lump[i : i + 10]) for i in range(0, len(lump), 10)]).astype(np.int16)

        things_dict = defaultdict(list)
        for thing in things:
            things_dict[self.id2sprites.get(thing[3], "NONE")].append((int(thing[0]), int(thing[1])))

        map_info["things"] = things_dict
        map_info["metadata"] = metadata

        return map_info

    def _parse_patches(self):
        lump = self._lump_data_by_name("PNAMES")

        n_patches = int.from_bytes(lump[0:4], byteorder="little")
        patches = []
        for i in range(n_patches):
            patch_name = lump[4 + i * 8 : 4 + (i + 1) * 8].decode("ascii").rstrip("\0")
            patches.append(patch_name)
        return patches

    def _parse_textures(self, lump_name, patches):
        textures = {}

        lump_id = self.lump_names.index(lump_name)
        _, lump_offset, size = self.lumps[lump_id]

        self.bytes.seek(lump_offset)
        texture1_data = self.bytes.read(size)

        numtextures = int.from_bytes(texture1_data[0:4], byteorder="little")
        self.bytes.seek(lump_offset + 4)

        textures_offsets = []
        for i in range(numtextures):
            offset = int.from_bytes(self.bytes.read(4), byteorder="little")
            textures_offsets.append(offset)

        logger.debug(textures_offsets)

        for tx_offset in textures_offsets:
            self.bytes.seek(lump_offset + tx_offset)
            texture_name = self.bytes.read(8).decode("ascii").rstrip("\0")

            mask, width, height, col_dir = struct.unpack("<ihhi", self.bytes.read(12))

            patch_count = int.from_bytes(self.bytes.read(2), byteorder="little")
            map_patches = np.array([struct.unpack("<hhhhh", self.bytes.read(10)) for i in range(patch_count)])

            orig_x = map_patches[:, 0]
            orig_y = map_patches[:, 1]
            patch_idxs = map_patches[:, 2]

            logger.debug(patch_idxs)

            patch_infos = [
                (patches[patch_idxs[i]], int(orig_x[i]), int(orig_y[i]))
                for i in range(patch_count)
                if patches[patch_idxs[i]] in self.lump_names
            ]
            textures[texture_name] = {"width": width, "height": height, "patches": patch_infos}

        return textures

    def _gather_textures(self):
        tex_lumps = [lump for lump in self.lump_names if TEX_REGEX.match(lump)]

        if (len(tex_lumps) == 0) | ("PNAMES" not in self.lump_names):
            logger.info(f"No textures found in this {self.wad_type}.")
            return None

        patches = self._parse_patches()

        textures = {}
        for tex_name in tex_lumps:
            texs = self._parse_textures(tex_name, patches)
            textures.update(texs)

        logger.info(f"Found {len(textures)} textures in {len(tex_lumps)} texture lumps.")
        return textures

    def _gather_musics(self):
        music_lumps = [lump for lump in self.lumps if lump[0].startswith("D_")]

        if len(music_lumps) == 0:
            logger.info(f"No music found in this {self.wad_type}.")
            return None

        music_lumps = {k: (offset, size) for k, offset, size in music_lumps}

        logger.info(f"Found {len(music_lumps)} music lumps.")

        return music_lumps

    def save_mus(self, music_name: str, output_path: str = None):
        if music_name not in self.musics.keys():
            raise ValueError(f"Music {music_name} not found in this {self.wad_type}.")
        if output_path is None:
            output_path = "output/" + music_name + ".mus"

        offset, size = self.musics[music_name]
        self.bytes.seek(offset)
        with open(output_path, "wb") as f:
            f.write(self.bytes.read(size))
        logger.info(f"Saved music {music_name} to {output_path}.")


def main():
    parsed_wad = open_wad_file("WADs/DOOM2.WAD")


if __name__ == "__main__":
    main()
