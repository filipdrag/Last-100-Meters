import numpy as np


class VictimSearching:

    def __init__(self, drone, worker, scan_width, scan_height, scan_step):
        self.drone = drone
        self.worker = worker
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

  
    #TODO: überprüfen ob richtig funktioniert
    #gives update ones tag gets detected
    def update(self, frame):
        
        from vision.detection import detect_tag
        vx, vy = detect_tag(frame)

        if vx is not None:
            self.worker.clear()  
            self.finished = True
            return (vx, vy)  
        return None