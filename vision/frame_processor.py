import cv2
import cv2.aruco as aruco

class FrameProcessor:
    def __init__(self, aruco_dict, aruco_params):
        self.aruco_dict = aruco_dict
        self.aruco_params = aruco_params

    def process_frame(self, frame):
        # Flip for mirror setup
        frame = cv2.flip(frame, 0)

        # Small frame for detection
        frame_small = cv2.resize(frame, (480, 360))

        # Debug:
        frame_debug = frame.copy()
        corners, ids, _ = aruco.detectMarkers(
            frame_debug,
            self.aruco_dict,
            parameters=self.aruco_params
        )
        if ids is not None:
            aruco.drawDetectedMarkers(frame_debug, corners, ids)
        cv2.imshow("Tello View", frame_debug)

        return frame_small, corners, ids
