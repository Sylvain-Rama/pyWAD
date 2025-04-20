import os
import csv
import struct
import sys
from collections import defaultdict
from loguru import logger
import numpy as np
import wave

"""Sources:
https://doomwiki.org/wiki/WAD
https://www.gamers.org/dhs/helpdocs/dmsp1666.html

"""

sys.path.append("src/")
from parser_utils import EXMY_REGEX, MAPXY_REGEX, MAPS_ATTRS, TEX_REGEX
from palettes import DEFAULT_PALETTE
from mus2mid import MUSIC_FORMATS


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
        if "ENDMAP" in self.lump_names:
            self.game_type = "UDMF"
        logger.info(f"Found a {self.game_type} {self.wad_type}.")

        self._maps_lumps, self._misc_lumps = self._parse_lumps()

        self.palette = self._get_palette()
        if self._maps_lumps is not None:
            self.id2sprites = self._parse_things()
            self.maps = {k: self._parse_map(k) for k in self._maps_lumps.keys()}

        self.flats = self._parse_by_markers("FLATS", "F_START", "F_END")
        self.sprites = self._parse_by_markers("SPRITES", "S_START", "S_END")
        self.spritesheets = self._get_spritesheets() if self.sprites else None

        self.textures = self._gather_textures()
        self.musics = self._gather_musics()
        self.sounds = self._gather_sounds()

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
            bytestring = None
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

    def _parse_lumps(self) -> tuple[dict, dict]:
        misc_lumps = {}
        maps_lumps = {}
        lump_names = [x[0] for x in self.lumps]

        maps_names = [x for x in lump_names if EXMY_REGEX.match(x)]
        maps_idxs = [i for i, x in enumerate(lump_names) if EXMY_REGEX.match(x)]

        if len(maps_names) == 0:
            maps_names = [x for x in lump_names if MAPXY_REGEX.match(x)]
            maps_idxs = [i for i, x in enumerate(lump_names) if MAPXY_REGEX.match(x)]

        if len(maps_names) == 1:
            maps_attrs_len = len(MAPS_ATTRS[self.game_type])
        else:
            maps_attrs_len = np.diff(maps_idxs)[0] - 1

        i = 0
        duplicates = []
        while i < len(self.lumps):
            name, offset, size = self.lumps[i]
            if name in maps_names:
                maps_lumps[name] = {}
                for j in range(maps_attrs_len):
                    maps_lumps[name][self.lumps[i + j + 1][0]] = self.lumps[i + j + 1][1:]
                i += maps_attrs_len + 1

            else:
                i += 1
                if name in misc_lumps:
                    duplicates.append(name)
                    continue
                misc_lumps[name] = (offset, size)
        if duplicates:
            logger.info(f"Found {len(duplicates)} duplicated lumps in this {self.wad_type}.")
        return maps_lumps, misc_lumps

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
        thing_type = "DOOM" if self.game_type == "UDMF" else self.game_type
        with open(f"src/THINGS/{thing_type}.csv", newline="") as csvfile:
            csvreader = csv.reader(csvfile, delimiter=";", quotechar="|")
            header = next(csvreader)  # Skips the column names
            for row in csvreader:
                id2sprite[int(row[0])] = row[5] + row[6][0]

        logger.info(f"{self.game_type} THINGS loaded.")
        return id2sprite

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

        res_set = set()
        for name, offset, size in sel_lumps:
            # Some lumps are folder markers, with a size of 0. Ignoring them as they don't have any image data.
            if size > 0:
                # But because of this folder structure, in theory 2 different lumps could have the same name.
                # Adding a warning just in case.
                if name in res_set:
                    logger.warning(f"{sequence_name} {name} is present multiple times in the lumps structure.")
                res_set.add(name)

        logger.info(f"Found {len(res_set)} {sequence_name} between {m_start} and {m_end} in this WAD.")
        return list(res_set)

    def _get_spritesheets(self) -> list[tuple[str, int, int]]:
        """Convenient method to group every sprite by their names."""
        sprite_names = set([x[:4] for x in self.sprites])

        sprite_dict = {}
        for sprite_name in sprite_names:
            sprite_dict[sprite_name] = sorted([x for x in self.sprites if x.startswith(sprite_name)])

        return sprite_dict

    def _parse_map(self, map_name: str) -> dict:

        def filter_flags_by_bit(flags: np.array, bit_position: int) -> np.array:
            """
            Returns the indices of flags where the given bit_position is set to 1.
            """
            mask = (flags & (1 << bit_position)) != 0
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

        if self.game_type in ["DOOM", "HERETIC"]:

            linedefs = np.array([struct.unpack("<HHHHHHH", lump[i : i + 14]) for i in range(0, len(lump), 14)])

        elif self.game_type in ["HEXEN", "UDMF"]:
            linedefs = np.array([struct.unpack("<HHHBBBBBBHH", lump[i : i + 16]) for i in range(0, len(lump), 16)])

        else:
            logger.error("Unable to parse map linedefs.")
            return None
        linecoords = [[int(k), int(v)] for k, v in zip(linedefs[:, 0], linedefs[:, 1])]

        lines = vertices[linecoords]
        flags = linedefs[:, 2]
        specials = linedefs[:, 3]

        map_info["block"] = lines[filter_flags_by_bit(flags, 0)]  # Impassable bit is 0th bit (1 << 0)
        map_info["two-sided"] = lines[filter_flags_by_bit(flags, 2)]  # Two-sided
        map_info["secret"] = lines[filter_flags_by_bit(flags, 5)]  # Secrets
        map_info["special"] = lines[np.where(specials != 0)[0]]  # specials

        lump = self._lump_data(*self._maps_lumps[map_name]["THINGS"])
        things = np.array([struct.unpack("<HHHHH", lump[i : i + 10]) for i in range(0, len(lump), 10)]).astype(np.int16)

        things_dict = {}
        for thing in things:
            thing_name = self.id2sprites.get(thing[3], "NONE")
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

    def _parse_patches(self) -> list:
        lump = self._lump_data_by_name("PNAMES")

        n_patches = int.from_bytes(lump[0:4], byteorder="little")
        patches = []
        for i in range(n_patches):
            patch_name = lump[4 + i * 8 : 4 + (i + 1) * 8].decode("ascii").rstrip("\0")
            patches.append(patch_name)
        return patches

    def _parse_textures(self, lump_name: str, patches: list) -> dict:
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

        for tx_offset in textures_offsets:
            self.bytes.seek(lump_offset + tx_offset)
            texture_name = self.bytes.read(8).decode("ascii").rstrip("\0")

            mask, width, height, col_dir = struct.unpack("<ihhi", self.bytes.read(12))

            patch_count = int.from_bytes(self.bytes.read(2), byteorder="little")
            map_patches = np.array([struct.unpack("<hhhhh", self.bytes.read(10)) for i in range(patch_count)])

            orig_x = map_patches[:, 0]
            orig_y = map_patches[:, 1]
            patch_idxs = map_patches[:, 2]

            patch_infos = [
                (patches[patch_idxs[i]], int(orig_x[i]), int(orig_y[i]))
                for i in range(patch_count)
                if patches[patch_idxs[i]] in self.lump_names  # Only include patches that exist in the WAD
            ]
            # Some PWADs have textures that reference patches not present in the WAD. Skip them.
            if len(patch_infos) > 0:
                textures[texture_name] = {"width": width, "height": height, "patches": patch_infos}

        return textures

    def _gather_textures(self) -> dict:
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

    def _gather_musics(self) -> list[str]:
        music_lumps = [lump for lump in self.lump_names if (lump.startswith("D_") | lump.startswith("MUS_"))]

        if len(music_lumps) == 0:
            logger.info(f"No music found in this {self.wad_type}.")
            return None

        logger.info(f"Found {len(music_lumps)} music lumps.")

        return music_lumps

    def export_music(self, music_name: str) -> str:
        if music_name not in self.lump_names:
            raise ValueError(f"Music {music_name} not found in this {self.wad_type}.")

        offset, size = self._misc_lumps[music_name]

        self.bytes.seek(offset)
        header_id = struct.unpack("<4s", self.bytes.read(4))[0]
        if header_id not in MUSIC_FORMATS.keys():
            raise ValueError(f"Music format not recognised: {header_id}")

        output_path = "output/" + music_name + MUSIC_FORMATS[header_id]

        self.bytes.seek(offset)
        with open(output_path, "wb") as f:
            f.write(self.bytes.read(size))
        logger.info(f"Saved music {music_name} to {output_path}.")

        return output_path

    def _gather_sounds(self):
        sounds = [x for x in self.lump_names if x.startswith("DS")]
        logger.info(f"Fould {len(sounds)} sounds in this {self.wad_type}.")
        return sounds

    def export_sound(self, sound_name: str) -> str:
        if sound_name not in self._misc_lumps.keys():
            raise ValueError(f"Sound {sound_name} not found in this {self.wad_type}.")

        lump_data = self._lump_data_by_name(sound_name)
        sample_rate = struct.unpack_from("<H", lump_data, 2)[0]
        sample_count = struct.unpack_from("<I", lump_data, 4)[0]

        samples = lump_data[8 : 8 + sample_count]

        with wave.open(f"output/{sound_name}.wav", "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(1)  # 8-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples)


def open_wad_file(wad_path: str) -> WAD_file:
    """Open a WAD file and return a WAD_file object."""

    if not os.path.isfile(wad_path):
        raise ValueError(f"No file detected at {wad_path}.")

    else:
        return WAD_file(open(wad_path, "rb"))


def main():
    parsed_wad = open_wad_file("WADs/DOOM2.WAD")


if __name__ == "__main__":
    main()
