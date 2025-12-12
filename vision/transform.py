import numpy as np
from .config import H_GLOBAL
GRID_CELL_CM = 14.0

# pixel → world coordinate transform using H_GLOBAL
def pixel_to_world(x, y):
    pt = np.array([[x], [y], [1.0]], dtype=np.float32)
    w = H_GLOBAL @ pt
    if w[2, 0] != 0:
        w /= w[2, 0]
    return float(w[0, 0]), float(w[1, 0])

# world → grid cell label
def world_to_grid_label(X, Y):
    # clamp negative values
    X = max(X, 0)
    Y = max(Y, 0)

    # compute column (numbers) and row (letters)
    col_idx = int(X // GRID_CELL_CM)    # 0 → column 1
    row_idx = int(Y // GRID_CELL_CM)    # 0 → row A

    # convert row index to letter
    row_letter = chr(ord('A') + row_idx)
    # convert column index to number (1-based)
    col_number = col_idx + 1
    
    return f"{row_letter}{col_number}"
