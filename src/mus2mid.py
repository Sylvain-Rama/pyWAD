import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import BinaryIO
from loguru import logger


"""
Translation to Python and slight adaptation of mus2mid.c by Ben Ryves, 2006. 
See https://svn.prboom.org/repos/tags/prboom-plus-2.5.0.1/src/mus2mid.c
Added MIDI management by simply saving the MIDI lump to a .mid.
Many thanks to https://github.com/KurtDing for his help on MUS conversion to MIDI in Labview.

"""

# Constants
NUM_CHANNELS = 16
MIDI_PERCUSSION_CHAN = 9
MUS_PERCUSSION_CHAN = 15
MUS_ID = b"MUS\x1a"
MIDI_ID = b"MThd"
OGG_ID = b"OggS"

MUSIC_FORMATS = {MUS_ID: ".mus", MIDI_ID: ".mid", OGG_ID: ".ogg"}


# MUS event codes
class Musevent(IntEnum):
    RELEASEKEY = 0x00
    PRESSKEY = 0x10
    PITCHWHEEL = 0x20
    SYSTEMEVENT = 0x30
    CHANGECONTROLLER = 0x40
    SCOREEND = 0x60


# MIDI event codes
class Midievent(IntEnum):
    RELEASEKEY = 0x80
    PRESSKEY = 0x90
    AFTERTOUCHKEY = 0xA0
    CHANGECONTROLLER = 0xB0
    CHANGEPATCH = 0xC0
    AFTERTOUCHCHANNEL = 0xD0
    PITCHWHEEL = 0xE0


@dataclass
class MusHeader:
    id: bytes
    scorelength: int
    scorestart: int
    primarychannels: int
    secondarychannels: int
    instrumentcount: int


# MIDI header
midiheader = MIDI_ID + struct.pack(">IHHH", 6, 0, 1, 0x46) + b"MTrk" + struct.pack(">I", 0)

# Global state
channelvelocities = [127] * NUM_CHANNELS
controller_map = [0x00, 0x20, 0x01, 0x07, 0x0A, 0x0B, 0x5B, 0x5D, 0x40, 0x43, 0x78, 0x7B, 0x7E, 0x7F, 0x79]
channel_map = [-1] * NUM_CHANNELS


