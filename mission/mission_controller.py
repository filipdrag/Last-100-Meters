import time
from mission.victim_searching import VictimSearching
from mission.victim_hover import victim_hover, victim_communication
from vision.config import SCAN_WIDTH_CM, SCAN_HEIGHT_CM, SCAN_STEP_CM
from utils.voice import Voice 
from mission.route_calculation import AreaMap
from mission.fly_path import fly_path, fly_path_visuals



class MissionController:
    def __init__(self, drone, state, frame_processor):
        self.drone = drone
        self.state = state
        self.frame_processor = frame_processor
        self.map: AreaMap = AreaMap()

    def update(self, frame, scanning):
        running = True
        scanning = scanning
        # Global emergency key
        from utils.emergency import emergency_check
        emergency_check(self.drone)

        if self.state.mode == "scan":
            if scanning:
                self._scan(frame)
            else: 
                scanning = True
        elif self.state.mode == "victim_hover":
            self._victim_hover()
            scanning = False
        elif self.state.mode == "guide_ambulance":            
            self._guide_ambulance()
            scanning = False
        elif self.state.mode == "homing":
            return self._homing(), False
        
        return running, scanning

    #scanning of area and detection of victim
    def _scan(self, frame):
        
        frame_small, corners, ids = self.frame_processor.process_frame(frame)
        
        if not hasattr(self, "victim_search"):
            self.victim_search = VictimSearching(
                drone=self.drone.drone, 
                worker=self.drone.worker, 
                state=self.state,
                scan_width=SCAN_WIDTH_CM, 
                scan_height=SCAN_HEIGHT_CM, 
                scan_step=SCAN_STEP_CM
            )

        self.victim_search.update(frame_small)

        
    #hovering over patient and communicating with them
    def _victim_hover(self):
        print("[INFO] Starting victim hover...")
        
        
        victim_hover(self.drone)
        
        voice = Voice(rate=175)
        victim_communication(self.drone, voice)
        
        self.state.mode = "guide_ambulance"
        print("[MISSION] Victim hover and communication done -> guiding ambulance")

    #drone flys towards amblance and guides it to patient
    def _guide_ambulance(self):
        print("[INFO] Starting guidance of ambulance...")
        #compute path from patient to entrance
        route = self.map.findShortestRoute(self.state.grid_label, "A11")
        print("route (victim -> entrance): ", route)
        print("route in Grid labels: ", self.map.printShortestRoute(route))
        
        if self.drone.worker.is_idle():
            print("Worker starting now")
        
        #send drone to entrance
        try:
            fly_path(self.drone, route)
            
            while not self.drone.worker.is_idle():
                time.sleep(0.05)
        except Exception as e:
            print("[ERROR] during flying towards ambulance: ", e)
            try:
                self.drone.drone.land()
            except:
                pass
        
        #compute path for guidance of ambulance
        route = self.map.findRoute("A11", self.state.grid_label)
        print("route (entrance -> victim): ", route)
        print("route in Grid labels: ", self.map.printRoute(route))
        
        #guide ambulance from entrance to patient
        try:
            fly_path_visuals(self.drone, route, self.state)
            while not self.drone.worker.is_idle():
                time.sleep(0.05)
        except Exception as e:
            print("[ERROR] during guiding ambulance: ", e)
            try:
                self.drone.drone.land()
            except:
                pass
        
        self.state.mode = "homing"
        print("[MISSION] guiding ambulance towards patient done -> homing")
        
    
        #drone flies home from patient
    def _homing(self):
        print("[INFO] starting homing...")
        
        #compute path from patient to home
        if (self.state.grid_label != None):
            route = self.map.findShortestRoute(self.state.grid_label, "J1")
            print("route (victim -> home): ", route)
            print("route in Grid labels: ", self.map.printShortestRoute(route))
        
            #send drone home
            try:
                fly_path(self.drone, route)
                while not self.drone.worker.is_idle():
                    time.sleep(0.05)
            except Exception as e:
                print("[ERROR] during returning home: ", e)
        else:
            print("no grid label")      

        while not self.drone.worker.is_idle():
            time.sleep(0.05)

        time.sleep(5)
        self.drone.drone.send_rc_control(0, 0, 0, 0)
        time.sleep(0.2)
        
        try:
            self.drone.drone.land()

        except Exception as e:
            print("[ERROR] during landing:", e)
            
        # Stop worker thread fully
        self.drone.worker.clear()
        self.drone.worker.stop()

        print("[MISION] Homing complete -> mission finished")
        return False

