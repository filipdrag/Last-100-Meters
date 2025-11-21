import cv2
import time
from djitellopy import Tello


tello = Tello()
tello.connect()

tello.streamoff()
tello.streamon()
frame_read = tello.get_frame_read()

time.sleep(1)

while True:
    frame = frame_read.frame

    if frame is not None:
        cv2.imshow("Video Streaming", frame)

    if cv2.waitKey(1) == 27:
        frame_read.stop()
        tello.streamoff()
        break
