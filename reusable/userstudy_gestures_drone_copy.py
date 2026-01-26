"""
userstudy_gestures_tello.py

Human-Drone Interaction mock (Emergency Q/A) with:
- Video input: Tello camera stream (NOT laptop webcam)
- Gesture input: thumbs-up = YES, thumbs-down = NO (MediaPipe Hands)
- Voice output: played on the laptop (cross-platform OS TTS: macOS `say`, Windows PowerShell)
- Drone LED matrix:
    * While speaking the question: QUESTION MARK
    * While waiting for answer: DOTS
    * After recognition: moving "YES" or "NO"
- End: prints all answers to terminal

Controls:
- ESC in the video window: abort (lands if flying)
- r in the video window: restart flow

Dependencies:
  pip install djitellopy opencv-python mediapipe numpy

Notes:
- LED matrix commands require the Tello with expansion module that supports `mled ...`
- Best gesture recognition when the hand is clearly visible and not too small in the frame.
"""

import time
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple

import cv2
import numpy as np
import mediapipe as mp

from djitellopy import Tello


# -----------------------------
# Thermal safety helper
# -----------------------------
def thermal_idle_big(tello: Tello, seconds: float = 0.25):
    """
    Short motor idle pulse to cool ESC, CPU and WiFi.
    Call this regularly during long vision/LED/voice phases.
    """
    tello.send_rc_control(0, 0, 0, 0)
    time.sleep(seconds)

def thermal_idle_micro(tello, dt=0.02):
    """
    Super short motor idle pulse to cool ESC, CPU and WiFi.
    Call this in realtime-loops.
    """
    tello.send_rc_control(0,0,0,0)
    time.sleep(dt)

# -----------------------------
# Cross-platform Voice (Laptop)
# -----------------------------
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


# -----------------------------
# Drone LED patterns / helpers
# -----------------------------
PATTERNS = {
    "CROSS": [
        "000pp000",
        "000pp000",
        "000pp000",
        "pppppppp",
        "pppppppp",
        "000pp000",
        "000pp000",
        "000pp000",
    ],
    "QUESTION_MARK": [
        "00000000",
        "000pp000",
        "00p00p00",
        "0000p000",
        "000p0000",
        "000p0000",
        "00000000",
        "000p0000",
    ],
    "DOTS": [
        "00000000",
        "00000000",
        "00000000",
        "00000000",
        "00000000",
        "00p0p0p0",
        "00000000",
        "00000000",
    ],
}

LETTERS = {
    " ": [
        "00000000",
        "00000000",
        "00000000",
        "00000000",
        "00000000",
        "00000000",
        "00000000",
        "00000000",
    ],
    "Y": [
        "pp0000pp",
        "pp0000pp",
        "0pppppp0",
        "00pppp00",
        "000pp000",
        "000pp000",
        "000pp000",
        "000pp000",
    ],
    "E": [
        "pppppppp",
        "pp000000",
        "pp000000",
        "pppppp00",
        "pp000000",
        "pp000000",
        "pppppppp",
        "00000000",
    ],
    "S": [
        "0pppppp0",
        "pp000000",
        "pp000000",
        "0pppppp0",
        "000000pp",
        "000000pp",
        "0pppppp0",
        "00000000",
    ],
    "N": [
        "pp0000pp",
        "ppp000pp",
        "pp0p00pp",
        "pp00p0pp",
        "pp000ppp",
        "pp0000pp",
        "pp0000pp",
        "pp0000pp",
    ],
    "O": [
        "0pppppp0",
        "pp0000pp",
        "pp0000pp",
        "pp0000pp",
        "pp0000pp",
        "pp0000pp",
        "0pppppp0",
        "00000000",
    ],
}


def bitmap_to_pattern(rows: List[str]) -> str:
    return "".join(rows)


def show_pattern(tello: Tello, rows: List[str], color: str = "g") -> None:
    pattern = bitmap_to_pattern(rows)
    tello.send_expansion_command(f"mled {color} {pattern}")


def clear_led(tello: Tello, color: str = "g") -> None:
    tello.send_expansion_command(f"mled {color} " + "0" * 64)


def build_cols_for_text(text: str) -> List[List[str]]:
    cols: List[List[str]] = []
    for ch in text:
        glyph = LETTERS.get(ch, LETTERS[" "])
        for x in range(8):
            col = [glyph[y][x] for y in range(8)]
            cols.append(col)
        cols.append(["0"] * 8)  # spacing

    pad = [["0"] * 8] * 8
    return pad + cols + pad


def frame_from_cols(cols: List[List[str]], start: int) -> List[str]:
    window = cols[start: start + 8]
    rows = ["".join(window[x][y] for x in range(8)) for y in range(8)]
    return rows


