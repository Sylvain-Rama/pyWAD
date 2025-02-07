import os
import struct
from loguru import logger

from utils import DEFAULT_PALETTE, HEADER_FORMAT


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

    def is_wad(self, path):
        with open(path, "rb") as opened_file:

            magic, dir_size, dir_offset = struct.unpack(
                HEADER_FORMAT, opened_file.read(struct.calcsize(HEADER_FORMAT))
            )
            if magic.decode("ascii") in ["IWAD", "PWAD"]:
                self.dir_size = dir_size
                self.dir_offset = dir_offset
                self.wad_path = path
                self.wad_type = magic.decode("ascii")

                return True

            return False

    def _get_lumps(self):

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

    def get_lump_data(self, lump_name: str):
        if lump_name not in self.lump_names:
            raise ValueError(f"Unknown lump: {lump_name}.")
        else:
            lump_id = self.lump_names.index(lump_name)
            _, offset, size = self.lumps[lump_id]
            self.wad.seek(offset)
            return self.wad.read(size)

    def _get_palette(self):
        if "PLAYPAL" not in self.lump_names:
            logger.info(f"No palette in this {self.wad_type}, loading the default one.")
            pal_b = DEFAULT_PALETTE
        else:
            pal_b = self.get_lump_data("PLAYPAL")

        # 14 Palettes are packed all together by [R, G, B, R...] values.
        # Making a list of tuples [(R, G, B), ...] and taking only the first one (256 colors).
        pal_iter = iter(pal_b)
        pal = list(zip(pal_iter, pal_iter, pal_iter))[:256]
        logger.info("Palette extracted.")
        return pal


def main():
    WAD_file("WADs/DOOM.WAD")


if __name__ == "__main__":
    main()
