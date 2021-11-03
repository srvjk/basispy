import basis
import sys

# создаем объект Системы
system = basis.System()

# загружаем нужные модули
cells = system.load('cells.py', '.')
if not cells:
    sys.exit('could not load module "cells"')

# создаем нужные сущности
system.new(cells.ResourceManager, "ResourceManager")

board = system.new(cells.Board, "Board")
board.create_obstacles(density=0.1)

agent = board.new(cells.Agent)
agent.set_board(board)

#system.printEntities()

viewer = system.new(cells.Viewer)
if viewer:
    system.activate(viewer)

net_viewer = system.new(cells.NetViewer)
if net_viewer:
    system.activate(net_viewer)

if agent:
    agent.set_step_divider(50)
    system.activate(agent)

system.print_entities()

# запускаем систему
system.operate()
