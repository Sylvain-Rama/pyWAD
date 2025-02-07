import os
import struct
from loguru import logger

from utils import DEFAULT_PALETTE, HEADER_FORMAT


class WAD_file:
    def __init__(self, wad_path: str = None):
        if not os.path.isfile(wad_path):
            raise ValueError("There is no file")

        if self.is_wad(wad_path):
            logger.info("It's a WAD!")
            self.wad = open(wad_path, "rb")
        else:
            logger.error("Not a WAD")
            raise TypeError("This file is not a WAD file!")

        self.lumps = self._get_lumps()
        self.lump_names = [lump[0] for lump in self.lumps]

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
        for name, offset, size in self.lumps:
            if name == lump_name:
                self.wad.seek(offset)
                return self.wad.read(size)
            else:
                raise ValueError(f"Unknown lump: {lump_name}.")

    def _get_palette(self):
        if "PLAYPAL" not in self.lump_names:
            logger.info("No palette in this WAD file, loading the default one.")
            pal = DEFAULT_PALETTE
        else:

            pal_int = [x for x in self.get_lump_data("PLAYPAL")]
            pal_int = [x for x in DEFAULT_PALETTE]
            pal_iter = iter(pal_int)

            pal = list(zip(pal_iter, pal_iter, pal_iter))[:256]

        self.palette = pal


def main():
    WAD_file("WADs/DOOM.WAD")


if __name__ == "__main__":
    main()
