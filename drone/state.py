class DroneState:
    def __init__(self):
        self.mode = "scan"
        self.victim_found = False
        self.victim_pixel = None
        self.victim_world = None
        self.grid_label = None

"""TODO: check on states"""