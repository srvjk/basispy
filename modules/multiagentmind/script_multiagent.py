import basis
import basis_ui
import cells
import world_viewer
import net_viewer
import config_helper


def main():
    # создаем объект Системы
    system = basis.System()

    conf_hlpr = system.add_new(config_helper.TOMLHelper, "ConfigHelper")
    conf_hlpr.load("config.toml")

    gui = system.add_new(basis_ui.GuiHelper, "GuiHelper")
    if gui:
        gui.make_active()

    board = system.add_new(cells.Board, "Board")
    board.create_obstacles(density=0.1)

    agent = board.add_new(cells.Agent, "Agent")
    agent.create()
    agent.set_board(board)
    agent.make_active()

    agent.memory.set_speed_factor(99)

    w_view = system.add_new(world_viewer.WorldViewer, "WorldViewer")
    if w_view:
        w_view.make_active()

    n_view = system.add_new(net_viewer.NetViewer, "NetViewer")
    if n_view:
        n_view.make_active()

    # запускаем систему
    system.operate()

    conf_hlpr.save()

if __name__ == "__main__":
    main()
