import time
import vision.transform as transform

class VictimHover:

    def __init__(self, drone, victim_pixel, state):
        self.ddrone = drone
        self.victim_pixel = victim_pixel
        self.state=state

    def update(self):
        # 1) Show X on matrix
        self.drone.show_pattern("X_SHAPE")

        # 2) Hover for ~2 seconds, keeping ESC responsive
        hover_start = time.time()
        while time.time() - hover_start < 2.0:
            self.drone.drone.send_rc_control(0, 0, 0, 0)

            from utils.emergency import emergency_check
            emergency_check(self.drone)

            time.sleep(0.05)

        # 3) CLEAR LED + RESET MOTION
        self.drone.drone.send_expansion_command("mled g 0")

        # Compute victim coordinate
        vx, vy = self.victim_pixel
        Xw, Yw = transform.pixel_to_world(vx, vy)
        label = transform.world_to_grid_label(Xw, Yw)

        print("====================================")
        print(f"Victim pixel = ({vx},{vy})")
        print(f"World coords = ({Xw:.2f} cm, {Yw:.2f} cm)")
        print(f"Grid cell = {label}")
        print("====================================")

        print("[INFO] Finished victim hover → ROUTE CALCULATION")
        self.state = "route_calc"
    
    #TODO: possible further communication with patient