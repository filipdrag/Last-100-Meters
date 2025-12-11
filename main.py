from drone.controller import DroneController
from drone.state import DroneState
from mission.mission_controller import MissionController
from vision.detection import detect_tag

def main():
    drone = DroneController()
    state = DroneState()
    mission = MissionController(drone, state)

    drone.connect_and_start()

    try:
        while True:
            frame = drone.get_frame()
            if frame is None:
                continue
            # Resize oder preprocess falls nötig
            mission.update(frame)
    except KeyboardInterrupt:
        print("[INFO] Shutting down...")
    finally:
        drone.worker.stop()
        print("[INFO] Shutdown complete")

if __name__ == "__main__":
    main()
