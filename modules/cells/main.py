import sys
import basis

# создаем объект Системы
system = basis.System()

# загружаем нужные модули
cells = system.load('cells.py')
if not cells:
    sys.exit('could not load module "cells"')

world_viewer = system.load('world_viewer.py')
if not world_viewer:
    sys.exit('could not load module "world_viewer"')

net_viewer = system.load('net_viewer.py')
if not net_viewer:
    sys.exit('could not load module "net_viewer"')

board = system.new(cells.Board, "Board")
board.create_obstacles(density=0.1)

agent = board.new(cells.Agent)
agent.set_board(board)

#system.printEntities()

w_view = system.new(world_viewer.WorldViewer)
if w_view:
    system.activate(w_view)

n_view = system.new(net_viewer.NetViewer)
if n_view:
    system.activate(n_view)

if agent:
    agent.set_step_divider(50)
    system.activate(agent)

system.print_entities()

# запускаем систему
system.operate()
