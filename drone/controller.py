from djitellopy import Tello
import threading, queue, time
from .patterns import PATTERNS

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
        self.q.put((func, args))

    def is_idle(self):
        return self.q.empty() and not self.active

    def stop(self):
        self.running = False
        try:
            self.thread.join(timeout=1)
        except:
            pass

class DroneController:
    def __init__(self):
        self.drone = Tello()
        print("[INFO] Connecting to drone...")
        self.worker = CommandWorker(self.drone)

    def connect_and_start(self):
        self.drone.connect()
        print("[INFO] Battery:", self.drone.get_battery())
        self.drone.streamon()

    def get_frame(self):
        frame_reader = self.drone.get_frame_read().frame
        time.sleep(1)
        return frame_reader

    def show_pattern(self, pattern_name):
        pattern = PATTERNS.get(pattern_name)
        if pattern:
            # TODO: LED-Matrix Befehl senden
            cmd = f"mled g {''.join(pattern)}"
            self.drone.send_expansion_command(cmd)
