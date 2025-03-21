import struct
from enum import Enum, IntEnum
from typing import List, Tuple
from loguru import logger

# Constants
NUM_CHANNELS = 16
MIDI_PERCUSSION_CHAN = 9
MUS_PERCUSSION_CHAN = 15


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


# Structure to hold MUS file header
class MusHeader:
    def __init__(
        self,
        id: bytes,
        scorelength: int,
        scorestart: int,
        primarychannels: int,
        secondarychannels: int,
        instrumentcount: int,
    ):
        self.id = id
        self.scorelength = scorelength
        self.scorestart = scorestart
        self.primarychannels = primarychannels
        self.secondarychannels = secondarychannels
        self.instrumentcount = instrumentcount

    def __repr__(self) -> str:
        return f"MusHeader(id={self.id}, scorelength={self.scorelength}, scorestart={self.scorestart}, primarychannels={self.primarychannels}, secondarychannels={self.secondarychannels}, instrumentcount={self.instrumentcount})"


# Standard MIDI type 0 header + track header
midiheader = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 0x46) + b"MTrk" + struct.pack(">I", 0)

# Cached channel velocities
channelvelocities = [127] * NUM_CHANNELS

# Timestamps between sequences of MUS events
queuedtime = 0

# Counter for the length of the track
tracksize = 0

# Controller map
controller_map = [0x00, 0x20, 0x01, 0x07, 0x0A, 0x0B, 0x5B, 0x5D, 0x40, 0x43, 0x78, 0x7B, 0x7E, 0x7F, 0x79]

# Channel map
channel_map = [-1] * NUM_CHANNELS


def write_time(time: int, midioutput) -> bool:
    global tracksize

    buffer = time & 0x7F
    shifted_time = time >> 7

    while shifted_time != 0:
        buffer <<= 8
        buffer |= (shifted_time & 0x7F) | 0x80
        shifted_time >>= 7

    while True:
        writeval = buffer & 0xFF
        if midioutput.write(struct.pack("B", writeval)) != 1:
            return True
        tracksize += 1
        if (buffer & 0x80) != 0:
            buffer >>= 8
        else:
            global queuedtime
            queuedtime = 0
            return False


def write_end_track(midioutput) -> bool:
    global tracksize
    endtrack = b"\xff\x2f\x00"
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(endtrack) != 3:
        return True
    tracksize += 3
    return False


def write_press_key(channel: int, key: int, velocity: int, midioutput) -> bool:
    global tracksize
    working = Midievent.PRESSKEY | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    working = key & 0x7F
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    working = velocity & 0x7F
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    tracksize += 3
    return False


def write_release_key(channel: int, key: int, midioutput) -> bool:
    global tracksize
    working = Midievent.RELEASEKEY | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    working = key & 0x7F
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    working = 0
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    tracksize += 3
    return False


def write_pitch_wheel(channel: int, wheel: int, midioutput) -> bool:
    logger.info(f"write_pitch_wheel {channel} {wheel}")
    global tracksize
    working = Midievent.PITCHWHEEL | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    working = wheel & 0x7F
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    working = (wheel >> 7) & 0x7F
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    tracksize += 3
    return False


def write_change_patch(channel: int, patch: int, midioutput) -> bool:
    logger.info(f"write_change_patch {channel} {patch}")
    global tracksize
    working = Midievent.CHANGEPATCH | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    working = patch & 0x7F
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    tracksize += 2
    return False


def write_change_controller_valued(channel: int, control: int, value: int, midioutput) -> bool:
    global tracksize
    working = Midievent.CHANGECONTROLLER | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    working = control & 0x7F
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    working = value
    if working & 0x80:
        working = 0x7F
    if midioutput.write(struct.pack("B", working)) != 1:
        return True
    tracksize += 3
    return False


def write_change_controller_valueless(channel: int, control: int, midioutput) -> bool:
    return write_change_controller_valued(channel, control, 0, midioutput)


def allocate_midi_channel() -> int:
    logger.info("allocate_midi_channel")
    max_channel = -1
    for i in range(NUM_CHANNELS):
        if channel_map[i] > max_channel:
            max_channel = channel_map[i]
    result = max_channel + 1
    if result == MIDI_PERCUSSION_CHAN:
        result += 1
    return result


