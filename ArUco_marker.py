import cv2
import cv2.aruco as aruco

# Choose a small dictionary (simple tags)
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

marker_id = 7   # victim ID, pick any 0–49
marker_size = 200  # pixels, for printing

img = aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
cv2.imwrite("victim_marker_id7.png", img)
