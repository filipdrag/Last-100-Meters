import time
import numpy as np
from vision.config import SCAN_STEP_CM, SCAN_WIDTH_CM

def execute_homing(drone, worker ):
    print("[INFO] Executing return path now...")

    # Stop worker thread fully
    worker.clear()
    worker.stop()
    time.sleep(0.2)   # small delay to avoid race condition

    drone.send_rc_control(0, 0, 0, 0)
    time.sleep(0.2)

    num_stripes = max(1, int(np.ceil(SCAN_WIDTH_CM / SCAN_STEP_CM)))

    try:
        drone.move_left((SCAN_STEP_CM * (num_stripes - 1)))
        drone.land()

    except Exception as e:
        print("[ERROR] during return:", e)
        try:
            drone.land()
        except:
            pass


    
    