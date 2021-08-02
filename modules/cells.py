import basis
import sys
import random
import pygame
import pygame_gui
from pygame_gui.ui_manager import UIManager
from pygame_gui.elements.ui_window import UIWindow
from pygame_gui.elements.ui_image import UIImage


class Link:
    def __init__(self):
        self.weight = 0
        self.src_neuron = None
        self.dst_neuron = None


class Neuron:
    def __init__(self):
        self.out_links = list()
        self.pos = [0, 0]


class Layer:
    def __init__(self, name):
        self.name = name
        self.neurons = list()

    def create(self, num_neurons):
        self.neurons = [Neuron() for _ in range(num_neurons)]

    def connect(self, target_layer):
        for src in self.neurons:
            for dst in target_layer.neurons:
                # прямые связи:
                fwd_link = Link()
                fwd_link.src_neuron = src
                fwd_link.dst_neuron = dst
                src.out_links.append(fwd_link)

                # обратные связи
                back_link = Link()
                back_link.src_neuron = dst
                back_link.dst_neuron = src
                dst.out_links.append(back_link)


class Net:
    def __init__(self):
        self.layers = list()

    def new_layer(self, layer_name, num_neurons):
        layer = Layer(layer_name)
        layer.create(num_neurons)
        self.layers.append(layer)
        return layer

    def print(self):
        print("Layers: {}".format(len(self.layers)))
        for layer in self.layers:
            print("{}: {}".format(layer.name, len(layer.neurons)))


class Board(basis.Entity):
    def __init__(self):
        super().__init__()
        self.agents = list()
        self.size = 100
        self.cell_size = 3
        self.visual_field = pygame.Surface((self.size_in_pixels(), self.size_in_pixels()))
        self.back_color = (10, 10, 10)

    def size_in_cells(self):
        return self.size

    def size_in_pixels(self):
        return self.size * self.cell_size

    def add_agent(self, agent):
        self.agents.append(agent)

    def draw(self):
        self.visual_field.fill(self.back_color)

        for agent in self.agents:
            if isinstance(agent, Agent):
                try:
                    p = agent.position
                    agent_pos = agent.position
                    agent_rect = pygame.Rect(agent_pos[0] * self.cell_size, agent_pos[1] * self.cell_size,
                                             self.cell_size, self.cell_size)
                    pygame.draw.rect(self.visual_field, (100, 0, 0), agent_rect)
                except AttributeError:
                    pass


class NetView(UIWindow):
    def __init__(self, net, position, ui_manager):
        super().__init__(pygame.Rect(position, (320, 240)), ui_manager, window_display_title='Neural Net',
                         object_id='#neural_net')
        self.net = net
        surface_size = self.get_container().get_size()
        self.size = surface_size
        self.surface_element = UIImage(pygame.Rect((0, 0), surface_size), pygame.Surface(surface_size).convert(),
                                       manager=ui_manager, container=self, parent_element=self)

    def set_net(self, net):
        self.net = net

    def process_event(self, event):
        handled = super().process_event(event)
        return handled

    def update(self, time_delta):
        super().update(time_delta)
        self.draw()

    def draw(self):
        self.surface_element.image.fill((0, 0, 0))

        if self.net is None:
            return

        max_neurons = 0
        for layer in self.net.layers:
            n = len(layer.neurons)
            if n > max_neurons:
                max_neurons = n

        if max_neurons < 1:
            return

        net_area_width = self.size[0]
        net_area_height = self.size[1]

        sx = net_area_width / max_neurons
        sy = net_area_height / len(self.net.layers)
        s = int(min(sx, sy))
        neuron_fill_coeff = 0.5  # какой процент места занимает нейрон в отведенном ему квадратике

        radius = int((s * neuron_fill_coeff) / 2)

        y = net_area_height - radius
        for layer in self.net.layers:
            layer_sx = s * len(layer.neurons)
            empty_space_left = int((net_area_width - layer_sx) / 2)
            x = empty_space_left + radius
            for neuron in layer.neurons:
                neuron.pos = [x, y]
                pygame.draw.circle(self.surface_element.image, (100, 100, 100), neuron.pos, radius)
                x += s
            y -= s

        for layer in self.net.layers:
            for neuron in layer.neurons:
                for link in neuron.out_links:
                    src_x = link.src_neuron.pos[0]
                    src_y = link.src_neuron.pos[1] - radius
                    dst_x = link.dst_neuron.pos[0]
                    dst_y = link.dst_neuron.pos[1] + radius
                    pygame.draw.line(self.surface_element.image, (50, 50, 50), (src_x, src_y), (dst_x, dst_y))


