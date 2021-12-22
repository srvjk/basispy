import sys
import basis
import basis_ui
import net


class Scenario(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.net = None

    def init_net(self):
        main_subnet = self.net.new(net.SubNet, "MainSubNet")
        if not main_subnet:
            return

        n = 10
        for row in range(n):
            for col in range(n):
                neuron = main_subnet.new(net.Neuron)
                neuron.geo_pos[0] = col * neuron.geo_size[0]
                neuron.geo_pos[1] = row * neuron.geo_size[1]

        main_subnet.init_connections(pattern='random')

    def step(self):
        if not self.net:
            self.net = self.system.get_entity_by_name("Net")
            if self.net:
                print("connection with Net established")
            else:
                return

            self.init_net()


def main():
    # создаем объект Системы
    system = basis.System()

    gui = system.new(basis_ui.GuiHelper, "GuiHelper")
    if gui:
        system.activate(gui)

    # загружаем нужные модули
    cells = system.load('cells.py')
    if not cells:
        sys.exit('could not load module "cells"')

    net_module = system.load("net.py")
    if not net_module:
        sys.exit('could not load module "net"')

    net = system.new(net_module.Net, "Net")

    net_viewer = system.load('net_viewer.py')
    if not net_viewer:
        sys.exit('could not load module "net_viewer"')

    n_view = system.new(net_viewer.NetViewer)
    if n_view:
        n_view.net_name = "Net"  # TODO убрать это отсюда
        system.activate(n_view)

    scenario = system.new(Scenario, "Scenario")
    if scenario:
        system.activate(scenario)

    # выводим главную панель управления
    # control_panel = system.new(basis_ui.ControlPanel, "ControlPanel")
    # if control_panel:
    #     system.activate(control_panel)

    # запускаем систему
    system.operate()


if __name__ == "__main__":
    main()
