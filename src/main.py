import os
import struct
from loguru import logger
import re
import numpy as np

from utils import DEFAULT_PALETTE, HEADER_FORMAT, EXMY_REGEX, MAPXY_REGEX, MAPS_ATTRS


class WAD_file:
    def __init__(self, wad_path: str = None):
        if not os.path.isfile(wad_path):
            raise ValueError(f"No file detected at {wad_path}")

        if self.is_wad(wad_path):
            logger.info(f"{self.wad_type} found at {wad_path}")
            self.wad = open(wad_path, "rb")
        else:
            raise TypeError(f"{wad_path} is not a WAD file.")

        self.lumps = self._get_lumps()
        self.lump_names = [lump[0] for lump in self.lumps]
        self.palette = self._get_palette()
        self.maps = self._parse_levels()
        self.flats = self._parse_by_markers("FLATS", "F_START", "F_END")
        self.sprites = self._parse_by_markers("SPRITES", "S_START", "S_END")

    def is_wad(self, path: str) -> bool:
        with open(path, "rb") as opened_file:

            name, dir_size, dir_offset = struct.unpack(HEADER_FORMAT, opened_file.read(struct.calcsize(HEADER_FORMAT)))
            name = name.decode("ascii")
            if name in ["IWAD", "PWAD"]:
                self.dir_size = dir_size
                self.dir_offset = dir_offset
                self.wad_path = path
                self.wad_type = name

                return True

            return False

    def _get_lumps(self) -> list[tuple[str, int, int]]:

        self.wad.seek(4)

        # Read number of lumps and directory offset
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

    def read_lump_data(self, lump_name: str):
        if lump_name not in self.lump_names:
            raise ValueError(f"Unknown lump: {lump_name}.")
        else:
            lump_id = self.lump_names.index(lump_name)
            _, offset, size = self.lumps[lump_id]
            self.wad.seek(offset)
            return self.wad.read(size)

    def _get_palette(self) -> list:
        if "PLAYPAL" not in self.lump_names:
            logger.info(f"No palette in this {self.wad_type}, loading the default one.")
            pal_b = DEFAULT_PALETTE
        else:
            pal_b = self.read_lump_data("PLAYPAL")[:768]

        # 14 Palettes are packed all together by [R, G, B, R...] values.
        # The first one is thus 768 bytes long.
        pal = np.array(struct.unpack("768B", pal_b), dtype=np.uint8).reshape((256, 3))
        logger.info("Palette extracted.")
        return pal

    def _parse_levels(self) -> dict:
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

    def _parse_by_markers(self, sequence_name: str = "FLATS", m_start: str = "F_START", m_end: str = "F_END"):

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

    def open_flat(self, offset, size):
        if size != 4096:
            raise NotImplementedError("Flats can be only of 64*64 size. For the moment.")

        self.wad.seek(offset)
        flat = self.wad.read(size)

        indices = np.array(struct.unpack("4096B", flat), dtype=np.uint8).reshape((64, 64))  # 8-bit index array
        rgb_image = self.palette[indices]

        return rgb_image


def main():
    WAD_file("WADs/DOOM2.WAD")


if __name__ == "__main__":
    main()
