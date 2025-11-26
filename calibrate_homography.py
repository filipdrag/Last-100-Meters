import cv2
import numpy as np
import time
import cv2.aruco as aruco
from djitellopy import Tello

# --------- USER / MAP SETTINGS ---------
# World coordinates in cm, origin at TOP-LEFT corner of the map.
ANCHOR_WORLD = {
    11: (0.0,   0.0),    # top-left
    7:  (210.0, 0.0),    # top-right
    19: (0.0, 140.0),    # bottom-left
    8:  (210.0, 140.0),  # bottom-right
}

ARUCO_DICT = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
ARUCO_PARAMS = aruco.DetectorParameters()

CALIB_WIDTH = 640
CALIB_HEIGHT = 480


def detect_all_tags(frame):
    """
    Detect all ArUco markers in the frame.
    Returns:
        tag_positions: dict {id: (cx, cy)} in pixel coordinates
        corners, ids: raw outputs from aruco.detectMarkers
    """
    corners, ids, _ = aruco.detectMarkers(
        frame, ARUCO_DICT, parameters=ARUCO_PARAMS
    )

    tag_positions = {}

    if ids is None:
        return tag_positions, corners, ids

    for i, tag_id in enumerate(ids.flatten()):
        pts = corners[i][0]  # 4x2
        cx = int(pts[:, 0].mean())
        cy = int(pts[:, 1].mean())
        tag_positions[int(tag_id)] = (cx, cy)

    return tag_positions, corners, ids


def compute_homography_from_anchors(tag_pixels):
    """
    Compute a 3x3 homography H that maps image pixels -> world coordinates.
    Uses the anchors defined in ANCHOR_WORLD.
    Requires at least 4 visible anchor markers.
    """
    # Which of our anchor IDs are actually visible in this frame?
    visible_ids = [tid for tid in ANCHOR_WORLD.keys() if tid in tag_pixels]

    # We want all 4 corners for a robust homography
    if len(visible_ids) < 4:
        return None

    # Use exactly 4 points (you could use more and do least-squares, but
    # here we have exactly 4 anchors).
    visible_ids = visible_ids[:4]

    src = np.float32([tag_pixels[tid] for tid in visible_ids])  # image pixels
    dst = np.float32([ANCHOR_WORLD[tid]
                     for tid in visible_ids])  # world coords

    H, status = cv2.findHomography(src, dst, method=0)  # 0 = regular LSE

    if H is None:
        return None

    return H.astype(np.float32)


def main():
    tello = Tello()
    print("[INFO] Connecting to drone...")
    tello.connect()
    print("[INFO] Battery:", tello.get_battery(), "%")

    tello.streamon()
    frame_read = tello.get_frame_read()
    time.sleep(1)

    print("[INFO] Calibration started.")
    print("→ Make sure ArUco IDs 11 (TL), 7 (TR), 19 (BL), 8 (BR) are visible.")
    print("→ Press ESC when you are satisfied with the result.\n")

    H_global = None
    stable_count = 0

    while True:
        frame = frame_read.frame
        if frame is None:
            continue

        # Flip if your normal pipeline flips (keep consistent!)
        frame = cv2.flip(frame, 0)
        frame_small = cv2.resize(frame, (CALIB_WIDTH, CALIB_HEIGHT))

        tag_pixels, corners, ids = detect_all_tags(frame_small)

        # Draw markers for feedback
        debug = frame_small.copy()
        if ids is not None:
            aruco.drawDetectedMarkers(debug, corners, ids)
        cv2.imshow("Calibration View", debug)

        # Try compute homography
        H_candidate = compute_homography_from_anchors(tag_pixels)
        if H_candidate is not None:
            H_global = H_candidate
            stable_count += 1

            if stable_count == 1:
                print("[INFO] Homography locked for the first time.")
            if stable_count % 20 == 0:
                print(f"[INFO] Homography stable for {stable_count} frames.")

        # Optionally dump result once it's been stable for a while
        if H_global is not None and stable_count >= 60:
            print("\n[RESULT] H_GLOBAL = np.array([")
            for row in H_global:
                print(f"    [{row[0]:.6f}, {row[1]:.6f}, {row[2]:.6f}],")
            print("], dtype=np.float32)\n")

        # ESC to finish
        if cv2.waitKey(1) & 0xFF == 27:
            print("[INFO] ESC pressed → exiting calibration.")
            if H_global is not None:
                print("\n[FINAL RESULT] H_GLOBAL = np.array([")
                for row in H_global:
                    print(f"    [{row[0]:.6f}, {row[1]:.6f}, {row[2]:.6f}],")
                print("], dtype=np.float32)\n")
            break

    cv2.destroyAllWindows()
    tello.streamoff()
    print("[INFO] Calibration finished. Bye.")


if __name__ == "__main__":
    main()
