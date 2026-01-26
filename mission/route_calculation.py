from dijkstar import Graph, find_path, NoPathError
from utils.converter import Converters
import heapq
from collections import deque

class MapSizeMismatchException(Exception):
    pass

class MapHasNoEntrancesException(Exception):
    pass
class FeatureNotImplementedException(Exception):
    def __init__(self, *args: object, message: str) -> None:
        print(f'Feature not supported yet: {message}')
        super().__init__(*args)
        

DEFAULT_MAP ='' \
'GTGGGGGTGGPGGGG' \
'GWGGGGTGGpPGTGG' \
'TGGPPPPPPPPPPPP' \
'GGpPTGGGGGGTGGG' \
'PPPPGGTGWWTTGGG' \
'GGGPGGGTWWGGTTG' \
'GGTPGGGGGGTGGGG' \
'GGTPGGpGTTGGWGT' \
'GTGPPPPPTGGGWTG' \
'GGGGGGGPGGGGGGG'
DEFAULT_WIDTH = 15
DEFAULT_HEIGHT = 10

PATH_V_COST = 1
GRASS_V_COST = 5
PATH_P_COST = 10
GRASS_P_COST = 12
TREES_P_COST = 15

PATH_MARK = 'P'
GRASS_MARK = 'G'
TREES_MARK = 'T'
WATER_MARK = 'W'
PARKING_MARK = 'p'

ALLOWED_SYMBOLS = [PATH_MARK, PARKING_MARK, GRASS_MARK, TREES_MARK, WATER_MARK]

