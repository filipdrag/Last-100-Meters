import time
from drone.controller import DroneController
from drone.state import DroneState
from mission.mission_controller import MissionController
from vision.frame_processor import FrameProcessor
from vision.config import ARUCO_DICT, ARUCO_PARAMS

def main():
    drone = DroneController()
    state = DroneState()
    frame_processor = FrameProcessor(ARUCO_DICT, ARUCO_PARAMS)
    mission = MissionController(drone, state, frame_processor)
    scanning = False
    
    drone.connect_and_start()
    
    frame_reader = drone.drone.get_frame_read()
    time.sleep(1)
    
    state.yaw = 0
    
    try:
        while True:
            frame = None
            
            if (scanning):
                frame = frame_reader.frame
                if frame is None:
                    continue

            keep_running, scanning = mission.update(frame, scanning)

            if keep_running is False:
                print("[Main] Mission ended")
                print("[INFO] Battery:", drone.drone.get_battery())
                break 
            
    except KeyboardInterrupt:
        print("[INFO] Shutting down...")
    finally:
        drone.worker.stop()
        print("[INFO] Shutdown complete")

if __name__ == "__main__":
    main()
