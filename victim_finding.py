import cv2
import numpy as np
import time
import threading
import queue
import cv2.aruco as aruco
from djitellopy import Tello

# ---------- USER SETTINGS ----------
SCAN_WIDTH_CM = 190       # width of map area
SCAN_HEIGHT_CM = 80       # height of map area
SCAN_STEP_CM = 28         # sideways distance between scan stripes
FLYING_UP_CM = 20         # takeoff climb height

CENTER_DEADBAND = 150      # px tolerance for "centered"
CENTER_LOCK_FR = 12       # how many frames in-a-row we consider centered


# ArUco victim tag settings
VICTIM_ID = 8
HOME_ID = 11
ARUCO_DICT = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
ARUCO_PARAMS = aruco.DetectorParameters()

# 8x8 X-shape pattern: 'p' = pixel on, '0' = off
X_SHAPE = [
    "p000000p",
    "0p0000p0",
    "00p00p00",
    "000pp000",
    "000pp000",
    "00p00p00",
    "0p0000p0",
    "p000000p",
]

DEBUG = False

# -----------------------------------


def log(msg):
    if DEBUG:
        print(f"[LOG] {msg}")


class CommandWorker:
    """
    Background thread for blocking Tello SDK commands (takeoff, move_forward, etc.).
    This keeps the main thread free for video processing.
    """

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


def emergency_check(drone):
    """Global ESC emergency handler (from OpenCV window)."""
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        print("[EMERGENCY] ESC pressed → landing!")
        try:
            drone.send_rc_control(0, 0, 0, 0)
            drone.land()
        except:
            pass
        cv2.destroyAllWindows()
        raise SystemExit


'''def center_over_tag(drone, cx, cy, W, H):
    ex = cx - W // 2
    ey = cy - H // 2

    k = 0.04
    lr = int(np.clip(k * ex, -7, 7))  # left/right
    fb = int(np.clip(k * ey, -7, 7))  # forward/back
    fb = -fb  # flip, depending on your camera orientation

    if abs(ex) < (CENTER_DEADBAND + 20) and abs(ey) < (CENTER_DEADBAND + 20):
        drone.send_rc_control(0, 0, 0, 0)
        return True
    else:
        print(f"Not enough in the center to land")

    drone.send_rc_control(lr, fb, 0, 0)
    # tiny pause so we don't spam commands too fast
    time.sleep(0.03)
    return False
'''

def detect_tag(frame_small, target_id):
    corners, ids, _ = aruco.detectMarkers(
        frame_small, ARUCO_DICT, parameters=ARUCO_PARAMS)
    if ids is None:
        return None, None

    for i, found_id in enumerate(ids.flatten()):
        if found_id == target_id:
            pts = corners[i][0]
            cx = int(pts[:, 0].mean())
            cy = int(pts[:, 1].mean())
            return cx, cy

    return None, None

# Display pattern on Tello's LED matrix for 2 sec
def pattern_on_led_matrix(tello, shape):
    assert len(shape) == 8 and all(len(r) == 8 for r in shape), "Need 8x8"
    pattern = "".join(shape)
    color = "g"  # green
    cmd = f"mled {color} {pattern}"
    tello.send_expansion_command(cmd)


