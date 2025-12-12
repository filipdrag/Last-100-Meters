import numpy as np
from vision.config import CENTER_DEADBAND

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

        #prepare TakeOff
        self.worker.submit(self.drone.takeoff)
        self._prepare_scan_path()
    
    # Build lawnmower scan pattern
    def _prepare_scan_path(self):
        
        for i in range(self.num_stripes):
            if forward:
                self.worker.submit(self.drone.move_forward, (self.stripe_len // 2) + 20)
                self.worker.submit(self.drone.move_forward, self.stripe_len // 2)
            else:
                self.worker.submit(self.drone.move_back, self.stripe_len // 2)
                self.worker.submit(self.drone.move_back, self.stripe_len // 2)
            forward = not forward

            if i < self.num_stripes - 1:
                self.worker.submit(self.drone.move_right, self.scan_step)
            
        
        # Return to left after scanning
        self.worker.submit(self.drone.move_left, self.scan_step * (self.num_stripes - 1))
        # Optionally: come back along height if ended "far"
        if not forward:
            self.worker.submit(self.drone.move_back, self.stripe_len)

  
    #gives update ones tag gets detected
    def update(self, frame_small):

        from vision.detection import detect_tag
        vx, vy = detect_tag(frame_small)

        if vx is not None:
            # compute center offset
            Hs, Ws = frame_small.shape[:2]
            ex = vx - Ws//2
            ey = vy - Hs//2
            print("Not enough in the center")

            # If victim nicely centered, stop scan
            if (abs(ex) < CENTER_DEADBAND and abs(ey) < CENTER_DEADBAND) and not victim_reported:
                print("Victim properly centered → stop scan")
                victim_reported = True
                victim_pixel = (vx, vy)
                self.worker.clear()

        # 2) Decide what to do when movement commands are finished
        if self.worker.is_idle():
            self.drone.drone.send_rc_control(0, 0, 0, 0)
            if victim_reported:
                print("[INFO] Scan stopped at victim → VICTIM_HOVER")
                self.state = "victim_hover"
            else:
                print("[INFO] Scan finished, no victim → HOMING")
                self.state = "homing"
        return victim_pixel