import basis
import sys

# создаем объект Системы
system = basis.System()

# загружаем нужные модули
cells = system.load('cells.py', 'modules')
if not cells:
    sys.exit('could not load module "cells"')

# создаем нужные сущности
system.new(cells.ResourceManager, "ResourceManager")

board = system.new(cells.Board, "Board")
board.create_obstacles(density=0.1)

viewer = system.new(cells.Viewer)
#viewer.set_board(board)

agent = board.new(cells.Agent)
agent.set_board(board)

#system.printEntities()

# активируем нужные сущности
if viewer:
    system.activate(viewer)

if agent:
    agent.set_step_divider(10)
    system.activate(agent)

system.print_entities()

# запускаем систему
system.operate()