def rows_to_payload(rows: List[str]) -> str:
    flat = "".join(rows)
    assert len(rows) == 8 and all(len(r) == 8 for r in rows)
    assert set(flat) <= {"p", "0"}
    return flat


def show_moving_text_once(tello: Tello, text: str, color: str = "g", speed: float = 0.10) -> None:
    cols = build_cols_for_text(text)
    total = len(cols)
    for offset in range(0, max(1, total - 7)):
        rows = frame_from_cols(cols, offset)
        payload = rows_to_payload(rows)
        tello.send_expansion_command(f"mled {color} {payload}")
        time.sleep(max(speed, 0.15))


# -----------------------------
# Flow definitions
# -----------------------------
@dataclass
class Question:
    key: str
    voice_text: str


class RestartFlow(Exception):
    pass


# -----------------------------
# Tello camera + MediaPipe thumbs recognizer
# -----------------------------
class TelloThumbsRecognizerMP:
    """
    Uses the Tello video stream as input instead of laptop webcam.
    MediaPipe Hands for landmarks + same neutral gating logic you tested.
    """

    def __init__(self, tello: Tello, window_name: str = "Tello Gesture Input (ESC abort, r restart)"):
        self.tello = tello
        self.window_name = window_name

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.mp_draw = mp.solutions.drawing_utils

        # Start stream and keep a frame reader
        #self.tello.streamon()
        self.frame_read = None
        
        self.vision_enabled = False

    def close(self) -> None:
        try:
            self.hands.close()
        except Exception:
            pass
        try:
            self.tello.streamoff()
        except Exception:
            pass
        cv2.destroyAllWindows()

    @staticmethod
    def _lm_xy(lms, idx: int, w: int, h: int) -> np.ndarray:
        return np.array([lms[idx].x * w, lms[idx].y * h], dtype=np.float32)

    @staticmethod
    def _is_finger_extended(lms, tip: int, pip: int, w: int, h: int) -> bool:
        tip_xy = np.array([lms[tip].x * w, lms[tip].y * h])
        pip_xy = np.array([lms[pip].x * w, lms[pip].y * h])
        return tip_xy[1] < pip_xy[1] - 10

    def classify_thumb(self, lms, w: int, h: int) -> Tuple[Optional[bool], str]:
        WRIST = 0
        THUMB_MCP = 2
        THUMB_TIP = 4

        INDEX_PIP, INDEX_TIP = 6, 8
        MIDDLE_PIP, MIDDLE_TIP = 10, 12
        RING_PIP, RING_TIP = 14, 16
        PINKY_PIP, PINKY_TIP = 18, 20

        wrist = self._lm_xy(lms, WRIST, w, h)
        thumb_mcp = self._lm_xy(lms, THUMB_MCP, w, h)
        thumb_tip = self._lm_xy(lms, THUMB_TIP, w, h)

        idx_ext = self._is_finger_extended(lms, INDEX_TIP, INDEX_PIP, w, h)
        mid_ext = self._is_finger_extended(lms, MIDDLE_TIP, MIDDLE_PIP, w, h)
        ring_ext = self._is_finger_extended(lms, RING_TIP, RING_PIP, w, h)
        pink_ext = self._is_finger_extended(lms, PINKY_TIP, PINKY_PIP, w, h)

        other_extended = sum([idx_ext, mid_ext, ring_ext, pink_ext])
        if other_extended >= 2:
            return None, f"Other fingers extended ({other_extended}) -> ignore"

        v = thumb_tip - thumb_mcp
        v_norm = np.linalg.norm(v) + 1e-6
        v_unit = v / v_norm

        if v_unit[1] < -0.45:
            return True, f"Thumb vector up (vy={v_unit[1]:.2f}) -> THUMBS UP"
        if v_unit[1] > 0.45:
            return False, f"Thumb vector down (vy={v_unit[1]:.2f}) -> THUMBS DOWN"

        if thumb_tip[1] < wrist[1] - 30:
            return True, "Fallback: thumb tip above wrist -> THUMBS UP"
        if thumb_tip[1] > wrist[1] + 30:
            return False, "Fallback: thumb tip below wrist -> THUMBS DOWN"

        return None, f"Unclear thumb direction (vy={v_unit[1]:.2f})"

    def _get_frame(self) -> np.ndarray:
        
        if not self.vision_enabled:
            if self.frame_read:
                self.tello.streamoff()
                self.frame_read = None
            time.sleep(0.05)
            return np.zeros((120, 160, 3), dtype=np.uint8)
        
        if self.frame_read is None:
            self.tello.streamon()
            self.frame_read = self.tello.get_frame_read()
            time.sleep(0.3)
        
        frame = self.frame_read.frame
        if frame is None:
            return np.zeros((120, 160, 3), dtype=np.uint8)
        # Tello often provides BGR already; if colors look wrong, you can swap channels.
        return cv2.resize(frame, (160, 120))

    def _handle_keys(self) -> Optional[str]:
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            return "esc"
        if key == ord("r"):
            return "restart"
        return None

    def wait_for_neutral(
        self,
        *,
        neutral_seconds: float = 0.6,
        timeout_s: float = 8.0,
        hint: str = "(Reset) Please release gesture to neutral...",
    ) -> bool:
        self.vision_enabled = True
        t0 = time.time()
        neutral_start = None
        last_debug = ""

        while True:
            frame = self._get_frame()
            frame = cv2.flip(frame, 1)  # mirror for participant
            h, w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.hands.process(rgb)

            value = None
            if res.multi_hand_landmarks:
                lms = res.multi_hand_landmarks[0].landmark
                value, last_debug = self.classify_thumb(lms, w, h)
                self.mp_draw.draw_landmarks(
                    frame, res.multi_hand_landmarks[0], self.mp_hands.HAND_CONNECTIONS)
            else:
                value = None
                last_debug = "No hand detected"

            is_neutral = (value is None)

            if is_neutral:
                if neutral_start is None:
                    neutral_start = time.time()
                elif (time.time() - neutral_start) >= neutral_seconds:
                    self.vision_enabled = False
                    return True
            else:
                neutral_start = None

            cv2.putText(frame, hint, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
            cv2.putText(frame, f"Debug: {last_debug}", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            held = 0 if neutral_start is None else (
                time.time() - neutral_start)
            cv2.putText(frame, f"Neutral held: {held:.1f}/{neutral_seconds:.1f}s", (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

            cv2.imshow(self.window_name, frame)

            k = self._handle_keys()
            if k == "esc":
                self.vision_enabled = False
                return False
            if k == "restart":
                raise RestartFlow()

            if (time.time() - t0) > timeout_s:
                self.vision_enabled = False
                return False
            
            # thermal relief every loop
            thermal_idle_micro(self.tello)

    def wait_for_yes_no(
        self,
        question_text: str,
        *,
        stable_frames: int = 10,
        timeout_s: float = 20.0,
        post_speech_delay_s: float = 0.3,
        require_neutral_before: bool = True,
        neutral_seconds: float = 0.6,
    ) -> Optional[bool]:
        self.vision_enabled = True
        time.sleep(post_speech_delay_s)

        if require_neutral_before:
            ok = self.wait_for_neutral(
                neutral_seconds=neutral_seconds, timeout_s=8.0)
            if not ok:
                self.vision_enabled = False
                return None
            
            self.vision_enabled = True

        t0 = time.time()
        yes_count = 0
        no_count = 0
        last_debug = "No hand detected"

        while True:
            frame = self._get_frame()
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.hands.process(rgb)

            value = None
            if res.multi_hand_landmarks:
                lms = res.multi_hand_landmarks[0].landmark
                value, last_debug = self.classify_thumb(lms, w, h)
                self.mp_draw.draw_landmarks(
                    frame, res.multi_hand_landmarks[0], self.mp_hands.HAND_CONNECTIONS)
            else:
                value = None
                last_debug = "No hand detected"

            if value is True:
                yes_count += 1
                no_count = max(0, no_count - 1)
            elif value is False:
                no_count += 1
                yes_count = max(0, yes_count - 1)
            else:
                yes_count = max(0, yes_count - 1)
                no_count = max(0, no_count - 1)

            cv2.putText(frame, question_text, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
            cv2.putText(frame, f"Debug: {last_debug}", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(frame, f"YES stable: {yes_count}/{stable_frames}", (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(frame, f"NO stable:  {no_count}/{stable_frames}", (20, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(frame, "Now answer: thumbs-up (YES) or thumbs-down (NO)", (20, 190),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

            cv2.imshow(self.window_name, frame)

            k = self._handle_keys()
            if k == "esc":
                return None
            if k == "restart":
                raise RestartFlow()

            if yes_count >= stable_frames:
                self.vision_enabled = False
                return True
            if no_count >= stable_frames:
                self.vision_enabled = False
                return False

            if (time.time() - t0) > timeout_s:
                self.vision_enabled = False
                return None
            
            # thermal relief every loop
            thermal_idle_micro(self.tello)


# -----------------------------
# Ask question with LEDs + voice + gesture
# -----------------------------
def ask_yes_no(
    tello: Tello,
    voice: Voice,
    recognizer: TelloThumbsRecognizerMP,
    q: Question,
    answers: Dict[str, Optional[bool]],
    *,
    wait_timeout_s: float = 25.0,
) -> Optional[bool]:
    #cool down drone
    thermal_idle_big(tello)
    
    # Show question mark while speaking
    show_pattern(tello, PATTERNS["QUESTION_MARK"], color="g")
    voice.say(q.voice_text)

    # Show dots while waiting for answer
    show_pattern(tello, PATTERNS["DOTS"], color="g")
    result = recognizer.wait_for_yes_no(
        question_text=q.voice_text,
        stable_frames=10,
        timeout_s=wait_timeout_s,
        post_speech_delay_s=0.2,
        require_neutral_before=True,
        neutral_seconds=0.6,
    )
    answers[q.key] = result

    # Show "YES"/"NO" as moving text after recognition
    if result is True:
        show_moving_text_once(tello, "YES", color="g", speed=0.08)
    elif result is False:
        show_moving_text_once(tello, "NO", color="g", speed=0.08)
    else:
        # Timeout/abort: briefly show question mark
        show_pattern(tello, PATTERNS["QUESTION_MARK"], color="g")
        time.sleep(1.0)

    clear_led(tello, "g")
    
    #cool down drone
    thermal_idle_big(tello)
    return result


def print_answers(answers: Dict[str, Optional[bool]]) -> None:
    print("\n==============================")
    print("Participant answers (thumbs-up=yes / thumbs-down=no):")
    for k, v in answers.items():
        if v is True:
            s = "YES"
        elif v is False:
            s = "NO"
        else:
            s = "N/A (timeout / aborted / not asked)"
        print(f"- {k}: {s}")
    print("==============================\n")


# -----------------------------
# Full study flow
# -----------------------------
def run_flow(tello: Tello, voice: Voice, recognizer: TelloThumbsRecognizerMP) -> Dict[str, Optional[bool]]:
    answers: Dict[str, Optional[bool]] = {}

    # Optional: approach sequence (edit to your needs)
    show_pattern(tello, PATTERNS["CROSS"], color="g")
    voice.say(
        "We are from the ambulance service. For the following questions, answer by showing a thumbs up for yes, "
        "or thumbs down for no."
    )

    ask_yes_no(tello, voice, recognizer, Question(
        "can_hear_me", "Can you hear me?"), answers)

    ask_yes_no(
        tello, voice, recognizer,
        Question("caller_or_patient",
                 "Are you the person needing help or the person who called the ambulance?"),
        answers,
    )

    voice.say("Help is on its way.")

    changed = ask_yes_no(
        tello, voice, recognizer,
        Question("situation_changed",
                 "Did the medical situation get worse since the call?"),
        answers,
    )

    ask_yes_no(
        tello, voice, recognizer,
        Question("medical_actions",
                 "Are any medical actions currently being done?"),
        answers,
    )

    ask_yes_no(
        tello, voice, recognizer,
        Question("safe_position", "Is the patient in a safe and stable position?"),
        answers,
    )

    show_pattern(tello, PATTERNS["CROSS"], color="g")
    voice.say(
        "I am now heading back to guide the ambulance to you. Please stay here.")

    return answers


def main():
    tello = Tello()
    tello.connect()
    print("Battery:", tello.get_battery(), "%")

    voice = Voice(rate=175)
    recognizer = TelloThumbsRecognizerMP(tello)

    # If you want the drone to fly for the real study, set this True.
    # For safety while testing vision/LEDs, keep it False.
    DO_FLIGHT = True

    try:
        if DO_FLIGHT:
            print("[DRONE] Taking off...")
            tello.takeoff()
            time.sleep(1.0)
            # Example approach
            tello.move_up(50)
            thermal_idle_big(tello, 0.3)
            
            tello.move_forward(100)
            thermal_idle_big(tello, 0.3)
            

        while True:
            try:
                answers = run_flow(tello, voice, recognizer)
                print_answers(answers)
                break
            except RestartFlow:
                print("\n[RESTART] Restarting the full flow...\n")
                continue
            
            
        if DO_FLIGHT:
            print("[DRONE] 180° turn and flying away")
            tello.rotate_clockwise(180)
            time.sleep(2.0)

            tello.move_forward(100)
            time.sleep(2.0)
            
            tello.send_rc_control(0, 0, 0, 0)

            print("[DRONE] Landing...")
            tello.land()
            time.sleep(3.0)

    except KeyboardInterrupt:
        print("\n[ABORT] KeyboardInterrupt")

    finally:
        try:
            clear_led(tello, "g")
        except Exception:
            pass

        if DO_FLIGHT:
            try:
                print("[DRONE] Landing...")
                tello.land()
            except Exception:
                pass

        try:
            tello.end()
        except Exception:
            pass

        recognizer.close()


if __name__ == "__main__":
    main()
