from mission.victim_searching import VictimSearching
from vision.config import SCAN_WIDTH_CM, SCAN_HEIGHT_CM, SCAN_STEP_CM 



class MissionController:
    def __init__(self, drone, state, frame_processor):
        self.drone = drone
        self.state = state
        self.frame_processor = frame_processor

    def update(self, frame):

        frame_small, corners, ids = self.frame_processor.process_frame(frame)

        # Global emergency key
        from utils.emergency import emergency_check
        emergency_check(self.drone.drone)

        if self.state.mode == "scan":
            self._scan(frame_small)
        elif self.state.mode == "victim_hover":
            self._victim_hover()
        elif self.state.mode == "route_calc":
            self._route_calc()
        elif self.state.mode == "guide_ambulance":
            self._guide_ambulance()
        elif self.state.mode == "homing":
            self._homing()

    #scanning of area and detection of victim
    def _scan(self, frame_small):
        if not hasattr(self, "victim_search"):
            self.victim_search = VictimSearching(
                drone=self.drone.drone, 
                worker=self.drone.worker, 
                scan_width=SCAN_WIDTH_CM, 
                scan_height=SCAN_HEIGHT_CM, 
                scan_step=SCAN_STEP_CM
            )

        self.state = self.victim_search.update(frame_small)

        

    def _victim_hover(self):
        # TODO: LED anzeigen, Hover, Pixel→World, etc.
        pass

    def _homing(self):
        # TODO: Rückflug Logik
        pass

    def _route_calc(self):
        # TODO: kürzester Weg berechnen
        pass

    def _guide_ambulance(self):
        # TODO: Krankenwagen zurückführen
        pass

