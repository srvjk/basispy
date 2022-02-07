import basis
import basis_ui
import net_core
import net_viewer


class Scenario(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.net = None
        self.trigger_pattern_all_active = self.new(basis.OnOffTrigger, "All active")
        self.trigger_pattern_square = self.new(basis.OnOffTrigger, "Square")
        self.trigger_pattern_clear = self.new(basis.OnOffTrigger, "Clear")

    def init_net(self):
        n = 10
        neuron_index = 0
        for y in range(n):
            for x in range(n):
                neuron = self.net.new(net_core.Neuron)
                neuron.pos = [x, y]
                self.net.spatial_index.insert(neuron_index, (x, y, 0, x, y, 0), neuron.uuid)
                neuron_index += 1

        self.net.init_connections(pattern='random')

    def do_pattern_default(self):
        pass

    def do_pattern_clear(self):
        if not self.net:
            return

        for neuron in self.net.entities:
            if not isinstance(neuron, net_core.Neuron):
                continue
            neuron.set_activity(False)

    def do_pattern_all_active(self):
        if not self.net:
            return

        for neuron in self.net.entities:
            if not isinstance(neuron, net_core.Neuron):
                continue
            neuron.set_activity(True)

    def do_pattern_square(self):
        if not self.net:
            return

        pattern = [
            "----------",
            "-********-",
            "-*------*-",
            "-*------*-",
            "-*------*-",
            "-*------*-",
            "-*------*-",
            "-*------*-",
            "-********-",
            "----------"
        ]

        for neuron in self.net.entities:
            if not isinstance(neuron, net_core.Neuron):
                continue
            x = neuron.pos[0]
            y = neuron.pos[1]
            if y < len(pattern):
                if x < len(pattern[y]):
                    symbol = pattern[y][x]
                    if symbol == "-":
                        neuron.set_activity(False)
                    if symbol == "*":
                        neuron.set_activity(True)

    def step(self):
        if not self.net:
            self.net = self.system.get_entity_by_name("Net")
            if self.net:
                print("connection with Net established")
            else:
                return

            self.init_net()

        if self.trigger_pattern_all_active.active:
            self.do_pattern_all_active()
        elif self.trigger_pattern_square.active:
            self.do_pattern_square()
        elif self.trigger_pattern_clear.active:
            self.do_pattern_clear()
        else:
            self.do_pattern_default()


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
