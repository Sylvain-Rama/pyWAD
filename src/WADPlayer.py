import os
import time
import threading
from loguru import logger

"""
Windows MIDI player and Linux/macOS MIDI to WAV converter using FluidSynth.
On Windows, this uses the winmm.dll library to play MIDI files directly.
On Linux/macOS, this uses the pyfluidsynth library to render MIDI files to WAV format.

Many thanks to https://github.com/KurtDing for showing me a MIDI Windows implementation.
"""


class WinMIDIPlayer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.stop_flag = False

        import ctypes
        try:
            winmm = ctypes.WinDLL("winmm.dll")
            self._mciSendString = winmm.mciSendStringW
            self._ctypes = ctypes
        except OSError as exc:
            raise ImportError(
                "winmm.dll not found. Windows playback unavailable.") from exc

    def mci_send(self, command):
        buffer = self._ctypes.create_unicode_buffer(256)
        self._mciSendString(command, buffer, 256, 0)
        return buffer.value

    def play_midi(self):
        logger.info(f"Playing MIDI file: {self.file_path}")
        self.stop_flag = False
        self.mci_send(f'open "{self.file_path}" type sequencer alias midi')
        self.mci_send("play midi")

        while self.mci_send("status midi mode") == "playing":
            if self.stop_flag:
                logger.info("Stopped by user")
                self.stop_midi()
                break

        if not self.stop_flag:
            logger.info("Stopped at the end")
            self.stop_midi()

    def is_playing(self):
        return self.mci_send("status midi mode") == "playing"

    def stop_midi(self):
        logger.info("Stopping MIDI playback")
        self.stop_flag = True
        self.mci_send("stop midi")
        time.sleep(0.1)
        self.mci_send("close midi")
        time.sleep(0.1)
        self.mci_send("reset midi")

    def play(self, loop_flag=False):
        """Start playback in a background thread."""
        self.loop_flag = loop_flag
        threading.Thread(target=self.play_midi, daemon=True).start()

    def stop(self):
        """Stop playback."""
        self.stop_flag = True


class MIDIWavConverter:
    def __init__(self, file_path, soundfont_path="media/gzdoom.sf2"):
        self.file_path = file_path
        self.soundfont_path = soundfont_path

        try:
            import fluidsynth as _fs
        except ImportError as exc:
            raise ImportError(
                f"Failed to load FluidSynth: {exc}. "
                "Ensure pyfluidsynth is installed ('pip install pyfluidsynth') "
                "and the FluidSynth native library is available "
                "('sudo apt-get install libfluidsynth-dev' on Debian/Ubuntu)."
            ) from exc

        if not os.path.isfile(soundfont_path):
            raise FileNotFoundError(f"SoundFont not found: {soundfont_path}")

        self._fs = _fs

    def to_wav(self, output_path=None):
        """Render the MIDI file to a WAV file using FluidSynth.

        Parameters
        ----------
        output_path : str, optional
            Destination WAV path. Defaults to the MIDI path with a .wav extension.

        Returns
        -------
        str
            Absolute path to the rendered WAV file.
        """

        if output_path is None:
            output_path = os.path.splitext(self.file_path)[0] + ".wav"

        logger.info(
            f"Rendering MIDI file to WAV: {self.file_path} to {output_path}")

        fs = self._fs.Synth()
        fs.setting("audio.driver", "file")
        fs.setting("audio.file.name", output_path)
        fs.setting("audio.file.type", "wav")
        fs.setting("synth.lock-memory", 0)
        fs.sfload(self.soundfont_path)
        fs.midi2audio(self.file_path, output_path)
        fs.delete()

        logger.info(f"WAV written to: {output_path}")
        return output_path
