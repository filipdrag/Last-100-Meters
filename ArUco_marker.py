import cv2
import cv2.aruco as aruco

# Choose a small dictionary (simple tags)
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

marker_id = 11   # victim ID = 7, home ID = 11
marker_size = 200  # pixels, for printing

img = aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
cv2.imwrite("home_marker_11.png", img)
