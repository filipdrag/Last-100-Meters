from djitellopy import Tello
import threading, queue, time
from .patterns import PATTERNS, LETTERS
from typing import Optional, Dict, List, Tuple

class CommandWorker:
    def __init__(self, drone: Tello):
        self.drone = drone
        self.q = queue.Queue()
        self.running = True
        self.active = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                func, args = self.q.get(timeout=0.1)
            except queue.Empty:
                continue
            self.active = True
            try:
                func(*args)
            except Exception as e:
                print("[CMD ERROR]", e)
            self.active = False
            self.q.task_done()

    def submit(self, func, *args):
        """Queue a blocking drone command (e.g. drone.move_forward, drone.move_up)."""
        self.q.put((func, args))

    def is_idle(self):
        """True if no more commands are queued or running."""
        return self.q.empty() and not self.active

    def stop(self):
        self.running = False
        try:
            self.thread.join(timeout=1)
        except:
            pass
    
    def clear(self):
        """Remove all pending commands from the queue."""
        while True:
            try:
                func, args = self.q.get_nowait()
                self.q.task_done()
            except queue.Empty:
                break
    
    def wait_until_idle(self):
        while not self.is_idle():
            time.sleep(0.05)
        print("is idle")


class DroneController:
    def __init__(self):
        self.drone = Tello()
        print("[INFO] Connecting to drone...")
        self.worker = CommandWorker(self.drone)

    def connect_and_start(self):
        self.drone.connect()
        print("[INFO] Battery:", self.drone.get_battery())
        self.drone.streamon()


    #returning a frame from the drone
    def get_frame(self):
        return self.frame_reader.frame

    #show a sign on the LED-Matrix
    def show_pattern(self, pattern_name):
        pattern = PATTERNS.get(pattern_name)
        if pattern:
            
            cmd = f"mled g {''.join(pattern)}"
            try:
                self.drone.send_expansion_command(cmd)
            except Exception as e:
                print("[ERROR] sending pattern: ", e)

    #clear LED-display
    def clear_led(self, color: str = "g") -> None:
        self.drone.send_expansion_command(f"mled {color} " + "0" * 64)

    """
    moving text displayed on LED-Matrix
    """
    def build_cols_for_text(self, text: str) -> List[List[str]]:
        cols: List[List[str]] = []
        for ch in text:
            glyph = LETTERS.get(ch, LETTERS[" "])
            for x in range(8):
                col = [glyph[y][x] for y in range(8)]
                cols.append(col)
            cols.append(["0"] * 8)  # spacing

        pad = [["0"] * 8] * 8
        return pad + cols + pad


    def frame_from_cols(self, cols: List[List[str]], start: int) -> List[str]:
        window = cols[start: start + 8]
        rows = ["".join(window[x][y] for x in range(8)) for y in range(8)]
        return rows


    def rows_to_payload(self, rows: List[str]) -> str:
        flat = "".join(rows)
        assert len(rows) == 8 and all(len(r) == 8 for r in rows)
        assert set(flat) <= {"p", "0"}
        return flat


    def show_moving_text_once(self, text: str, color: str = "g", speed: float = 0.10) -> None:
        cols = self.build_cols_for_text(text)
        total = len(cols)
        for offset in range(0, max(1, total - 7)):
            rows = self.frame_from_cols(cols, offset)
            payload = self.rows_to_payload(rows)
            try: 
                self.drone.send_expansion_command(f"mled {color} {payload}")
                time.sleep(max(speed, 0.15))
            except Exception as e:
                print("[ERROR] sending moving text: ", e)