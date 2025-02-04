import os
from struct import unpack, calcsize

HEADER_FORMAT = "<4sII"


class WAD_file:
    def __init__(self, wad_path: str = None):
        if not os.path.isfile(wad_path):
            raise ValueError("There is no file")

        if self.is_wad(wad_path):
            print("It's a WAD!")
        else:
            raise TypeError("This file is not a WAD file!")

    def is_wad(self, path):
        with open(path, "rb") as opened_file:

            magic, dir_size, dir_offset = unpack(
                HEADER_FORMAT, opened_file.read(calcsize(HEADER_FORMAT))
            )
            if magic.decode("ascii") in ["IWAD", "PWAD"]:
                self.dir_size = dir_size
                self.dir_offset = dir_offset
                return True

            return False


def main():
    WAD_file("WADs/DOOM.WAD")


if __name__ == "__main__":
    main()
