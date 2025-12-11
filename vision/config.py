import cv2.aruco as aruco
import numpy as np

ARUCO_DICT = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
ARUCO_PARAMS = aruco.DetectorParameters()

VICTIM_ID = 8

H_GLOBAL = np.array([
    [0.398328, 0.029717, -28.861313],
    [-0.009227, 0.427238, -8.519964],
    [0.000006, 0.000129, 1.000000],
], dtype=np.float32)


SCAN_WIDTH_CM = 190       # width of map area
SCAN_HEIGHT_CM = 80       # height of map area
SCAN_STEP_CM = 28         # sideways distance between scan stripes

CENTER_DEADBAND = 150      # px tolerance for "centered"
GRID_CELL_CM = 14.0       # grid size in cm