import numpy as np
from .config import H_GLOBAL
GRID_CELL_CM = 14.0

def pixel_to_world(H, x, y):
    pt = np.array([[x], [y], [1.0]], dtype=np.float32)
    w = H @ pt
    if w[2, 0] != 0:
        w /= w[2, 0]
    return float(w[0, 0]), float(w[1, 0])

def world_to_grid_label(X, Y):
    X = max(X, 0)
    Y = max(Y, 0)
    col_idx = int(X // GRID_CELL_CM)
    row_idx = int(Y // GRID_CELL_CM)
    row_letter = chr(ord('A') + row_idx)
    col_number = col_idx + 1
    return f"{row_letter}{col_number}"
