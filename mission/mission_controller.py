from mission.victim_searching import VictimSearching
from vision.config import SCAN_WIDTH_CM, SCAN_HEIGHT_CM, SCAN_STEP_CM 



class MissionController:
    def __init__(self, drone, state):
        self.drone = drone
        self.state = state

    def update(self, frame):
        if self.state.mode == "scan":
            self._scan(frame)
        elif self.state.mode == "victim_hover":
            self._victim_hover()
        elif self.state.mode == "homing":
            self._homing()
        elif self.state.mode == "route_calc":
            self._route_calc()
        elif self.state.mode == "guide_ambulance":
            self._guide_ambulance()

    #scanning of area and detection of victim
    def _scan(self, frame):
        if not hasattr(self, "victim_search"):
            self.victim_search = VictimSearching(
                drone=self.drone.drone, 
                worker=self.drone.worker, 
                scan_width=SCAN_WIDTH_CM, 
                scan_height=SCAN_HEIGHT_CM, 
                scan_step=SCAN_STEP_CM
            )

        result = self.victim_search.update(frame)

        if result:
            (vx, vy) = result
            self.state.victim_pixel = (vx, vy)
            self.state.mode = "victim_hover"

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
