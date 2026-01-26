import time
from utils.converter import Converters
from mission.route_calculation import DEFAULT_HEIGHT, DEFAULT_WIDTH

CELL_SIZE_CM = 14

  
def compress_path(path, converter):
    """
    compresses several moves into one direction into one move
    """
    moves = []

    current_dir = None
    length = 0

    for a, b in zip(path, path[1:]):
        x1, y1 = converter.idToCoords(a)
        x2, y2 = converter.idToCoords(b)

        dx = x2 - x1
        dy = y2 - y1

        if dx == 1:
            d = "R"
        elif dx == -1:
            d = "L"
        elif dy == 1:
            d = "B"
        elif dy == -1:
            d = "F"
        else:
            raise ValueError("Invalid grid step")

        if d == current_dir:
            length += 1
        else:
            if current_dir is not None:
                moves.append((current_dir, length))
            current_dir = d
            length = 1

    moves.append((current_dir, length))
    return moves
    
def round_to_nearest_20(cm: int) -> int:
    return max(20, round(cm / 20) * 20)

#drone flys given path without visual guidance
def fly_path(drone, path: list[int]):
    """
    Converts a grid path into drone movement commands.
    """
    
    converter = Converters(DEFAULT_WIDTH, DEFAULT_HEIGHT)

    if len(path) < 2:
        return

    moves = compress_path(path, converter)

    for direction, steps in moves:
        distance = steps * CELL_SIZE_CM
        
        distance = round_to_nearest_20(distance)

        if direction == "R":
            drone.worker.submit(drone.drone.move_right, distance)

        elif direction == "L":
            drone.worker.submit(drone.drone.move_left, distance)

        elif direction == "F":
            drone.worker.submit(drone.drone.move_forward, distance)

        elif direction == "B":
            drone.worker.submit(drone.drone.move_back, distance)

        drone.worker.submit(time.sleep, distance/25.0 + 0.3)
        drone.worker.wait_until_idle()


def rotate_to_world_dir(drone, state, target_world_dir):
    target_yaw = {"N":180,"E":270,"S":0,"W":90}[target_world_dir]
    diff = (target_yaw - state.yaw) % 360

    if diff == 90:
        print("right")
        drone.worker.submit(drone.show_pattern, "TURN_RIGHT")
        time.sleep(2)
        drone.worker.submit(drone.drone.rotate_clockwise, 90)
        drone.worker.submit(time.sleep, 1.2)
        drone.worker.wait_until_idle()
        state.yaw = (state.yaw + 90) % 360
    elif diff == 180:
        print("180 turn")
        drone.worker.submit(drone.drone.rotate_clockwise, 180)
        drone.worker.submit(time.sleep, 2.4)
        drone.worker.wait_until_idle()
        state.yaw = (state.yaw + 180) % 360
    elif diff == 270:
        print("left")
        drone.worker.submit(drone.show_pattern, "TURN_LEFT")
        time.sleep(2)
        drone.worker.submit(drone.drone.rotate_counter_clockwise, 90)
        drone.worker.submit(time.sleep, 1.2)
        drone.worker.wait_until_idle()
        state.yaw = (state.yaw - 90) % 360


def compress_path_world(path, converter):
    """
    Compresses grid path into world directions (N,E,S,W)
    """
    moves = []

    current_dir = None
    length = 0

    for a, b in zip(path, path[1:]):
        x1, y1 = converter.idToCoords(a)
        x2, y2 = converter.idToCoords(b)

        if x2 == x1 + 1:
            d = "E"
        elif x2 == x1 - 1:
            d = "W"
        elif y2 == y1 - 1:
            d = "N"
        elif y2 == y1 + 1:
            d = "S"
        else:
            raise ValueError("Invalid grid step")

        if d == current_dir:
            length += 1
        else:
            if current_dir is not None:
                moves.append((current_dir, length))
            current_dir = d
            length = 1

    moves.append((current_dir, length))
    return moves


def fly_path_visuals(drone, route, state):
    """
    Drone flies a given path with visual guidance for the ambulance.
    Shows LED patterns before rotation and movement.
    Combines consecutive steps in one direction.
    Drone flies backwards so LEDs face backward.
    """
    vehicle_route, parking, foot_route = route
    converter = Converters(DEFAULT_WIDTH, DEFAULT_HEIGHT)

    last_world_dir = state.yaw

    def fly_path(path):
        nonlocal last_world_dir
        moves = compress_path_world(path, converter)
        print("moves: ", moves)

        if not path or len(path) < 2:
            return


        for wdir, steps in moves:
            distance = steps * CELL_SIZE_CM 
            distance = round_to_nearest_20(distance)

            #announce direction change on LED-Matrix and rotate in new direction
            if wdir != last_world_dir:
                rotate_to_world_dir(drone, state, wdir)

            # FORWARD on LED-Matrix
            drone.worker.submit(drone.show_pattern, "UP")
            time.sleep(2)

            # movement into direction
            drone.worker.submit(drone.drone.move_back, distance)
            drone.worker.submit(time.sleep, distance/25.0 + 0.3)
            drone.worker.wait_until_idle()

            last_world_dir = wdir
            

    # --- VEHICLE ROUTE ---
    fly_path(vehicle_route)

    # --- PARKING TRANSITION ---
    drone.worker.submit(drone.show_pattern, "PARKING")
    time.sleep(3)

    # --- FOOT ROUTE ---
    fly_path(foot_route)

    # --- ARRIVED ---
    drone.worker.submit(drone.show_pattern, "X_SHAPE")
    time.sleep(2)
    rotate_to_world_dir(drone, state, "S")
    drone.worker.submit(drone.show_pattern, "HOMING")
    time.sleep(2)
   

    

