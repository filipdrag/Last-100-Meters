ABC = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

class Converters:
    def __init__(self, _width: int, _height: int) -> None:
        self.width = _width
        self.height = _height

        self.idToCloth_x = {}
        self.idToCloth_y = {}
        self.clothToId_x = {}
        self.clothToId_y = {}

        for i in range(self.width):
            cloth_x = str(i + 1)
            self.idToCloth_x[i] = cloth_x
            self.clothToId_x[cloth_x] = i
        for i in range(self.height):
            self.idToCloth_y[i] = ABC[i]
            self.clothToId_y[ABC[i]] = i

        pass

    def idToCloth(self, node_id: int) -> str:
        y = node_id // self.width
        x = node_id % self.width
        return self.idToCloth_y[y] + self.idToCloth_x[x]
    
    def clothToId(self, cloth_id: str) -> int: 
        i = 0
        while i < len(cloth_id) and cloth_id[i].isalpha():
            i += 1

        y_part = cloth_id[:i]
        x_part = cloth_id[i:]

        y = self.clothToId_y[y_part]
        x = self.clothToId_x[x_part]

        return y * self.width + x
    
    def idToCoords(self, node_id: int) -> tuple[int, int]: # coords in format (x, y)
        return (node_id % self.width, node_id // self.width)
    
    def coordsToId(self, x: int, y: int) -> int: # coords in format (x, y)
        return y * self.width + x