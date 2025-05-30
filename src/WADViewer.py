import matplotlib as mpl
import matplotlib.pyplot as plt

from matplotlib.collections import LineCollection
import numpy as np
import argparse
import struct
import re

from loguru import logger

import WADParser
from palettes import MAP_CMAPS

"""Main class to display WAD files.
This class is used to display the content of a WAD file. It can display flats, textures, maps and sprites.

CLI use:

python WADViewer.py -w <path to WAD_file> -m <map pattern> -f <output_format> -p <palette_name> -s <scale> -mw <max_width>

Or use 
python Wadviever.py -h 

to get help on the command line arguments.
"""


class WadViewer:
    def __init__(self, wad: WADParser.WAD_file):
        if not isinstance(wad, WADParser.WAD_file):
            raise TypeError(f"WadViewer expects a WAD_file object, got {type(wad)}.")
        self.wad = wad

    def get_flat_data(self, offset: int, size: int) -> np.ndarray:
        if size == 320 * 200:
            shape = (200, 320)

        elif size % 64 == 0:
            shape = (size // 64, 64)

        else:
            logger.debug(size)
            raise NotImplementedError("This flat has an unknown size.")

        self.wad.bytes.seek(offset)
        flat = self.wad.bytes.read(size)

        indices = np.array(struct.unpack(f"{size}B", flat), dtype=np.uint8).reshape(shape)
        rgb_image = self.wad.palette[indices]

        return rgb_image

    def draw_flat(self, flat_name: str, ax: mpl.axes.Axes | None = None) -> plt.figure:

        if flat_name not in self.wad._misc_lumps.keys():
            logger.error(f"Flat {flat_name} not found in this WAD.")
            return None

        output_fig = False
        if ax is None:
            fig, ax = plt.subplots(figsize=(4, 4))
            output_fig = True

        offset, size = self.wad._misc_lumps[flat_name]

        rgb_image = self.get_flat_data(offset, size)

        ax.imshow(rgb_image / 255, interpolation="nearest", aspect=1.0)

        if output_fig:
            fig.suptitle(flat_name)
            fig.tight_layout(pad=1.2)
            return fig

    def draw_map(
        self,
        map_name: str,
        palette: str = "OMGIFOL",
        max_width: int = 4096,
        scale: float = 2.0,
        ax: mpl.axes.Axes | None = None,
        show_secrets: bool = False,
        show_specials: bool = True,
        show_things: bool = False,
        **kwargs,
    ) -> plt.figure:
        if map_name not in self.wad.maps.keys():
            raise ValueError(f"Map {map_name} not found in this WAD.")

        def parse_kwargs(kwargs):

            # Parse kwargs to get attributes for each type of line
            attribs = ["block", "twosided", "special", "secret", "things"]
            attrib_dict = {}
            for a in attribs:
                attrib_dict[a] = {k.split("__")[1]: v for k, v in kwargs.items() if k.startswith(f"{a}__")}

            return attrib_dict

        supp_args = parse_kwargs(kwargs)

        map_data = self.wad.maps[map_name]

        output_fig = False
        dpi = 150

        if ax is None:
            # Definition of a figure according to scale factor and max width.
            # We assume that 1000 doom units will fit in 1 inch of the figure.
            width, height = map_data.map_dims
            fig_width = min((width / 1000) * scale, max_width / dpi)
            wh_ratio = width / height

            fig, ax = plt.subplots(figsize=(fig_width, fig_width / wh_ratio), dpi=dpi)

            output_fig = True

        cmap = MAP_CMAPS[palette]

        bckgrd_color = [x / 255 for x in cmap["background"]]
        twosided_color = [x / 255 for x in cmap["twosided"]]
        block_color = [x / 255 for x in cmap["block"]]

        linewidth_primary = 0.4 + 0.2 * scale
        linewidth_secondary = 0.2 + 0.2 * scale
        things_size = 2 * scale

        twosided_args = {"colors": twosided_color, "linewidths": linewidth_secondary, "capstyle": "round"} | supp_args[
            "twosided"
        ]
        block_args = {"colors": block_color, "linewidths": linewidth_primary, "capstyle": "round"} | supp_args["block"]

        ax.set_facecolor(bckgrd_color)
        if output_fig:
            fig.patch.set_facecolor(bckgrd_color)

        twosided = LineCollection(map_data.twosided, **twosided_args)
        ax.add_collection(twosided)

        bloc_lines = LineCollection(map_data.block, **block_args)
        ax.add_collection(bloc_lines)

        # secial and secret lines are drawn on top of regular lines.
        if show_specials:
            special_color = [x / 255 for x in cmap["special"]]
            special_args = {"colors": special_color, "linewidths": linewidth_primary} | supp_args["special"]
            special_lines = LineCollection(map_data.special, **special_args)
            ax.add_collection(special_lines)

        if show_secrets:
            if map_data.secret is not None:
                secret_color = [x / 255 for x in cmap["secret"]]
                secret_args = {"colors": secret_color, "linewidths": linewidth_primary} | supp_args["secret"]
                secret_lines = LineCollection(map_data.secret, **secret_args)
                ax.add_collection(secret_lines)

        if show_things:
            things_color = [x / 255 for x in cmap["things"]]
            things_dict = map_data.things
            things_args = {"color": things_color, "s": things_size, "marker": "+"} | supp_args["things"]
            ax.scatter(things_dict["all_things"]["x"], things_dict["all_things"]["y"], **things_args)

        ax.axis("equal")
        ax.axis("off")

        logger.info(f"Plotted map {map_data.map_name}.")

        if output_fig:
            fig.tight_layout(pad=0.2)
            return fig

    def get_tex_data(self, tex_name: str) -> np.ndarray:
        def paste_array(original: np.ndarray, paste: np.ndarray, alpha: np.ndarray, x: int, y: int):
            """
            Pastes a 2D numpy array into another 2D numpy array at the specified (x, y) position.
            Allows for negative x and y values, and only pastes where the alpha channel is > 0.
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

            # We want to paste the new texture only where its transparency is > 0
            original[y_start:y_end, x_start:x_end] = np.where(
                alpha[paste_y_start:paste_y_end, paste_x_start:paste_x_end] > 0,
                paste[paste_y_start:paste_y_end, paste_x_start:paste_x_end],
                original[y_start:y_end, x_start:x_end],
            )

            return original

        texture_data = self.wad.textures[tex_name]
        pix_width, pix_height = texture_data["width"], texture_data["height"]

        pixmap = np.zeros((pix_width, pix_height), dtype=np.uint8)
        alphamap = np.ones((pix_width, pix_height), dtype=np.uint8)

        for patch_name, x, y in texture_data["patches"]:

            if patch_name not in self.wad.lump_names:
                logger.warning(f"Unknown patch '{patch_name}' in texture '{tex_name}'.")
                continue

            idx = self.wad.lump_names.index(patch_name)

            _, offset, size = self.wad.lumps[idx]
            img, alpha, _, _ = self.get_patch_data(offset, size)

            # x and y are flipped as the image will be transposed after
            pixmap = paste_array(pixmap, img, alpha, y, x)

        alphamap = alphamap.T[:, :, np.newaxis]

        rgb_img = self.wad.palette[pixmap.T]

        rgba_img = rgb_img * alphamap

        return rgba_img

    def draw_tex(self, tex_name: str, ax: mpl.axes.Axes | None = None) -> plt.figure:

        if tex_name not in self.wad.textures.keys():
            raise ValueError(f"Texture {tex_name} not found in this WAD.")

        output_fig = ax is None
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))
            fig.patch.set_alpha(0)

        rgba_img = self.get_tex_data(tex_name)

        ax.imshow(rgba_img / 255, interpolation="nearest", aspect=1.2)
        ax.axis("equal")
        ax.patch.set_alpha(0)

        if output_fig:
            ax.axis("off")
            fig.tight_layout(pad=1.2)
            return fig

    def get_patch_data(self, offset: int, size: int) -> np.ndarray:
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

    def draw_patch(self, patch_name: str, ax: mpl.axes.Axes | None = None) -> plt.figure:

        if patch_name not in self.wad._misc_lumps.keys():
            raise ValueError("Invalid Patch name")

        output_fig = False
        if ax is None:
            fig, ax = plt.subplots(figsize=(4, 4))
            output_fig = True

        offset, size = self.wad._misc_lumps[patch_name]

        img_data, alpha, left, top = self.get_patch_data(offset, size)

        alpha = alpha.T[:, :, np.newaxis] * np.ones((1, 1, 4))
        rgb_img = self.wad.palette[img_data.T]
        rgba_img = rgb_img * alpha

        ax.imshow(rgba_img / 255, interpolation="nearest", aspect=1.2)
        if output_fig:
            fig.suptitle(patch_name)
            fig.tight_layout(pad=1.2)
            return fig


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--wad", "-w", type=str, help="Path to WAD file", default="WADs/DOOM.WAD")
    parser.add_argument("--map", "-m", type=str, help="Map name pattern to draw, e.g. E1M1 / E1M. / .", default="E1M1")
    parser.add_argument("--palette", "-p", type=str, help="Palette name", default="OMGIFOL")
    parser.add_argument("--format", "-f", type=str, help="Output format", default="png", choices=["png", "svg"])
    parser.add_argument("--scale", "-s", type=float, help="Scale of the map", default=2.0)
    parser.add_argument("--max_width", "-mw", type=int, help="Max width (px) of the map", default=4096)

    args = parser.parse_args()
    wad = WADParser.open_wad_file(args.wad)
    viewer = WadViewer(wad)

    maps_to_draw = [x for x in wad.maps.keys() if re.match(args.map, x)]
    if len(maps_to_draw) == 0:
        raise ValueError(f"Invalid map pattern: {args.map}")

    for map_name in maps_to_draw:
        fig = viewer.draw_map(map_name, palette=args.palette, scale=args.scale, max_width=args.max_width)
        fig.savefig(f"output/{args.wad.split('/')[-1]}_{map_name}.{args.format}", bbox_inches="tight", dpi=150)
