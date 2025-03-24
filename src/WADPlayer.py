import ctypes
import time
import threading
from loguru import logger

"""
Small MIDI player for Windows using winmm.dll
Example usage:
    player = MIDIPlayer("path/to/your/file.mid")
    player.play()
    time.sleep(10)  
    player.stop()
    
"""


class MIDIPlayer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.stop_flag = False

        try:
            winmm = ctypes.WinDLL("winmm.dll")
            self.mciSendString = winmm.mciSendStringW
        except AttributeError:
            raise ImportError("winmm.dll not found. This player only works on Windows.")

    def __repr__(self):
        return f"MIDIPlayer(file_path={self.file_path}, stop_flag={self.stop_flag})."

    def mci_send(self, command):
        buffer = ctypes.create_unicode_buffer(256)
        self.mciSendString(command, buffer, 256, 0)
        return buffer.value

    def play_midi(self):
        logger.info(f"Playing MIDI file: {self.file_path}")

        self.stop_flag = False
        self.mci_send(f'open "{self.file_path}" type sequencer alias midi')
        self.mci_send("play midi")

        # Wait until playback finishes or stop is requested
        while self.mci_send("status midi mode") == "playing":
            if self.stop_flag:
                logger.info("Stopped by user")
                self.stop_midi()
                break

        # Stop normally if not interrupted
        if not self.stop_flag:
            logger.info("Stopped at the end")
            self.stop_midi()

    def stop_midi(self):
        logger.info("Stopping MIDI playback")
        self.stop_flag = True
        # Stop the currently playing MIDI
        self.mci_send("stop midi")
        time.sleep(0.1)  # Small delay to ensure stop completes
        self.mci_send("close midi")
        time.sleep(0.1)  # Delay to allow reset of alias
        self.mci_send("reset midi")  # Reset MIDI alias to avoid conflicts

    # Start playing MIDI in a separate thread
    def play(self, loop_flag=False):
        self.loop_flag = loop_flag
        threading.Thread(target=self.play_midi, daemon=True).start()

    # Stop playback
    def stop(self):
        self.stop_flag = True