class Mus2Mid:
    def __init__(self, mus_path: str) -> None:

        with open(mus_path, "rb") as musinput:
            header_id = struct.unpack("<4s", musinput.read(4))[0]

            if header_id != MUS_ID:
                raise ValueError(f"Unsupported file format: {header_id}")
            else:
                self.mus_path = mus_path
                self.id = header_id
                logger.info(f"File format detected: {header_id}")

    def read_mus_header(self, musfile: BinaryIO) -> MusHeader:
        """Reads and returns a MUS file header."""
        MUS_header, score_len, score_start, channels, sec_channels, instrCnt, _ = struct.unpack(
            "<4sHHHHHH", musfile.read(16)
        )
        return MusHeader(MUS_header, score_len, score_start, channels, sec_channels, instrCnt)

    def write_time(self, time: int, midioutput: BinaryIO) -> None:
        """Writes variable-length encoded time to the MIDI output."""

        buffer = []
        while time > 0x7F:
            buffer.insert(0, (time & 0x7F) | 0x80)
            time >>= 7
        buffer.append(time & 0x7F)

        for byte in buffer:
            if midioutput.write(struct.pack("B", byte)) != 1:
                raise ValueError(f"Failed to write byte {byte} to MIDI output.")
            self.tracksize += 1

        self.queuedtime = 0

    def write_midi_event(self, event: int, data: list[int], midioutput: BinaryIO) -> None:
        """Writes a complete MIDI event."""

        self.write_time(self.queuedtime, midioutput)

        midioutput.write(struct.pack("B", event))
        for value in data:
            midioutput.write(struct.pack("B", value & 0x7F))
        self.tracksize += 1 + len(data)

    def write_end_track(self, midioutput: BinaryIO) -> None:
        """Writes end of track event."""
        self.write_time(self.queuedtime, midioutput)

        midioutput.write(b"\xff\x2f\x00")

        self.tracksize += 3

    @staticmethod
    def allocate_midi_channel() -> int:
        """Allocates a new MIDI channel."""
        max_channel = max(channel_map)
        result = max_channel + 1
        if result == MIDI_PERCUSSION_CHAN:
            result += 1
        return result

    @staticmethod
    def allocate_midi_channel() -> int:
        """Allocates a new MIDI channel."""
        max_channel = max(channel_map)
        result = max_channel + 1
        if result == MIDI_PERCUSSION_CHAN:
            result += 1
        return result

    def get_midi_channel(self, mus_channel: int, midioutput: BinaryIO) -> int:
        """Returns the MIDI channel mapped to a MUS channel."""
        if mus_channel == MUS_PERCUSSION_CHAN:
            return MIDI_PERCUSSION_CHAN
        if channel_map[mus_channel] == -1:
            channel_map[mus_channel] = self.allocate_midi_channel()
            self.write_midi_event(Midievent.CHANGECONTROLLER | channel_map[mus_channel], [0x7B, 0], midioutput)
        return channel_map[mus_channel]

    def mus2mid(self, musinput: BinaryIO, midioutput: BinaryIO) -> None:
        """Converts a MUS file to MIDI format."""

        musfileheader = self.read_mus_header(musinput)

        musinput.seek(musfileheader.scorestart)
        midioutput.write(midiheader)

        self.queuedtime = 0
        self.tracksize = 0
        hitscoreend = False

        while not hitscoreend:
            while not hitscoreend:
                eventdescriptor = musinput.read(1)
                if not eventdescriptor:
                    raise ValueError("No Event descriptor")
                eventdescriptor = eventdescriptor[0]

                channel = self.get_midi_channel(eventdescriptor & 0x0F, midioutput)
                event = eventdescriptor & 0x70

                if event == Musevent.RELEASEKEY:
                    key = musinput.read(1)[0]
                    self.write_midi_event(Midievent.RELEASEKEY | channel, [key, 0], midioutput)

                elif event == Musevent.PRESSKEY:
                    key = musinput.read(1)[0]
                    if key & 0x80:
                        channelvelocities[channel] = musinput.read(1)[0] & 0x7F
                    self.write_midi_event(
                        Midievent.PRESSKEY | channel, [key & 0x7F, channelvelocities[channel]], midioutput
                    )

                elif event == Musevent.PITCHWHEEL:
                    key = musinput.read(1)[0]
                    self.write_midi_event(
                        Midievent.PITCHWHEEL | channel, [key * 64 & 0x7F, (key * 64) >> 7], midioutput
                    )

                elif event == Musevent.SYSTEMEVENT:
                    controllernumber = musinput.read(1)[0]
                    if 10 <= controllernumber <= 14:
                        self.write_midi_event(
                            Midievent.CHANGECONTROLLER | channel, [controller_map[controllernumber], 0], midioutput
                        )

                elif event == Musevent.CHANGECONTROLLER:
                    controllernumber, controllervalue = musinput.read(2)
                    if controllernumber == 0:
                        self.write_midi_event(Midievent.CHANGEPATCH | channel, [controllervalue], midioutput)
                    elif 1 <= controllernumber <= 9:
                        self.write_midi_event(
                            Midievent.CHANGECONTROLLER | channel,
                            [controller_map[controllernumber], controllervalue],
                            midioutput,
                        )
                elif event == Musevent.SCOREEND:
                    hitscoreend = True

                if eventdescriptor & 0x80:
                    break

            if not hitscoreend:
                timedelay = 0
                while True:
                    working = musinput.read(1)[0]
                    timedelay = (timedelay << 7) | (working & 0x7F)
                    if not (working & 0x80):
                        break
                self.queuedtime += timedelay

        self.write_end_track(midioutput)

        # Write track size
        midioutput.seek(18)
        midioutput.write(struct.pack("<I", self.tracksize))

    def to_midi(self) -> None:
        output_path = self.mus_path[:-4] + ".mid"

        if self.id == MUS_ID:
            with open(self.mus_path, "rb") as musinput, open(output_path, "wb") as midioutput:
                self.mus2mid(musinput, midioutput)
                logger.info(f"Exported MUS {self.mus_path} as a MIDI file to {output_path}.")
            return output_path
        else:
            raise ValueError(f"Unsupported file format: {self.id}")
