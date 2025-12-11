import cv2
import cv2.aruco as aruco
from .config import ARUCO_DICT, ARUCO_PARAMS, VICTIM_ID

def detect_tag(frame_small, target_id=VICTIM_ID):
    corners, ids, _ = aruco.detectMarkers(frame_small, ARUCO_DICT, parameters=ARUCO_PARAMS)
    if ids is None:
        return None, None

    for i, found_id in enumerate(ids.flatten()):
        if found_id == target_id:
            pts = corners[i][0]
            cx = int(pts[:, 0].mean())
            cy = int(pts[:, 1].mean())
            return cx, cy
    return None, None
