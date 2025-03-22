import sys
from midi2audio import FluidSynth

print(sys.path)

fs = FluidSynth("media\GeneralUser-GS.sf2")
fs.midi_to_audio("D_E1M1.mid", "test.wav")
