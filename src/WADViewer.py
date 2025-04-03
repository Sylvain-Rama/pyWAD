import matplotlib.pyplot as plt
import numpy as np
import argparse
import struct
import sys
import os
import shutil
from loguru import logger

sys.path.append("src/")

import WADParser
from palettes import MAP_CMAPS


class WadViewer:
    def __init__(self, wad: WADParser.WAD_file):
        if not isinstance(wad, WADParser.WAD_file):
            raise TypeError(f"WadViewer expects a WAD_file object, got {type(wad)}.")
        self.wad = wad

    def draw_flat(self, patch_name: str, ax=None):

        if patch_name not in self.wad.flats.keys():
            logger.error(f"Patch {patch_name} not found in this WAD.")
            return None

        output_fig = False
        if ax is None:
            fig, ax = plt.subplots(figsize=(4, 4))
            output_fig = True

        offset, size = self.wad.flats[patch_name]
        if size != 4096:
            raise NotImplementedError("Flats can be only of 64*64 size. For the moment.")

        self.wad.bytes.seek(offset)
        flat = self.wad.bytes.read(size)

        indices = np.array(struct.unpack("4096B", flat), dtype=np.uint8).reshape((64, 64))  # 8-bit index array
        rgb_image = self.wad.palette[indices]

        ax.imshow(rgb_image / 255, interpolation="nearest")

        if output_fig:
            fig.suptitle(patch_name)
            fig.tight_layout(pad=1.2)
            return fig

    def draw_map(self, map_name, palette: str = "OMGIFOL", ax=None, scaler: float = 1, show_secret: bool = True):

        if map_name not in self.wad.maps.keys():
            raise ValueError(f"Map {map_name} not found in this WAD.")
        map_data = self.wad.maps[map_name]
        output_fig = False

        if ax is None:
            width, height = map_data["metadata"]["map_size"]
            wh_ratio = width / height

            fig, ax = plt.subplots(figsize=(12, 12 / wh_ratio))

            output_fig = True

        cmap = MAP_CMAPS[palette]

        bckgrd_color = [x / 255 for x in cmap["background"]]

        ax.set_facecolor(bckgrd_color)
        if output_fig:
            fig.patch.set_facecolor(bckgrd_color)

        step_color = [x / 255 for x in cmap["2-sided"]]
        for line in map_data["two-sided"]:
            ax.plot(line[:, 0], line[:, 1], color=step_color, linewidth=0.6)

        block_color = [x / 255 for x in cmap["block"]]
        for line in map_data["block"]:
            ax.plot(line[:, 0], line[:, 1], color=block_color, linewidth=0.6)

        if show_secret:
            secret_color = [x / 255 for x in cmap["secret"]]
            for line in map_data["secret"]:
                ax.plot(line[:, 0], line[:, 1], color=secret_color, linewidth=0.6)

        ax.axis("equal")
        ax.axis("off")

        logger.info(f'Plotted map {map_data["metadata"]["map_name"]}.')

        if output_fig:
            fig.tight_layout(pad=0.2)
            return fig

    def draw_tex(self, tex_name: str, ax=None) -> plt.Figure | None:
        def paste_array(original, paste, x, y):
            """
            Pastes a 2D numpy array into another 2D numpy array at the specified (x, y) position.
            Allows for negative x and y values.
            I miss Labview paste-and-forget function :'(
            """
            orig_h, orig_w = original.shape
            paste_h, paste_w = paste.shape

            # Valid region in the original array
            x_start = max(x, 0)
            y_start = max(y, 0)
            x_end = min(x + paste_w, orig_w)
            y_end = min(y + paste_h, orig_h)

            # Corresponding region in the paste array
            paste_x_start = max(-x, 0)
            paste_y_start = max(-y, 0)
            paste_x_end = paste_x_start + (x_end - x_start)
            paste_y_end = paste_y_start + (y_end - y_start)

            original[y_start:y_end, x_start:x_end] = paste[paste_y_start:paste_y_end, paste_x_start:paste_x_end]

            return original

        if tex_name not in self.wad.textures.keys():
            raise ValueError(f"Texture {tex_name} not found in WAD.")

        output_fig = ax is None
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))

        texture_data = self.wad.textures[tex_name]
        pix_width, pix_height = texture_data["width"], texture_data["height"]

        pixmap = np.zeros((pix_width, pix_height), dtype=np.uint8)
        alphamap = np.zeros((pix_width, pix_height), dtype=np.uint8)

        for patch_name, x, y in texture_data["patches"]:

            if patch_name not in self.wad.lump_names:
                logger.warning(f"Unknown patch '{patch_name}' in texture '{tex_name}'.")
                continue

            idx = self.wad.lump_names.index(patch_name)

            _, offset, size = self.wad.lumps[idx]
            img, alpha, _, _ = self._read_patch_data(offset, size)

            # x and y are flipped as the image will be transposed after
            pixmap = paste_array(pixmap, img, y, x)
            alphamap = paste_array(alphamap, alpha, y, x)

        alphamap = alphamap.T[:, :, np.newaxis] * np.ones((1, 1, 4))

        rgb_img = self.wad.palette[pixmap.T]

        rgba_img = rgb_img * alphamap

        ax.imshow(rgba_img / 255, interpolation="nearest")
        ax.axis("equal")

        if output_fig:
            ax.axis("off")
            fig.tight_layout(pad=1.2)
            return fig

    def _read_patch_data(self, offset: int, size: int) -> np.ndarray:
        # See https://doomwiki.org/wiki/Picture_format for documentation

        self.wad.bytes.seek(offset)

        width, height, left_offset, top_offset = struct.unpack("<2H2h", self.wad.bytes.read(8))

        column_offsets = [struct.unpack("<I", self.wad.bytes.read(4))[0] for _ in range(width)]

        image_data = np.zeros((width, height), dtype=np.uint8)
        image_alpha = np.zeros((width, height), dtype=np.uint8)

        for i in range(width):

            inner_offset = column_offsets[i] + offset
            self.wad.bytes.seek(inner_offset)  # Move to column start

            while True:
                row_start = struct.unpack("<B", self.wad.bytes.read(1))[0]  # Read row start
                if row_start == 0xFF:
                    break  # End of column

                pixel_count = ord(self.wad.bytes.read(1))
                _ = self.wad.bytes.read(1)  # Skip unused byte

                pixels = list(self.wad.bytes.read(pixel_count))
                _ = self.wad.bytes.read(1)  # Skip column termination byte

                image_data[i, row_start : row_start + pixel_count] = pixels
                image_alpha[i, row_start : row_start + pixel_count] = 1

        return image_data, image_alpha, left_offset, top_offset

    def draw_patch(self, offset, size):

        img_data, alpha, left, top = self._read_patch_data(offset, size)

        alpha = alpha.T[:, :, np.newaxis] * np.ones((1, 1, 4))
        rgb_img = self.wad.palette[img_data.T]
        rgba_img = rgb_img * alpha

        return rgba_img

    def draw_sprite(self, sprite_name, ax=None):
        """Method to draw a single patch, with alpha channel."""
        if sprite_name not in self.wad.sprites.keys():
            raise ValueError(f"Unknown patch name {sprite_name} in this WAD.")

        img_data, alpha, _, _ = self._read_patch_data(*self.wad.sprites[sprite_name])

        alpha = alpha.T[:, :, np.newaxis] * np.ones((1, 1, 4))
        rgb_img = self.wad.palette[img_data.T]
        rgba_img = rgb_img * alpha

        return rgba_img


