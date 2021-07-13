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
viewer = cells.Viewer(board)
agent = cells.Agent()

#system.printEntities()

# активируем нужные сущности
if viewer:
    system.activate(viewer)
if agent:
    system.activate(agent)

system.print_entities()

# запускаем систему
system.operate()
