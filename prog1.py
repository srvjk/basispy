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

# активируем нужные сущности
if viewer:
    system.activate(viewer)
if agent:
    system.activate(agent)

# запускаем систему
system.operate()