def get_midi_channel(mus_channel: int, midioutput) -> int:
    if mus_channel == MUS_PERCUSSION_CHAN:
        return MIDI_PERCUSSION_CHAN
    else:
        if channel_map[mus_channel] == -1:
            channel_map[mus_channel] = allocate_midi_channel()
            write_change_controller_valueless(channel_map[mus_channel], 0x7B, midioutput)
        return channel_map[mus_channel]


def read_mus_header(file) -> MusHeader:
    id = file.read(4)
    scorelength = struct.unpack("<h", file.read(2))[0]
    scorestart = struct.unpack("<h", file.read(2))[0]
    primarychannels = struct.unpack("<h", file.read(2))[0]
    secondarychannels = struct.unpack("<h", file.read(2))[0]
    instrumentcount = struct.unpack("<h", file.read(2))[0]
    return MusHeader(id, scorelength, scorestart, primarychannels, secondarychannels, instrumentcount)


def mus2mid(musinput, midioutput) -> bool:
    global queuedtime, tracksize
    musfileheader = read_mus_header(musinput)
    logger.info(f"MUS file header: {musfileheader}")
    if musfileheader.id != b"MUS\x1a":
        raise ValueError("Not a MUS file")
    musinput.seek(musfileheader.scorestart)
    midioutput.write(midiheader)
    tracksize = 0
    hitscoreend = False
    while not hitscoreend:
        while not hitscoreend:
            eventdescriptor = musinput.read(1)
            if not eventdescriptor:
                raise ValueError("No Event descriptor")
            eventdescriptor = eventdescriptor[0]
            channel = get_midi_channel(eventdescriptor & 0x0F, midioutput)
            event = eventdescriptor & 0x70
            if event == Musevent.RELEASEKEY:
                key = musinput.read(1)
                if not key:
                    return True
                key = key[0]
                if write_release_key(channel, key, midioutput):
                    return True
            elif event == Musevent.PRESSKEY:
                key = musinput.read(1)
                if not key:
                    return True
                key = key[0]
                if key & 0x80:
                    velocity = musinput.read(1)
                    if not velocity:
                        return True
                    channelvelocities[channel] = velocity[0] & 0x7F
                if write_press_key(channel, key, channelvelocities[channel], midioutput):
                    return True
            elif event == Musevent.PITCHWHEEL:
                key = musinput.read(1)
                if not key:
                    return True
                key = key[0]
                if write_pitch_wheel(channel, key * 64, midioutput):
                    return True
            elif event == Musevent.SYSTEMEVENT:
                controllernumber = musinput.read(1)
                if not controllernumber:
                    return True
                controllernumber = controllernumber[0]
                if controllernumber < 10 or controllernumber > 14:
                    return True
                if write_change_controller_valueless(channel, controller_map[controllernumber], midioutput):
                    return True
            elif event == Musevent.CHANGECONTROLLER:
                controllernumber = musinput.read(1)
                if not controllernumber:
                    return True
                controllernumber = controllernumber[0]
                controllervalue = musinput.read(1)
                if not controllervalue:
                    return True
                controllervalue = controllervalue[0]
                if controllernumber == 0:
                    if write_change_patch(channel, controllervalue, midioutput):
                        return True
                else:
                    if controllernumber < 1 or controllernumber > 9:
                        return True
                    if write_change_controller_valued(
                        channel, controller_map[controllernumber], controllervalue, midioutput
                    ):
                        return True
            elif event == Musevent.SCOREEND:
                hitscoreend = True
            else:
                return True
            if eventdescriptor & 0x80:
                break
        if not hitscoreend:
            timedelay = 0
            while True:
                working = musinput.read(1)
                if not working:
                    return True
                working = working[0]
                timedelay = timedelay * 128 + (working & 0x7F)
                if (working & 0x80) == 0:
                    break
            queuedtime += timedelay
    if write_end_track(midioutput):
        return True
    midioutput.seek(18)
    tracksizebuffer = struct.pack(">I", tracksize)
    if midioutput.write(tracksizebuffer) != 4:
        return True
    return False


# Example usage:
# with open('input.mus', 'rb') as musinput, open('output.mid', 'wb') as midioutput:
#     mus2mid(musinput, midioutput)
