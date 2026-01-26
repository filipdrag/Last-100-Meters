# -----------------------------
# Cross-platform Voice (Laptop)
# -----------------------------
import platform
import subprocess


class Voice:
    """
    Cross-platform TTS that works while OpenCV windows are open.

    macOS: uses `say`
    Windows: uses PowerShell System.Speech
    """

    def __init__(self, rate: int = 175):
        self.system = platform.system().lower()
        self.rate = rate
        if "windows" in self.system:
            # Approx mapping WPM-ish -> SpeechSynthesizer.Rate [-10..10]
            self.win_rate = max(-10, min(10, int((rate - 175) / 15)))

    def say(self, text: str) -> None:
        print(f"[VOICE] {text}")

        if "darwin" in self.system or "mac" in self.system:
            subprocess.run(["say", "-r", str(self.rate), text], check=False)
        elif "windows" in self.system:
            safe = text.replace('"', r'\"')
            ps_cmd = (
                "Add-Type -AssemblyName System.Speech; "
                "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$speak.Rate = {self.win_rate}; "
                f'$speak.Speak("{safe}");'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            subprocess.run(["espeak", text], check=False)
