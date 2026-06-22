import os
import sys
import shutil
import logging
import subprocess

from ..utils import any_type


logger = logging.getLogger("cid_node_pack")


class CidPlaySound:
    """Play a sound file asynchronously.

    - No outputs (side-effect only)
    - No mode widget; always eligible to run
    - Cross-platform best-effort using external players
      (prefers ffplay; falls back to paplay/sox on Linux; limited
      PowerShell/WAV fallback on Windows if ffplay is unavailable).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                # Optional trigger so the node can be chained anywhere
                "any": (any_type, {"tooltip": "Optional trigger input"}),
                "volume": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.01,
                        "tooltip": "Playback volume multiplier (implementation-dependent)",
                    },
                ),
                "sound_path": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Path to an audio file (.wav, .mp3, .ogg/.oga, etc.)",
                    },
                ),
            },
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/IO"

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        # No mode widget: behave like "always" so the node can fire each execution
        return float("NaN")

    # -------------------------------
    # Helpers
    # -------------------------------
    @staticmethod
    def _expand_user_env(path: str) -> str:
        if not path:
            return path
        return os.path.expandvars(os.path.expanduser(path))

    @staticmethod
    def _clamp(value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    def _build_play_command(self, file_path: str, volume: float) -> list | None:
        """Return a subprocess command list to play the file, or None if not possible.

        Preference order:
          1) ffplay (Windows/Linux/macOS) – supports many formats
          2) paplay (Linux, PulseAudio) – supports many formats
          3) sox/play (Linux/macOS) – supports many formats
          4) aplay (Linux, ALSA – WAV/PCM)
          5) PowerShell MediaPlayer fallback (Windows; limited format support)
        """

        # Prefer ffplay if available (most ComfyUI installs have ffmpeg/ffplay)
        ffplay = shutil.which("ffplay")
        if ffplay:
            # ffplay volume: 0..100 (integers); allow amplification up to 200%
            vol = int(round(self._clamp(volume, 0.0, 2.0) * 100))
            return [
                ffplay,
                "-nodisp",
                "-autoexit",
                "-loglevel",
                "quiet",
                "-volume",
                str(vol),
                file_path,
            ]

        # Linux-specific fallbacks
        if sys.platform.startswith("linux"):
            paplay = shutil.which("paplay")
            if paplay:
                # paplay volume: 0..65536 (integers); no amplification beyond 100%
                vol = int(round(self._clamp(volume, 0.0, 1.0) * 65536))
                return [paplay, f"--volume={vol}", file_path]

            sox_play = shutil.which("play")  # from sox
            if sox_play:
                # sox uses -v <amplitude multiplier>
                vol = str(self._clamp(volume, 0.0, 2.0))
                return [sox_play, "-q", "-v", vol, file_path]

            aplay = shutil.which("aplay")
            if aplay and file_path.lower().endswith(".wav"):
                return [aplay, "-q", file_path]

        # Windows fallback (if ffplay is missing)
        if os.name == "nt":
            powershell = shutil.which("powershell") or shutil.which("pwsh")
            if powershell and file_path.lower().endswith(".wav"):
                # WAV-only fallback using System.Media.SoundPlayer (non-blocking)
                # Volume control is not available here; ignore volume.
                ps_cmd = (
                    "Add-Type -AssemblyName System.Media;"
                    f"(New-Object System.Media.SoundPlayer '{file_path}').Play();"
                )
                return [powershell, "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd]

        return None

    def _start_process_detached(self, cmd: list) -> None:
        try:
            creationflags = 0
            startupinfo = None
            if os.name == "nt":
                # Detach on Windows to avoid locking the UI
                creationflags = (
                    getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                    | getattr(subprocess, "DETACHED_PROCESS", 0)
                )
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=(os.name != "nt"),
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
        except Exception as exc:
            logger.warning(f"CidPlaySound: Failed to start player: {exc}")

    # -------------------------------
    # Main
    # -------------------------------
    def main(self, any=None, volume=1.0, sound_path: str = ""):
        path = self._expand_user_env(sound_path).strip()
        if not path:
            logger.info("CidPlaySound: No 'sound_path' specified; nothing to play.")
            return {}

        # If a relative path is provided, try absolute based on CWD
        if not os.path.isabs(path):
            candidate = os.path.abspath(path)
        else:
            candidate = path

        if not os.path.exists(candidate):
            logger.warning(f"CidPlaySound: File not found: {candidate}")
            return {}

        cmd = self._build_play_command(candidate, float(volume))
        if not cmd:
            logger.error(
                "CidPlaySound: No suitable audio player found. Install 'ffplay' (ffmpeg) for best compatibility."
            )
            return {}

        self._start_process_detached(cmd)
        return {}


