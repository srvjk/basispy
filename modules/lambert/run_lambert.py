import basis
import basis_ui
import lambert_core as core
import lambert_world_viewer as world_viewer
import config_helper


def main():
    # создаем объект Системы
    system = basis.System()

    conf_hlpr = system.add_new(config_helper.TOMLHelper, "ConfigHelper")
    conf_hlpr.load("config.toml")

    gui = system.add_new(basis_ui.GuiHelper, "GuiHelper")

    board = system.add_new(core.Board, "Board")
    board.step_min_time_period = 1.0
    board.create_obstacles(density=0.5)

    agent = board.add_new(core.Agent, "Agent")
    agent.step_min_time_period = 1.0
    agent.create()
    agent.set_board(board)

    w_view = system.add_new(world_viewer.WorldViewer, "WorldViewer")

    # запускаем систему
    system.operate()

    conf_hlpr.save()

if __name__ == "__main__":
    main()
