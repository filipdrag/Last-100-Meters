import numpy as np
from vision.config import CENTER_DEADBAND
import vision.transform as transform

class VictimSearching:

    def __init__(self, drone, worker, state, scan_width, scan_height, scan_step):
        self.drone = drone
        self.worker = worker
        self.state = state
        self.scan_width = scan_width
        self.scan_height = scan_height
        self.scan_step = scan_step

        self.num_stripes = max(1, int(np.ceil(self.scan_width / self.scan_step)))
        self.stripe_len = self.scan_height
        self.forward = True
        self.current_stripe = 0
        self.finished = False
        self.victim_reported = False

        #prepare TakeOff
        self.worker.submit(self.drone.takeoff)
        self._prepare_scan_path()
    
    # Build lawnmower scan pattern
    def _prepare_scan_path(self):
        
        for i in range(self.num_stripes):
            if self.forward:
                self.worker.submit(self.drone.move_forward, (self.stripe_len // 2) + 20)
                self.worker.submit(self.drone.move_forward, self.stripe_len // 2)
            else:
                self.worker.submit(self.drone.move_back, self.stripe_len // 2)
                self.worker.submit(self.drone.move_back, self.stripe_len // 2)
            self.forward = not self.forward

            if i < self.num_stripes - 1:
                self.worker.submit(self.drone.move_right, self.scan_step)
            
        
        # Return to left after scanning
        self.worker.submit(self.drone.move_left, self.scan_step * (self.num_stripes - 1))
        # Optionally: come back along height if ended "far"
        if not self.forward:
            self.worker.submit(self.drone.move_back, self.stripe_len)

    def victim_found(self):
        print("[INFO] Scan stopped at victim → VICTIM_HOVER")
        self.state.mode = "victim_hover"
        self.state.victim_found = True
        
        # Compute victim coordinate
        vx, vy = self.state.victim_pixel
        Xw, Yw = transform.pixel_to_world(vx, vy)
        self.state.victim_world = (Xw, Yw)
        label = transform.world_to_grid_label(Xw, Yw)
        self.state.grid_label = label

        print("====================================")
        print(f"Victim pixel = ({vx},{vy})")
        print(f"World coords = ({Xw:.2f} cm, {Yw:.2f} cm)")
        print(f"Grid cell = {label}")
        print("====================================")
  
    #gives update ones tag gets detected
    def update(self, frame_small):
        #once victim found -> no more scanning logic
        if self.victim_reported:
            if self.worker.is_idle():
                self.victim_found()
            return
        
        
        from vision.detection import detect_tag
        vx, vy = detect_tag(frame_small)

        if vx is not None:
            # compute center offset
            Hs, Ws = frame_small.shape[:2]
            ex = vx - Ws//2
            ey = vy - Hs//2
            
            if abs(ex) >= CENTER_DEADBAND or abs(ey) >= CENTER_DEADBAND:
                print("Not enough in the center")
                
            # If victim nicely centered, stop scan
            elif not self.victim_reported:
                print("Victim properly centered → stop scan")
                self.victim_reported = True
                self.state.victim_pixel = (vx, vy)
                print("victim pixel: ", self.state.victim_pixel)
                
                #stop movements
                self.worker.clear()
                self.drone.send_rc_control(0, 0, 0, 0)

        # 2) Decide what to do when movement commands are finished
        if self.worker.is_idle():
            if self.victim_reported:
                self.victim_found()
            else:
                print("[INFO] Scan finished, no victim → HOMING")
                self.state.mode = "homing"
        elif self.victim_reported:
            print("victim found but worker not empty")
            