def save_music(wad: WADParser.WAD_file, lump_name: str, output_path: str | None = None) -> None:

    if lump_name not in wad.musics.keys():
        raise ValueError(f"Unknown music lump: {lump_name}.")

    if output_path is None:
        output_path = f"output/{lump_name}.mid"

    temp_path = "output/lump.mus"

    music_lump = wad._lump_data(*wad.musics[lump_name])

    with open(temp_path, "wb") as f:
        f.write(music_lump)

    with open(temp_path, "rb") as musinput, open(output_path, "wb") as midioutput:
        header_id = struct.unpack("<4s", musinput.read(4))[0]

        if header_id == MUS_ID:

            musinput.seek(0)
            mus2mid(musinput, midioutput)
            logger.info(f"Exported MUS {lump_name} as a MIDI file.")

    if header_id == MIDI_ID:

        shutil.copy(temp_path, output_path)
        logger.info(f"Saved MIDI {lump_name} as a MIDI file.")

    elif header_id != MUS_ID:
        logger.info(f"Lump {lump_name} music format not recognised: {header_id}.")

    os.remove(temp_path)


if __name__ == "__main__":

    args = argparse.ArgumentParser()
    args.add_argument("--wad", "-w", type=str, help="Path to WAD file", default="WADs/DOOM2.wad")
    args.add_argument(
        "--command",
        "-c",
        type=str,
        help="Command to run",
        choices=["draw_map", "draw_tex", "get_music"],
        default="draw_map",
    )
    args.add_argument("--map", "-m", type=str, help="Map name", default="E1M1")
    args.add_argument("--palette", "-p", type=str, help="Palette name", default="OMGIFOL")
    args.add_argument("--texture", "-t", type=str, help="Texture name", default="AASTINKY")
    args.add_argument("--music", "-mu", type=str, help="Music lump name", default="D_MAP01")

    args = args.parse_args()
    wad = open_wad_file(args.wad)

    if args.command == "draw_map":
        if args.map == "*":
            maps_to_draw = wad.maps.keys()
        else:
            maps_to_draw = [args.map]

        for map_name in maps_to_draw:
            map_data = wad.map(map_name)
            fig = draw_map(map_data, palette=args.palette)
            fig.savefig(f"output/{map_name}.png", bbox_inches="tight", dpi=300)

    elif args.command == "draw_tex":
        if args.texture == "*":
            textures_to_draw = wad.textures.keys()
        else:
            textures_to_draw = [args.texture]

        for texture_name in textures_to_draw:
            fig = draw_tex(wad, texture_name)
            fig.savefig(f"output/{texture_name}.png", bbox_inches="tight", dpi=300)

    elif args.command == "get_music":
        if args.music == "*":
            musics_to_get = wad.musics.keys()
        else:
            musics_to_get = [args.music]
        for music_name in musics_to_get:
            save_music(wad, music_name)