class Viewer(basis.Entity):
    def __init__(self):
        super().__init__()
        pygame.init()
        pygame.display.set_caption('Cells')
        self.board = None
        size = width, height = 640, 480
        self.bk_color = (0, 0, 0)
        self.point_color = (100, 100, 100)
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.background_surface = None
        self.show_grid = True
        self.delay = 0.5
        self.ui_manager = pygame_gui.UIManager(size)
        self.clock = pygame.time.Clock()
        self.toggle_grid_button = None
        self.net_window = None
        self.recreate_ui()

    def recreate_ui(self):
        self.background_surface = pygame.Surface(self.screen.get_size()).convert()
        self.background_surface.fill(self.bk_color)
        self.ui_manager.set_window_resolution(self.screen.get_size())
        self.ui_manager.clear_and_reset()
        button_layout_rect = pygame.Rect(0, 0, 100, 20)
        button_layout_rect.topright = (-10, 10)
        self.toggle_grid_button = pygame_gui.elements.UIButton(relative_rect=button_layout_rect,
                                                               text='Grid', manager=self.ui_manager,
                                                               anchors={'left': 'right',
                                                                        'right': 'right',
                                                                        'top': 'top',
                                                                        'bottom': 'bottom'})
        self.net_window = NetView(None, (100, 100), self.ui_manager)

    def set_board(self, board):
        self.board = board

    def step(self):
        time_delta = self.clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.VIDEORESIZE:
                print("new size {}x{}".format(event.w, event.h))
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                self.recreate_ui()
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.toggle_grid_button:
                        self.show_grid = not self.show_grid

            self.ui_manager.process_events(event)

        self.ui_manager.update(time_delta)

        self.screen.blit(self.background_surface, (0, 0))

        actual_size = pygame.display.get_window_size()

        # draw the board
        if self.board:
            board_size = min(actual_size[0], actual_size[1])
            self.board.draw()
            scaled_visual_field = pygame.transform.scale(self.board.visual_field, (board_size, board_size))
            self.screen.blit(scaled_visual_field, (0, 0))

            if self.show_grid:
                scaled_cell_size = board_size / self.board.size
                y = scaled_cell_size / 2.0
                for row in range(self.board.size):
                    x = scaled_cell_size / 2.0
                    for col in range(self.board.size):
                        point_rect = pygame.Rect(x, y, 1, 1)
                        pygame.draw.rect(self.screen, self.point_color, point_rect)
                        x += scaled_cell_size
                    y += scaled_cell_size

        # draw agent's neural network
        agent = None
        if self.board:
            if len(self.board.agents) > 0:
                agent = self.board.agents[0]
        if agent:
            self.net_window.set_net(agent.net)

        self.ui_manager.draw_ui(self.screen)
        pygame.display.update()


class Agent(basis.Entity):
    def __init__(self):
        super().__init__()
        self.board = None
        self._position = [0, 0]

        # neural net
        self.net = Net()
        layer1 = self.net.new_layer("in", 8)
        layer2 = self.net.new_layer("mid", 4)
        layer3 = self.net.new_layer("out", 2)
        layer1.connect(layer2)
        layer2.connect(layer3)

    def set_board(self, board):
        self.board = board
        self.board.add_agent(self)

    @property
    def position(self):
        return self._position

    def step(self):
        if not self.board:
            return

        self.position[0] += random.choice([-1, 0, 1])
        self.position[0] = max(0, self.position[0])
        self.position[0] = min(self.position[0], self.board.size - 1)
        self.position[1] += random.choice([-1, 0, 1])
        self.position[1] = max(0, self.position[1])
        self.position[1] = min(self.position[1], self.board.size - 1)

