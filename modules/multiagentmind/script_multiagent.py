import basis
import basis_ui
import cells
import world_viewer
import net_viewer


def main():
    # создаем объект Системы
    system = basis.System()

    gui = system.add_new(basis_ui.GuiHelper, "GuiHelper")
    if gui:
        system.activate(gui)

    board = system.add_new(cells.Board, "Board")
    board.create_obstacles(density=0.1)

    agent = board.add_new(cells.Agent, "Agent")
    agent.create()
    agent.set_board(board)
    system.activate(agent)

    w_view = system.add_new(world_viewer.WorldViewer)
    if w_view:
        system.activate(w_view)

    n_view = system.add_new(net_viewer.NetViewer)
    if n_view:
        system.activate(n_view)

    # запускаем систему
    system.operate()


if __name__ == "__main__":
    main()
