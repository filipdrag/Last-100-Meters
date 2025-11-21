import cv2
import numpy as np
import time
from djitellopy import Tello

# ---------- USER SETTINGS ----------
SCAN_WIDTH_CM = 190
SCAN_HEIGHT_CM = 70
SCAN_STEP_CM = 28
FLYING_UP_CM = 30

CENTER_DEADBAND = 30
CENTER_LOCK_FR = 12


# Launching and langing pad color (blue/cyan in Tello image)
PAD_LOWER = (80, 100, 80)  # H, S, V
PAD_UPPER = (110, 255, 255)

# Landing size threshold
AREA_LOCK = 3000

DEBUG = False

# -----------------------------------


# Logging Helper, only prints if DEBUG=True
def log(msg):
    if DEBUG:
        print(f"[LOG] {msg}")

# If ESC is pressed, land drone immediately


def emergency_check(drone):
    """Global ESC emergency handler."""
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        log("EMERGENCY STOP: ESC PRESSED → LANDING!")
        try:
            drone.send_rc_control(0, 0, 0, 0)
            drone.land()
        except:
            pass
        cv2.destroyAllWindows()
        exit(0)


# Find yellow pad centroid in frame
def find_pad_centroid(frame):
    # Convert frame from BGR → HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, PAD_LOWER, PAD_UPPER)  # color segmentation
    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=3)

    cnts, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # find contours
    if not cnts:
        log("No yellow contour found")
        return None, None, 0

    c = max(cnts, key=cv2.contourArea)  # choose largest contour
    area = cv2.contourArea(c)

    if area < 300:
        log(f"Yellow contour too small: {area}")
        return None, None, 0

    M = cv2.moments(c)
    if M["m00"] == 0:
        log("Moment error (division by zero)")
        return None, None, 0

    cx = int(M["m10"]/M["m00"])
    cy = int(M["m01"]/M["m00"])
    log(f"Yellow centroid found at (cx={cx}, cy={cy}), area={area}")
    return cx, cy, area


# Center drone over target point (cx, cy) in frame
def center_over_target(drone, frame, cx, cy):
    H, W = frame.shape[:2]
    ex = cx - W//2
    ey = cy - H//2
    log(f"Centering error: ex={ex}, ey={ey}")

    k = 0.04
    lr = int(np.clip(k * ex, -7, 7))
    fb = int(np.clip(k * ey, -7, 7))
    fb = -fb  # flip forward/backward depending on camera orientation

    if abs(ex) < CENTER_DEADBAND and abs(ey) < CENTER_DEADBAND:
        log("Centered within deadband → sending rc (0,0,0,0)")
        drone.send_rc_control(0, 0, 0, 0)
        return True

    log(f"Sending rc control lr={lr}, fb={fb}")
    drone.send_rc_control(lr, fb, 0, 0)

    # tiny pause so it doesn't stack commands too aggressively
    time.sleep(0.05)

    return False


def safe_drone_command(drone, description, func, *args):
    log(f"Attempt: {description} with args={args}")
    try:
        func(*args)
        log(f"Success: {description}")
    except Exception as e:
        log(f"ERROR during '{description}': {e}")


def main():
    drone = Tello()
    log("Connecting to drone...")
    drone.connect()
    log(f"Battery: {drone.get_battery()}%")

    log("Turning on video stream...")
    drone.streamon()
    frame_reader = drone.get_frame_read()
    time.sleep(1)

    try:
        log("TAKEOFF sequence started.")
        safe_drone_command(drone, "takeoff", drone.takeoff)
        time.sleep(2)

        emergency_check(drone)

        log("Ascending to cruise altitude...")
        safe_drone_command(
            drone, f"move_up({FLYING_UP_CM})", drone.move_up, FLYING_UP_CM)
        time.sleep(1)

        emergency_check(drone)

        # ---- SCAN START ----
        log("Beginning scan pattern. Moving forward to map start...")
        safe_drone_command(drone, "move_forward(20)", drone.move_forward, 20)
        time.sleep(1)

        emergency_check(drone)

        # Lawnmower scan pattern
        num_stripes = max(1, int(np.ceil(SCAN_WIDTH_CM / SCAN_STEP_CM)))
        stripe_len = SCAN_HEIGHT_CM
        forward = True

        for i in range(num_stripes):

            # Display video during scanning
            raw = frame_reader.frame
            if raw is not None:
                frame = cv2.flip(raw, 0)
                cv2.imshow("Debug Tello Feed", frame)

            emergency_check(drone)

            if forward:
                safe_drone_command(
                    drone, f"move_forward({stripe_len})", drone.move_forward, stripe_len)
            else:
                safe_drone_command(
                    drone, f"move_back({stripe_len})", drone.move_back, stripe_len)

            forward = not forward

            if i < num_stripes - 1:
                safe_drone_command(
                    drone, f"move_right({SCAN_STEP_CM})", drone.move_right, SCAN_STEP_CM)

            emergency_check(drone)

        log("Scan finished. Returning left...")
        safe_drone_command(drone, f"move_left({SCAN_STEP_CM * (num_stripes - 1)})",
                           drone.move_left, SCAN_STEP_CM * (num_stripes - 1))

        emergency_check(drone)

        if not forward:
            log("Returning back to start...")
            safe_drone_command(
                drone, f"move_back({stripe_len})", drone.move_back, stripe_len)

        emergency_check(drone)

        # ---- HOMING LOOP ---- find pad and land
        log("Beginning HOMING sequence – searching for yellow pad...")
        lock_frames = 0

        while True:
            raw = frame_reader.frame
            if raw is None:
                log("WARNING: No frame read")
                emergency_check(drone)
                continue

            frame = cv2.flip(raw, 0)

            cx, cy, area = find_pad_centroid(frame)

            if cx is None:  # if not visible, rotate to search
                log("Pad not visible → rotating")
                drone.send_rc_control(0, 0, 0, 8)
                lock_frames = 0
            else:
                log(f"Pad visible with area={area}")

                # If we are already close (pad big in frame), just land
                if area > AREA_LOCK:
                    log("Pad big enough in view → LANDING")
                    drone.send_rc_control(0, 0, 0, 0)
                    safe_drone_command(drone, "land", drone.land)
                    break

                # Otherwise keep gently centering
                centered = center_over_target(drone, frame, cx, cy)
                if centered:
                    lock_frames += 1
                    log(f"Centered frames count: {lock_frames}")
                else:
                    lock_frames = 0

            emergency_check(drone)

            if lock_frames > CENTER_LOCK_FR:
                log("Pad centered → Landing now")
                safe_drone_command(drone, "land", drone.land)
                break

            cv2.imshow("Debug Tello Feed", frame)

    except Exception as e:
        log(f"MAIN LOOP ERROR: {e}")
        try:
            drone.land()
        except:
            pass

    finally:
        cv2.destroyAllWindows()
        drone.streamoff()
        log("Shutting down normally")


if __name__ == "__main__":
    main()
