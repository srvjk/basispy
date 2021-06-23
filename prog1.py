import basis
import sys

# создаем объект Системы
system = basis.System()

# загружаем нужные модули
cells = system.load('cells.py', 'modules')
if not cells:
    sys.exit('could not load module "cells"')

# создаем нужные сущности
board = cells.Board()
viewer = cells.Viewer()
agent = cells.Agent()

#system.printEntities()

# оживляем нужные сущности
if agent:
    system.animate(agent)

# запускаем систему
system.operate()
