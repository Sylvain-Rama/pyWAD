MIDI_PERCUSSION_CHAN = 9
MUS_PERCUSSION_CHAN = 15

# MUS event codes
class Musevent:
    mus_releasekey = 0x00
    mus_presskey = 0x10
    mus_pitchwheel = 0x20
    mus_systemevent = 0x30
    mus_changecontroller = 0x40
    mus_scoreend = 0x60

# MIDI event codes
class Midievent:
    midi_releasekey = 0x80
    midi_presskey = 0x90
    midi_aftertouchkey = 0xA0
    midi_changecontroller = 0xB0
    midi_changepatch = 0xC0
    midi_aftertouchchannel = 0xD0
    midi_pitchwheel = 0xE0

# Structure to hold MUS file header
class MusHeader:
    def __init__(self):
        self.id = bytearray(4)
        self.scorelength = 0
        self.scorestart = 0
        self.primarychannels = 0
        self.secondarychannels = 0
        self.instrumentcount = 0

# MIDI header
midiheader = bytearray([
    ord('M'), ord('T'), ord('h'), ord('d'),  # Main header
    0x00, 0x00, 0x00, 0x06,  # Header size
    0x00, 0x00,  # MIDI type (0)
    0x00, 0x01,  # Number of tracks
    0x00, 0x46,  # Resolution
    ord('M'), ord('T'), ord('r'), ord('k'),  # Start of track
    0x00, 0x00, 0x00, 0x00  # Placeholder for track length
])

# Cached channel velocities
channelvelocities = [127] * 16

# Timestamps between sequences of MUS events
queuedtime = 0

# Counter for the length of the track
tracksize = 0

controller_map = [
    0x00, 0x20, 0x01, 0x07, 0x0A, 0x0B, 0x5B, 0x5D,
    0x40, 0x43, 0x78, 0x7B, 0x7E, 0x7F, 0x79
]

channel_map = [-1] * 16  # Assuming NUM_CHANNELS = 16

def write_time(time, midioutput):
    buffer = time & 0x7F

    while (time >>= 7) != 0:
        buffer <<= 8
        buffer |= ((time & 0x7F) | 0x80)

    while True:
        writeval = buffer & 0xFF
        if midioutput.write(bytes([writeval])) != 1:
            return True
        tracksize += 1
        if (buffer & 0x80) != 0:
            buffer >>= 8
        else:
            queuedtime = 0
            return False

def write_end_track(midioutput):
    endtrack = [0xFF, 0x2F, 0x00]

    if write_time(queuedtime, midioutput):
        return True

    if midioutput.write(bytes(endtrack)) != 3:
        return True

    tracksize += 3
    return False

def write_press_key(channel, key, velocity, midioutput):
    working = Midievent.midi_presskey | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(bytes([working])) != 1:
        return True
    if midioutput.write(bytes([key & 0x7F])) != 1:
        return True
    if midioutput.write(bytes([velocity & 0x7F])) != 1:
        return True
    tracksize += 3
    return False

def write_release_key(channel, key, midioutput):
    working = Midievent.midi_releasekey | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(bytes([working])) != 1:
        return True
    if midioutput.write(bytes([key & 0x7F])) != 1:
        return True
    if midioutput.write(bytes([0])) != 1:
        return True
    tracksize += 3
    return False

def write_pitch_wheel(channel, wheel, midioutput):
    working = Midievent.midi_pitchwheel | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(bytes([working])) != 1:
        return True
    if midioutput.write(bytes([wheel & 0x7F])) != 1:
        return True
    if midioutput.write(bytes([(wheel >> 7) & 0x7F])) != 1:
        return True
    tracksize += 3
    return False

def write_change_patch(channel, patch, midioutput):
    working = Midievent.midi_changepatch | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(bytes([working])) != 1:
        return True
    if midioutput.write(bytes([patch & 0x7F])) != 1:
        return True
    tracksize += 2
    return False

