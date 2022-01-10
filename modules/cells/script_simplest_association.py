import basis
import basis_ui
import net_core
import net_viewer


class Scenario(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.net = None

    def init_net(self):
        n = 20
        neuron_index = 0
        for y in range(n):
            for x in range(n):
                neuron = self.net.new(net_core.Neuron)
                neuron.pos = [x, y]
                self.net.spatial_index.insert(neuron_index, (x, y, 0, x, y, 0), neuron.uuid)
                neuron_index += 1

        self.net.init_connections(pattern='random')

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

    system.new(net_core.Net, "Net")

    n_view = system.new(net_viewer.NetViewer)
    if n_view:
        n_view.net_name = "Net"  # TODO убрать это отсюда
        system.activate(n_view)

    scenario = system.new(Scenario, "Scenario")
    if scenario:
        system.activate(scenario)

    # запускаем систему
    system.operate()


if __name__ == "__main__":
    main()
