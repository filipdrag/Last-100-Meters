class DroneState:
    def __init__(self):
        self.mode = "scan"
        self.victim_found = False
        self.victim_pixel = None
        self.victim_world = None
        self.grid_label = None
        
        self.yaw = 0 #0=N, 90=E, 180=S, 270=W

