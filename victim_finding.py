import cv2
import numpy as np
import time
import threading
import queue
import cv2.aruco as aruco
from djitellopy import Tello

# ---------- USER SETTINGS ----------
SCAN_WIDTH_CM = 190       # width of map area
SCAN_HEIGHT_CM = 50       # height of map area
SCAN_STEP_CM = 28         # sideways distance between scan stripes
FLYING_UP_CM = 30         # takeoff climb height

CENTER_DEADBAND = 50      # px tolerance for "centered"
CENTER_LOCK_FR = 12       # how many frames in-a-row we consider centered

# Launching and landing pad color (cyan in Tello image), HSV
PAD_LOWER = (80, 200, 80)
PAD_UPPER = (110, 255, 255)

AREA_LOCK = 4000          # if pad contour area > this → close enough to land

VICTIM_ID = 7
ARUCO_DICT = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
ARUCO_PARAMS = aruco.DetectorParameters()

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


def find_pad_centroid(frame_small):
    """
    Detect pad in a small frame (e.g., 320x240).
    Returns (cx, cy, area) in that SMALL frame's coordinates.
    """
    hsv = cv2.cvtColor(frame_small, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, PAD_LOWER, PAD_UPPER)
    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=2)

    cnts, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, None, 0

    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area < 300:
        return None, None, 0

    M = cv2.moments(c)
    if M["m00"] == 0:
        return None, None, 0
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return cx, cy, area


def center_over_target_rc(drone, cx, cy, W, H):
    """
    Use RC control (non-blocking) to gently nudge the drone so that the pad
    moves towards the image center.
    Uses coordinates from a *small* frame (e.g., 320x240).
    """
    ex = cx - W // 2
    ey = cy - H // 2

    k = 0.04
    lr = int(np.clip(k * ex, -7, 7))  # left/right
    fb = int(np.clip(k * ey, -7, 7))  # forward/back
    fb = -fb  # flip, depending on your camera orientation

    if abs(ex) < CENTER_DEADBAND and abs(ey) < CENTER_DEADBAND:
        drone.send_rc_control(0, 0, 0, 0)
        return True

    drone.send_rc_control(lr, fb, 0, 0)
    # tiny pause so we don't spam commands too fast
    time.sleep(0.03)
    return False


def detect_victim_tag(frame_small):
    """
    Detect ArUco victim tag in a small frame.
    Returns (cx, cy) of the tag center if found, else (None, None).
    """
    corners, ids, _ = aruco.detectMarkers(
        frame_small, ARUCO_DICT, parameters=ARUCO_PARAMS)

    if ids is None:
        return None, None

    # ids is an array of shape (N,1)
    for i, marker_id in enumerate(ids.flatten()):
        if marker_id == VICTIM_ID:
            # corners[i] is 4x1x2 or 1x4x2 depending on version; use first dimension
            # 4 points: top-left, top-right, bottom-right, bottom-left
            pts = corners[i][0]
            cx = int(pts[:, 0].mean())
            cy = int(pts[:, 1].mean())
            return cx, cy

    return None, None



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
    worker.submit(drone.move_up, FLYING_UP_CM)
    worker.submit(drone.move_forward, 10)  # get onto the map

    # Build lawnmower scan pattern
    num_stripes = max(1, int(np.ceil(SCAN_WIDTH_CM / SCAN_STEP_CM)))
    stripe_len = SCAN_HEIGHT_CM
    forward = True

    for i in range(num_stripes):
        if forward:
            worker.submit(drone.move_forward, stripe_len)
        else:
            worker.submit(drone.move_back, stripe_len)
        forward = not forward

        if i < num_stripes - 1:
            worker.submit(drone.move_right, SCAN_STEP_CM)

    # Return to left after scanning
    worker.submit(drone.move_left, SCAN_STEP_CM * (num_stripes - 1))
    # Optionally: come back along height if ended "far"
    if not forward:
        worker.submit(drone.move_back, stripe_len)

    # After scan+return finished, we'll start homing in the main loop
    state = "scan"   # or "homing" later
    lock_frames = 0
    running = True
    victim_found = False
    victim_reported = False

    try:
        while running:
            # --- Read latest frame (non-blocking) ---
            frame = frame_reader.frame
            if frame is None:
                continue

            # Flip for mirror setup
            frame = cv2.flip(frame, 0)

            # Show what the drone sees
            cv2.imshow("Tello View", frame)

            # Global emergency key
            emergency_check(drone)

            # ---- STATE MACHINE ----
            if state == "scan":
                # process smaller frame for victim detection (cheap)
                frame_small = cv2.resize(frame, (320, 240))
                vx, vy = detect_victim_tag(frame_small)

                if vx is not None and not victim_reported:
                    print("Found victim!")
                    victim_found = True
                    victim_reported = True
                    # TODO: here you could also log the approximate cell later

                # Wait until the worker has completed all scan commands
                if worker.is_idle():
                    print("[INFO] Scan finished → switching to HOMING")
                    state = "homing"
                    # make sure drone isn't still moving from last RC
                    drone.send_rc_control(0, 0, 0, 0)
                # no vision processing here to keep it fast

            elif state == "homing":
                # Process a smaller version of the frame for pad detection
                frame_small = cv2.resize(frame, (320, 240))
                cx, cy, area = find_pad_centroid(frame_small)

                if cx is None:
                    # Pad not visible → slowly rotate in place to search
                    drone.send_rc_control(0, 0, 0, 8)
                    lock_frames = 0
                else:
                    # If the pad is big enough → land directly
                    if area > AREA_LOCK:
                        print("[INFO] Pad big in view → LANDING")
                        drone.send_rc_control(0, 0, 0, 0)
                        drone.land()
                        running = False
                        break

                    # Otherwise gently center over it
                    Hs, Ws = frame_small.shape[:2]
                    centered = center_over_target_rc(drone, cx, cy, Ws, Hs)
                    if centered:
                        lock_frames += 1
                        print("[INFO] Centered frames:", lock_frames)
                    else:
                        lock_frames = 0

                    # If it's been centered for long enough → land as well
                    if lock_frames > CENTER_LOCK_FR:
                        print("[INFO] Pad centered for a while → LANDING")
                        drone.send_rc_control(0, 0, 0, 0)
                        drone.land()
                        running = False
                        break

            # small sleep to avoid burning 100% CPU
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