class AreaMap:
    def __init__(self, _width: int = DEFAULT_WIDTH, _height: int = DEFAULT_HEIGHT, _fields: str = DEFAULT_MAP) -> None:
        self.width = _width
        self.height = _height
        self.converter = Converters(self.width, self.height)
        self.fields = _fields
        self.size = self.width * self.height

        if len(self.fields) != self.size:
            raise MapSizeMismatchException
        
        for ch in self.fields:
            if ch not in ALLOWED_SYMBOLS:
                raise ValueError(f"Invalid character in matrix: {ch!r}")

        self.matrix: list[list[str]] = [
            list(self.fields[y*self.width : (y+1)*self.width])
            for y in range(self.height)
        ]
        self.gates: list[tuple[int, int, int]] = list() ## get entrances (path tiles on edge of matrix)
        self.parkings: list[tuple[int, int, int]] = list()
        for i in range(self.height):
            for j in range(self.width):
                if (i==0 or i==self.height-1 or j==0 or j==self.width-1) and self.matrix[i][j] == PATH_MARK:
                    self.gates.append((j, i, i*self.width + j))
                if self.matrix[i][j] == PARKING_MARK:
                    self.parkings.append((j, i, i*self.width + j))
        if len(self.gates) == 0: ## no entrances -> invalid map
            raise MapHasNoEntrancesException
        
        
        self.vehicle_graph: Graph = Graph()
        self.pedestrian_graph: Graph = Graph()

        def node_id(r: int, c: int) -> int:
            return r * self.width + c

        NEIGHBORS = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        for r in range(self.height):
            for c in range(self.width):
                ch = self.matrix[r][c]
                u = node_id(r, c)

                # Ensure nodes exist
                self.vehicle_graph.add_node(u)
                self.pedestrian_graph.add_node(u)

                for dr, dc in NEIGHBORS:
                    nr, nc = r + dr, c + dc

                    if not (0 <= nr < self.height and 0 <= nc < self.width):
                        continue

                    neigh_ch = self.matrix[nr][nc]
                    v = node_id(nr, nc)

                    #
                    # === VEHICLE GRAPH RULES ===
                    #
                    if ch not in (TREES_MARK, WATER_MARK) and neigh_ch not in (TREES_MARK, WATER_MARK):

                        # PATH <-> PATH or PARKING <-> PARKING
                        if ch in (PATH_MARK, PARKING_MARK) and neigh_ch in (PATH_MARK):
                            v_cost = PATH_V_COST
                        else:
                            v_cost = GRASS_V_COST

                        # Add undirected edge
                        self.vehicle_graph.add_edge(u, v, v_cost)
                        self.vehicle_graph.add_edge(v, u, v_cost)

                    #
                    # === PEDESTRIAN GRAPH RULES ===
                    #
                    if ch == WATER_MARK or neigh_ch == WATER_MARK:
                        # Water blocks pedestrians entirely
                        continue

                    # PATH/PARKING <-> PATH/PARKING
                    if ch in (PATH_MARK, PARKING_MARK) and neigh_ch in (PATH_MARK, PARKING_MARK):
                        p_cost = PATH_P_COST

                    # Anything involving trees (as long as no water)
                    elif ch == TREES_MARK or neigh_ch == TREES_MARK:
                        p_cost = TREES_P_COST

                    # Grass and mixed grass/path
                    else:
                        p_cost = GRASS_P_COST

                    # Undirected edge
                    self.pedestrian_graph.add_edge(u, v, p_cost)
                    self.pedestrian_graph.add_edge(v, u, p_cost)


    def printMatrix(self)->None:
        for i in self.matrix:
            for j in i:
                print(j, end='')
            print('')
    
    def findRoute(self, src: tuple[int, int] | str | int, dest: tuple[int, int] | str | int) -> tuple[list[int], int, list[int]]:
        def normalise(value):
            """Convert input format into (x, y, id)."""
            # tuple with two ints
            if isinstance(value, tuple) and len(value) == 2 and all(isinstance(i, int) for i in value):
                x, y = value
                return x, y, y * self.width + x

            # string like 'A3'
            if isinstance(value, str) and value[0].isalpha() and value[1].isnumeric():
                id_ = self.converter.clothToId(value)
                x, y = self.converter.idToCoords(id_)
                return x, y, id_

            # id as int
            if isinstance(value, int):
                x, y = self.converter.idToCoords(value)
                return x, y, value

            raise TypeError
        
        src_x, src_y, src_id = normalise(src)
        dest_x, dest_y, dest_id = normalise(dest)

        # Validation
        if src_x > self.width or src_y > self.height:
            raise ValueError(f'Source coordinates {src} out of bounds, map has size ({self.width}, {self.height})')
        if dest_x > self.width or dest_y > self.height:
            raise ValueError(f'Destination coordinates {dest} out of bounds, map has size ({self.width}, {self.height})')
        if (src_x, src_y, src_id) not in self.gates:
            print(f'WARNING: starting navigation from non-gate tile {src}')
        if self.matrix[dest_y][dest_x] == WATER_MARK:
            raise FeatureNotImplementedException(message='It\' s not a sea rescue drone yet!')
        
        vehicle_route, foot_route, parking = None, None, None

        #VEHICLE ROUTING
        if self.matrix[dest_y][dest_x] not in (PATH_MARK, PARKING_MARK): # if the victim is not on a paved surface
            nearby_roads = self.__nNearestRoads(dest_id, 2) # find two closest roads to it
            for road in nearby_roads: 
                try:
                    vehicle_route = self.__routeVehicle(src_id, road) # navigate vehicle to the closest road
                    break
                except NoPathError: # if the chosen gate isn't reachable by car from the chosen gate, try the second closest road to victim
                    continue
                
            if vehicle_route is None: # if none of the closest roads are reachable by car, try reaching from other gates
                for gate in self.gates:
                    try:
                        route_alt_gate = self.findRoute(gate[2], dest)
                        print('WARNING: goal unreachable from preferred gate, routing from alternative')
                        return route_alt_gate
                    except NoPathError:
                        continue

                vehicle_route = [] # victim completely unreachable by car => park at desired entrance and walk all the way
                parking = src_id

            else:
                for idx, id in enumerate(vehicle_route):
                    if id in nearby_roads:
                        vehicle_route = vehicle_route[:idx+1] # if vehicle route crosses over the second closest road to victim, look for parking there
                        parking = id
                if parking is None:
                    parking = vehicle_route[-1]
        else: # the victim is already on a paved surface
            try:
                vehicle_route = self.__routeVehicle(src_id, dest_id)
                parking = vehicle_route[-1]
            except NoPathError: 
                raise FeatureNotImplementedException(message='VICTIM ON ROAD UNREACHABLE FROM CHOSEN GATE') #TODO edge case
                parking = src_id
                vehicle_route = []
        
        # PEDESTRIAN ROUTE
        try:
            foot_route = self.__routePedestrian(parking, dest_id)
        except NoPathError:
            raise FeatureNotImplementedException(message='CANNOT WALK TO VICTIM') #TODO
            foot_route = []

        # park on parking if current parking +- one node along path is marked as such
        transition = parking
        _x, _y = self.converter.idToCoords(parking)
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            x = _x + dx
            y = _y + dy
            
            if self.matrix[y][x] == PARKING_MARK:
                if abs(dx + dy) == 1 or (self.matrix[y][_x] not in (TREES_MARK, WATER_MARK) or self.matrix[_y][x] not in (TREES_MARK, WATER_MARK)):
                    transition = self.converter.coordsToId(x, y) # if parking is diagonal, check if reachable from previous transition point
                    break
        
        if(transition != parking):
            parking = transition
            vehicle_route = self.__routeVehicle(vehicle_route[0], parking)
            foot_route = self.__routePedestrian(parking, foot_route[-1])

        return (vehicle_route, parking, foot_route) 


    def __routeVehicle(self, src_id: int, dest_id: int) -> list[int]:
        route = find_path(self.vehicle_graph, src_id, dest_id)
        return [i for i in route.nodes]
    
    def __routePedestrian(self, src_id: int, dest_id: int) -> list[int]:
        route = find_path(self.pedestrian_graph, src_id, dest_id)
        return [i for i in route.nodes]
    
    def __nNearestRoads(self, src_id: int, n: int) -> list[int]:
        heap = [(0, src_id)]
        visited = set()
        found = []

        while(heap and len(found) < n):
            cost, node = heapq.heappop(heap)
            if node in visited:
                continue
            visited.add(node)

            x, y = self.converter.idToCoords(node)
            if self.matrix[y][x] in (PATH_MARK, PARKING_MARK):
                found.append((node, cost))
                if len(found) == n: break
            
            for neighbour, weight in self.pedestrian_graph.get(node, {}).items():
                if neighbour not in visited:
                    heapq.heappush(heap, (cost+weight, neighbour))
        
        found.sort(key=lambda pair: pair[1])
        return [node for node, _ in found]

    def findShortestRoute (self, src: tuple[int, int] | str | int, dest: tuple[int, int] | str | int) -> tuple[list[int], int, list[int]]:
        def normalise(value):
            if isinstance(value, tuple):
                x, y = value
                return x, y, y * self.width + x

            if isinstance(value, str):
                node_id = self.converter.clothToId(value)
                x, y = self.converter.idToCoords(node_id)
                return x, y, node_id

            if isinstance(value, int):
                x, y = self.converter.idToCoords(value)
                return x, y, value

            raise TypeError("Invalid coordinate format")

        src_x, src_y, src_id = normalise(src)
        dest_x, dest_y, dest_id = normalise(dest)

        # bounds check
        if not (0 <= src_x < self.width and 0 <= src_y < self.height):
            raise ValueError("Source out of bounds")
        if not (0 <= dest_x < self.width and 0 <= dest_y < self.height):
            raise ValueError("Destination out of bounds")

        # BFS
        queue = deque([src_id])
        came_from = {src_id: None}

        while queue:
            current = queue.popleft()

            if current == dest_id:
                break

            x, y = self.converter.idToCoords(current)

            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx = x + dx
                ny = y + dy

                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue

                nid = self.converter.coordsToId(nx, ny)

                if nid not in came_from:
                    came_from[nid] = current
                    queue.append(nid)

        # no path
        if dest_id not in came_from:
            raise NoPathError("No path found")

        # reconstruct path
        path = []
        cur = dest_id
        while cur is not None:
            path.append(cur)
            cur = came_from[cur]

        path.reverse()
        return path

    def printRoute(self, route: tuple[list[int], int, list[int]]) -> None:
        print('DRIVE: ', end = '')
        for i in route[0]:
            print(self.converter.idToCloth(i), end = ' -> ')
        print(f'\nPARK: {self.converter.idToCloth(route[1])}')
        print('WALK: ', end = '')
        for i in route[2]:
            print(self.converter.idToCloth(i), end = ' -> ')
        print('')
     
    def printShortestRoute(self, route: list[int]) -> None:
        print('FLYING: ', end = '')
        for i in route:
                print(self.converter.idToCloth(i), end = '->')
        print('')