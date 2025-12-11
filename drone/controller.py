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

class DroneController:
    def __init__(self):
        self.drone = Tello()
        print("[INFO] Connecting to drone...")
        self.worker = CommandWorker(self.drone)
        self.drone.connect()
        print("[INFO] Battery:", self.drone.get_battery())


        self.drone.streamon()
        self.frame_reader = self.drone.get_frame_read()
        time.sleep(1)


    '''def connect_and_start(self):
        self.drone.connect()
        print("[INFO] Battery:", self.drone.get_battery())
        self.drone.streamon()'''


    #returning a frame from the drone
    def get_frame(self):
        return self.frame_reader.frame

    #show a sign on the LED-Matrix
    def show_pattern(self, pattern_name):
        pattern = PATTERNS.get(pattern_name)
        if pattern:
            # TODO: LED-Matrix Befehl senden
            cmd = f"mled g {''.join(pattern)}"
            self.drone.send_expansion_command(cmd)
