import os
import csv
import struct
from collections import defaultdict
from loguru import logger
import re
import numpy as np

from utils import DEFAULT_PALETTE, EXMY_REGEX, MAPXY_REGEX, MAPS_ATTRS


class WAD_file:
    def __init__(self, wad_path: str):
        """This class is used to parse a WAD file and extract its lumps.
        It also provides methods to parse the levels and extract the flats and sprites."""

        if not os.path.isfile(wad_path):
            raise ValueError(f"No file detected at {wad_path}")

        if self.is_wad(wad_path):
            self.wad = open(wad_path, "rb")
        else:
            raise TypeError(f"{wad_path} is not a WAD file.")

        self.lumps = self._get_lumps()
        self.lump_names = [lump[0] for lump in self.lumps]

        self.game_type = "DOOM"
        if "TINTTAB" in self.lump_names:
            self.game_type = "HERETIC"
        if "BEHAVIOR" in self.lump_names:
            self.game_type = "HEXEN"
        logger.info(f"{self.game_type} {self.wad_type} found at {wad_path}.")

        self.palette = self._get_palette()
        self.maps = self._parse_levels()
        self.flats = self._parse_by_markers("FLATS", "F_START", "F_END")
        self.sprites = self._parse_by_markers("SPRITES", "S_START", "S_END")
        self.spritesheets = self._get_spritesheets()
        self.id2sprites = self._parse_things()

    def is_wad(self, path: str) -> bool:
        """Check if the file is a WAD file."""
        with open(path, "rb") as opened_file:

            name, dir_size, dir_offset = struct.unpack("<4sII", opened_file.read(12))
            name = name.decode("ascii")
            if name in ["IWAD", "PWAD"]:
                self.dir_size = dir_size
                self.dir_offset = dir_offset
                self.wad_path = path
                self.wad_type = name

                return True

            return False

    def _get_lumps(self) -> list[tuple[str, int, int]]:
        """Get the list of lumps in the WAD file."""

        # Read number of lumps and directory offset
        self.wad.seek(4)
        data = self.wad.read(8)
        num_lumps, dir_offset = struct.unpack("<ii", data)

        # Go to directory start
        self.wad.seek(dir_offset)
        lumps = []

        # Read each directory entry
        for _ in range(num_lumps):
            lump_data = self.wad.read(16)
            offset, size, name = struct.unpack("<ii8s", lump_data)
            name = name.rstrip(b"\0").decode("ascii")
            lumps.append((name, offset, size))

        return lumps

    def _lump_data(self, offset, size):
        self.wad.seek(offset)
        return self.wad.read(size)

    def _lump_data_by_name(self, lump_name: str):
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
                id2sprite[row[0]] = row[5] + row[6][0]

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

        map_dict = {}
        for map_id in maps_idx:
            lump_subset = self.lumps[map_id + 1 : map_id + len(MAPS_ATTRS) + 1]
            name_subset = self.lump_names[map_id + 1 : map_id + len(MAPS_ATTRS) + 1]

            map_name = self.lump_names[map_id]
            map_dict[map_name] = {}

            for map_attr in MAPS_ATTRS:
                if map_attr not in name_subset:
                    logger.warning(f"{map_name} does not have {map_attr} lump.")

                else:
                    lump_id = name_subset.index(map_attr)
                    map_dict[map_name][map_attr] = lump_subset[lump_id][1:]

        logger.info(f"{len(maps_idx)} levels found in this WAD.")
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

        logger.info(f"{len(res_dict.keys())} {sequence_name} found in this WAD.")
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

    def draw_flat(self, offset: int, size: int) -> np.ndarray:
        if size != 4096:
            raise NotImplementedError("Flats can be only of 64*64 size. For the moment.")

        self.wad.seek(offset)
        flat = self.wad.read(size)

        indices = np.array(struct.unpack("4096B", flat), dtype=np.uint8).reshape((64, 64))  # 8-bit index array
        rgb_image = self.palette[indices]

        return rgb_image

    def _read_patch_data(self, offset: int, size: int, flip=False) -> np.ndarray:
        # See https://doomwiki.org/wiki/Picture_format for documentation

        self.wad.seek(offset)

        width, height, left_offset, top_offset = struct.unpack("<2H2h", self.wad.read(8))

        column_offsets = [struct.unpack("<I", self.wad.read(4))[0] for _ in range(width)]

        image_data = np.zeros((width, height), dtype=np.uint8)
        image_alpha = np.zeros((width, height), dtype=np.uint8)

        for i in range(width):

            inner_offset = column_offsets[i] + offset
            self.wad.seek(inner_offset)  # Move to column start

            while True:
                row_start = struct.unpack("<B", self.wad.read(1))[0]  # Read row start
                if row_start == 0xFF:
                    break  # End of column

                pixel_count = ord(self.wad.read(1))
                _ = self.wad.read(1)  # Skip unused byte

                pixels = list(self.wad.read(pixel_count))
                _ = self.wad.read(1)  # Skip column termination byte

                image_data[i, row_start : row_start + pixel_count] = pixels
                image_alpha[i, row_start : row_start + pixel_count] = 1

        # Some enemies have only one direction for sprites and use a left-right flip for the other.
        if flip:
            image_data = np.fliplr(image_data)
            image_alpha = np.fliplr(image_alpha)

        return image_data, image_alpha, left_offset, top_offset

    def draw_patch(self, offset, size):
        """Method to draw a single patch, with alpha channel."""

        img_data, alpha, _, _ = self._read_patch_data(offset, size)

        alpha = alpha.T[:, :, np.newaxis] * np.ones((1, 1, 4))
        rgb_img = self.palette[img_data.T]
        rgba_img = rgb_img * alpha

        return rgba_img

    def map(self, map_name: str):
        map_info = defaultdict(list)

        lump = self._lump_data(*self.maps[map_name]["VERTEXES"])
        vertices = np.array([struct.unpack("<hh", lump[i : i + 4]) for i in range(0, len(lump), 4)])

        lump = self._lump_data(*self.maps[map_name]["LINEDEFS"])
        linedefs = np.array([struct.unpack("<hhhhhhh", lump[i : i + 14]) for i in range(0, len(lump), 14)])
        linedefs = linedefs.astype(np.int16)

        lines = vertices[linedefs[:, 0:2]]
        flags = linedefs[:, 2]

        for line, flag in zip(lines, flags):
            if flag & 0x20:  # Secret
                map_info["secret"].append(line)
            elif flag & 0x01:  # Impassable
                map_info["walls"].append(line)
            elif flag & 0x04:  # Two-sided, can see through
                map_info["steps"].append(line)

        lump = self._lump_data(*self.maps[map_name]["THINGS"])
        things = np.array([struct.unpack("<hhhhh", lump[i : i + 10]) for i in range(0, len(lump), 10)]).astype(np.int16)

        map_info["things"] = things

        return map_info


def main():
    WAD_file("WADs/DOOM2.WAD")


if __name__ == "__main__":
    main()