def main():
    drone = Tello()
    print("[INFO] Connecting to drone...")
    drone.connect()
    print("[INFO] Battery:", drone.get_battery(), "%")

    drone.streamon()
    frame_reader = drone.get_frame_read()
    time.sleep(1)

    # Background worker for blocking SDK commands
    worker = CommandWorker(drone)

    # ---- PREPARE HIGH-LEVEL FLIGHT PLAN (scan) ----
    # These commands will run in order in the background while the main loop stays responsive.
    worker.submit(drone.takeoff)

    # Build lawnmower scan pattern
    num_stripes = max(1, int(np.ceil(SCAN_WIDTH_CM / SCAN_STEP_CM)))
    stripe_len = SCAN_HEIGHT_CM
    forward = True

    for i in range(num_stripes):
        if forward:
            worker.submit(drone.move_forward, stripe_len // 2)
            worker.submit(drone.move_forward, stripe_len // 2)
        else:
            worker.submit(drone.move_back, stripe_len // 2)
            worker.submit(drone.move_back, stripe_len // 2)
        forward = not forward

        if i < num_stripes - 1:
            worker.submit(drone.move_right, SCAN_STEP_CM)

    # Return to left after scanning
    worker.submit(drone.move_left, SCAN_STEP_CM * (num_stripes - 1))
    # Optionally: come back along height if ended "far"
    if not forward:
        worker.submit(drone.move_back, stripe_len)

    # After scan+return finished, we'll start homing in the main loop
    state = "scan"   # "scan" -> "victim_hover" -> "homing"
    lock_frames = 0
    running = True

    victim_reported = False

    try:
        while running:
            # --- Read latest frame (non-blocking) ---
            frame = frame_reader.frame
            if frame is None:
                continue

            # Flip for mirror setup
            frame = cv2.flip(frame, 0)

            # debug:
            frame_debug = frame.copy()
            c, ids, _ = aruco.detectMarkers(
                frame_debug, ARUCO_DICT, parameters=ARUCO_PARAMS)
            if ids is not None:
                aruco.drawDetectedMarkers(frame_debug, c, ids)
            cv2.imshow("Tello View", frame_debug)

            # Show what the drone sees
            # cv2.imshow("Tello View", frame)

            # Global emergency key
            emergency_check(drone)

            # ---- STATE MACHINE ----
            if state == "scan":
                frame_small = cv2.resize(frame, (480, 360))
                vx, vy = detect_tag(frame_small, VICTIM_ID)

                if vx is not None:
                    # compute center offset
                    Hs, Ws = frame_small.shape[:2]
                    ex = vx - Ws//2
                    ey = vy - Hs//2
                    print("Not enough in the center")

                    if (abs(ex) < CENTER_DEADBAND and abs(ey) < CENTER_DEADBAND) and not victim_reported:
                        print("Victim properly centered → stop scan")
                        victim_reported = True
                        worker.clear()

                # 2) Decide what to do when movement commands are finished
                if worker.is_idle():
                    drone.send_rc_control(0, 0, 0, 0)
                    if victim_reported:
                        print("[INFO] Scan stopped at victim → VICTIM_HOVER")
                        state = "victim_hover"
                    else:
                        print("[INFO] Scan finished, no victim → HOMING")
                        state = "homing"

            elif state == "victim_hover":
                # 1) Show X on matrix
                pattern_on_led_matrix(drone, X_SHAPE)

                # 2) Hover for ~2 seconds, keeping ESC responsive
                hover_start = time.time()
                while time.time() - hover_start < 2.0:
                    drone.send_rc_control(0, 0, 0, 0)
                    emergency_check(drone)
                    time.sleep(0.05)

                # 3) CLEAR LED + RESET MOTION
                # drone.send_expansion_command("mled g " + "0"*64)
                drone.send_expansion_command("mled g 0")
                print("[INFO] Finished victim hover → RETURN_PATH")
                state = "homing"

            elif state == "homing":
                print("[INFO] Executing return path now...")

                # Stop worker thread fully
                worker.clear()
                worker.stop()
                time.sleep(0.2)   # small delay to avoid race condition

                drone.send_rc_control(0, 0, 0, 0)
                time.sleep(0.2)

                try:
                    drone.move_left((SCAN_STEP_CM * (num_stripes - 1)) // 2)
                    time.sleep(0.2)
                    drone.move_back(stripe_len)
                    drone.land()

                except Exception as e:
                    print("[ERROR] during return:", e)
                    try:
                        drone.land()
                    except:
                        pass

                # End program
                running = False
                break

            time.sleep(0.01)

    except SystemExit:
        # From emergency_check
        pass
    except Exception as e:
        print("[ERROR] Main loop:", e)
        try:
            drone.send_rc_control(0, 0, 0, 0)
            drone.land()
        except:
            pass
    finally:
        worker.stop()
        cv2.destroyAllWindows()
        drone.streamoff()
        print("[INFO] Shutdown complete")


if __name__ == "__main__":
    main()
