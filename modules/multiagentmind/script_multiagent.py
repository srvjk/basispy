import basis
import basis_ui
import cells
import world_viewer

def main():
    # создаем объект Системы
    system = basis.System()

    gui = system.new(basis_ui.GuiHelper, "GuiHelper")
    if gui:
        system.activate(gui)

    board = system.new(cells.Board, "Board")
    board.create_obstacles(density=0.1)

    agent = board.new(cells.Agent)
    agent.set_board(board)
    system.activate(agent)

    w_view = system.new(world_viewer.WorldViewer)
    if w_view:
        system.activate(w_view)

    # запускаем систему
    system.operate()


if __name__ == "__main__":
    main()
