from pathfinder import AreaMap, Converters

testMap: AreaMap = AreaMap()
testConverter: Converters = Converters(15, 10)
testMap.printRoute(testMap.findRoute('A11', 'F11'))
