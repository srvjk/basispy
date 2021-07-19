import basis
import sys

# создаем объект Системы
system = basis.System()

# загружаем нужные модули
cells = system.load('cells.py', 'modules')
if not cells:
    sys.exit('could not load module "cells"')

# создаем нужные сущности
board = system.new(cells.Board)

viewer = system.new(cells.Viewer)
viewer.set_board(board)

agent = board.new(cells.Agent)
agent.set_board(board)

#system.printEntities()

# активируем нужные сущности
if viewer:
    system.activate(viewer)
if agent:
    system.activate(agent)

system.print_entities()

# запускаем систему
system.operate()
