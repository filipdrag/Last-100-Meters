import cv2
import cv2.aruco as aruco
from djitellopy import Tello
import time

ARUCO_DICT = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

t = Tello()
t.connect()
t.streamon()
fr = t.get_frame_read()

time.sleep(1)

while True:
    frame = fr.frame
    if frame is None:
        continue
    frame = cv2.flip(frame, 0)

    corners, ids, _ = aruco.detectMarkers(frame, ARUCO_DICT)
    if ids is not None:
        print("DETECTED:", ids.flatten())
        aruco.drawDetectedMarkers(frame, corners, ids)

    cv2.imshow("Test", frame)
    if cv2.waitKey(1) == 27:
        break
