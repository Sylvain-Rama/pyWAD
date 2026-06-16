import sys
import os
import time
import threading
from loguru import logger

"""
Cross-platform MIDI player.
- Windows: uses winmm.dll via ctypes (MCI interface).
- Linux / other: uses FluidSynth (pyfluidsynth) to render MIDI to a WAV
  file, which can then be served to a browser via st.audio().

Example usage (Windows real-time playback):
    player = MIDIPlayer("path/to/your/file.mid")
    player.play()
    time.sleep(10)
    player.stop()

Example usage (Linux – render to WAV):
    player = MIDIPlayer("path/to/your/file.mid", soundfont_path="media/gzdoom.sf2")
    wav_path = player.to_wav("output/song.wav")

Many thanks to https://github.com/KurtDing for the original Windows implementation.
"""


class MIDIPlayer:
    def __init__(self, file_path, soundfont_path=None):
        self.file_path = file_path
        self.stop_flag = False

        if sys.platform == "win32":
            self._init_windows()
        else:
            self._init_fluidsynth(soundfont_path)

    def _init_windows(self):
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
        if sys.platform == "win32":
            return self.mci_send("status midi mode") == "playing"
        return False

    def stop_midi(self):
        logger.info("Stopping MIDI playback")
        self.stop_flag = True
        self.mci_send("stop midi")
        time.sleep(0.1)
        self.mci_send("close midi")
        time.sleep(0.1)
        self.mci_send("reset midi")

    def play(self, loop_flag=False):
        """Start playback in a background thread (Windows only)."""
        self.loop_flag = loop_flag
        threading.Thread(target=self.play_midi, daemon=True).start()

    def stop(self):
        """Stop playback (Windows only)."""
        self.stop_flag = True

    def _init_fluidsynth(self, soundfont_path):
        import os
        try:
            import fluidsynth as _fs
        except ImportError as exc:
            raise ImportError(
                "pyfluidsynth is not installed. Run: pip install pyfluidsynth"
            ) from exc

        if soundfont_path is None:
            # Default to the bundled soundfont relative to this file's location
            _here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            soundfont_path = os.path.join(_here, "media", "gzdoom.sf2")

        if not os.path.isfile(soundfont_path):
            raise FileNotFoundError(f"SoundFont not found: {soundfont_path}")

        self._soundfont_path = soundfont_path
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

        if sys.platform == "win32":
            raise NotImplementedError(
                "to_wav() is only available on Linux/macOS.")

        if output_path is None:
            output_path = os.path.splitext(self.file_path)[0] + ".wav"

        logger.info(f"Rendering MIDI → WAV: {self.file_path} → {output_path}")

        fs = self._fs.Synth()
        fs.setting("audio.driver", "file")
        fs.setting("audio.file.name", output_path)
        fs.setting("audio.file.type", "wav")
        fs.setting("synth.lock-memory", 0)
        fs.sfload(self._soundfont_path)
        fs.midi2audio(self.file_path, output_path)
        fs.delete()

        logger.info(f"WAV written to: {output_path}")
        return output_path

    def __repr__(self):
        return f"MIDIPlayer(file_path={self.file_path!r}, stop_flag={self.stop_flag})"