def write_change_controllermax_valued(channel, control, value, midioutput):
    working = Midievent.midi_changecontroller | channel
    if write_time(queuedtime, midioutput):
        return True
    if midioutput.write(bytes([working])) != 1:
        return True
    if midioutput.write(bytes([control & 0x7F])) != 1:
        return True
    working = value
    if working & 0x80:
        working = 0x7F
    if midioutput.write(bytes([working])) != 1:
        return True
    tracksize += 3
    return False

def write_change_controllermax_valueless(channel, control, midioutput):
    return write_change_controllermax_valued(channel, control, 0, midioutput)

def allocate_midi_channel():
    max_val = -1
    for i in range(16):
        if channel_map[i] > max_val:
            max_val = channel_map[i]
    result = max_val + 1
    if result == MIDI_PERCUSSION_CHAN:
        result += 1
    return result

def get_midi_channel(mus_channel, midioutput):
    if mus_channel == MUS_PERCUSSION_CHAN:
        return MIDI_PERCUSSION_CHAN
    else:
        if channel_map[mus_channel] == -1:
            channel_map[mus_channel] = allocate_midi_channel()
            write_change_controllermax_valueless(channel_map[mus_channel], 0x7b, midioutput)
        return channel_map[mus_channel]

def read_mus_header(file):
    header = MusHeader()
    result = file.read(4) == header.id
    result &= int.from_bytes(file.read(2), 'little') == header.scorelength
    result &= int.from_bytes(file.read(2), 'little') == header.scorestart
    result &= int.from_bytes(file.read(2), 'little') == header.primarychannels
    result &= int.from_bytes(file.read(2), 'little') == header.secondarychannels
    result &= int.from_bytes(file.read(2), 'little') == header.instrumentcount
    return result

def mus2mid(musinput, midioutput):
    musfileheader = MusHeader()

    if not read_mus_header(musinput):
        return True

    musinput.seek(musfileheader.scorestart)
    midioutput.write(midiheader)

    hitscoreend = 0

    while not hitscoreend:
        eventdescriptor = musinput.read(1)
        if not eventdescriptor:
            return True
        channel = get_midi_channel(eventdescriptor[0] & 0x0F, midioutput)
        event = eventdescriptor[0] & 0x70

        if event == Musevent.mus_releasekey:
            key = musinput.read(1)
            if write_release_key(channel, key[0], midioutput):
                return True
        elif event == Musevent.mus_presskey:
            key = musinput.read(1)
            if key[0] & 0x80:
                channelvelocities[channel] = musinput.read(1)[0] & 0x7F
            if write_press_key(channel, key[0], channelvelocities[channel], midioutput):
                return True
        elif event == Musevent.mus_pitchwheel:
            key = musinput.read(1)
            if write_pitch_wheel(channel, key[0] * 64, midioutput):
                return True
        elif event == Musevent.mus_systemevent:
            controllernumber = musinput.read(1)
            if controllernumber < 10 or controllernumber > 14:
                return True
            if write_change_controllermax_valueless(channel, controller_map[controllernumber[0]], midioutput):
                return True
        elif event == Musevent.mus_changecontroller:
            controllernumber = musinput.read(1)
            controllervalue = musinput.read(1)
            if controllernumber == 0:
                if write_change_patch(channel, controllervalue[0], midioutput):
                    return True
            elif 1 <= controllernumber < 10:
                if write_change_controllermax_valued(channel, controller_map[controllernumber[0]], controllervalue[0], midioutput):
                    return True
        elif event == Musevent.mus_scoreend:
            hitscoreend = 1
        else:
            return True

        if eventdescriptor[0] & 0x80:
            break

        timedelay = 0
        while True:
            working = musinput.read(1)
            if not working:
                return True
            timedelay = timedelay * 128 + (working[0] & 0x7F)
            if not working[0] & 0x80:
                break
        queuedtime += timedelay

    if write_end_track(midioutput):
        return True

    tracksizebuffer = [(tracksize >> 24) & 0xff, (tracksize >> 16) & 0xff, (tracksize >> 8) & 0xff, tracksize & 0xff]
    midioutput.seek(18)
    midioutput.write(bytes(tracksizebuffer))

    return False
