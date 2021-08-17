import basis
import sys
import random
from enum import Enum
import pygame
import pygame_gui
from pygame_gui.elements.ui_window import UIWindow
from pygame_gui.elements.ui_image import UIImage


class Link:
    def __init__(self):
        self.weight = 0
        self.src_neuron = None
        self.dst_neuron = None
        self.weight = 1.0  # вес связи без учета её знака
        self.sign = 1  # знак связи (+1 для возбуждающих и -1 для тормозящих связей)


class Neuron:
    def __init__(self):
        self.out_links = list()
        self.pos = [0, 0]
        self.state = 0
        self.pre_mediator_quantity = 0
        self.post_mediator_quantity = 0
        self.firing_mediator_threshold = 1.0  # порог количества медиатора, необходимый для срабатывания
        self.out_mediator_quantum = 0.1  # количество нейромедиатора, которое будет отправлено нейронам-получателям

    def set_state(self, state):
        self.state = state

    def add_mediator(self, mediator_quantity):
        self.pre_mediator_quantity += mediator_quantity

    def fire(self):
        """
        Рабочая функция нейрона - выстрел потенциала действия

        Раздаёт медиатор по всем исходящим связям с учетом их весов и полярностей.
        Кол-во медиатора фиксировано для данного нейрона, но при передаче умножается на вес и полярность связи,
        так что разные постсинаптические нейроны получат разное итоговое кол-во медиатора.
        """
        if self.mediator_quantity > self.firing_mediator_threshold:
            for link in self.out_links:
                link.dst_neuron.add_mediator(self.out_mediator_quantum * link.weight * link.sign)

    def swap_mediator_buffers(self):
        self.post_mediator_quantity = self.pre_mediator_quantity
        self.pre_mediator_quantity = 0

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

    def step(self):
        # фаза 1: пройтись во всем нейронам и активировать, какие надо
        # порядок обхода не имеет значения
        for layer in self.layers:
            for neuron in layer.neurons:
                neuron.fire()

        # фаза 2: поменять местами буферы накопления активности для следующей итерации
        for layer in self.layers:
            for neuron in layer.neurons:
                neuron.swap_mediator_buffers()


class AgentAction(Enum):
    NoAction = 0,
    MoveForward = 1,
    TurnLeft = 2,
    TurnRight = 3


class Obstacle(basis.Entity):
    def __init__(self):
        super().__init__()
        self._position = [0, 0]

    @property
    def position(self):
        return self._position

    def set_position(self, x, y):
        self._position = [x, y]


class Agent(basis.Entity):
    def __init__(self):
        super().__init__()
        self.board = None
        self._position = [0, 0]
        self._orientation = [1, 0]

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

    @property
    def orientation(self):
        return self._orientation

    def step(self):
        if not self.board:
            return

        front_sensor_color = self.board.get_cell_color(
            self.position[0] + self.orientation[0], self.position[1] + self.orientation[1])
        sensor_state = 0
        if front_sensor_color != self.board.back_color and front_sensor_color != self.board.color_no_color:
            sensor_state = 1
        self.net.layers[0].neurons[0].set_state(sensor_state)

        choice = random.choice(list(AgentAction))
        if choice == AgentAction.NoAction:
            pass
        if choice == AgentAction.MoveForward:
            self.position[0] += self.orientation[0]
            self.position[1] += self.orientation[1]
            self.position[0] = max(0, self.position[0])
            self.position[0] = min(self.position[0], self.board.size - 1)
            self.position[1] = max(0, self.position[1])
            self.position[1] = min(self.position[1], self.board.size - 1)
        if choice == AgentAction.TurnLeft:
            dir_x, dir_y = self._orientation
            self.orientation[0] = dir_y
            self.orientation[1] = -dir_x
        if choice == AgentAction.TurnRight:
            dir_x, dir_y = self._orientation
            self.orientation[0] = -dir_y
            self.orientation[1] = dir_x


class Board(basis.Entity):
    def __init__(self):
        super().__init__()
        self.agents = list()
        self.obstacles = list()
        self.size = 100
        self.cell_size = 3
        self.visual_field = pygame.Surface((self.size_in_pixels(), self.size_in_pixels()))
        self.compressed_visual_field = pygame.Surface((self.size, self.size))  # поле, сжатое до 1 пиксела на клетку
        self.back_color = (10, 10, 10)
        self.color_no_color = (0, 0, 0)  # цвет для обозначения пространства за пределами поля и т.п.

    def size_in_cells(self):
        return self.size

    def size_in_pixels(self):
        return self.size * self.cell_size

    def add_agent(self, agent):
        self.agents.append(agent)

    def create_obstacles(self, density):
        num_cells = self.size * self.size
        num_obstacles = int(num_cells * density)
        for i in range(num_obstacles):
            x = random.randrange(0, self.size)
            y = random.randrange(0, self.size)
            obstacle = Obstacle()
            obstacle.set_position(x, y)
            self.obstacles.append(obstacle)

    def get_cell_color(self, x, y):
        if x < 0 or x >= self.size or y < 0 or y >= self.size:
            return self.color_no_color
        return self.compressed_visual_field.get_at((x, y))

    def draw(self):
        self.visual_field.fill(self.back_color)

        for obstacle in self.obstacles:
            if isinstance(obstacle, Obstacle):
                try:
                    obst_pos = obstacle.position
                    obst_rect = pygame.Rect(obst_pos[0] * self.cell_size, obst_pos[1] * self.cell_size,
                                            self.cell_size, self.cell_size)
                    pygame.draw.rect(self.visual_field, (50, 50, 50), obst_rect)
                except AttributeError:
                    pass

        for agent in self.agents:
            if isinstance(agent, Agent):
                try:
                    agent_pos = agent.position
                    agent_rect = pygame.Rect(agent_pos[0] * self.cell_size, agent_pos[1] * self.cell_size,
                                             self.cell_size, self.cell_size)
                    pygame.draw.rect(self.visual_field, (100, 0, 0), agent_rect)
                except AttributeError:
                    pass

        # после всей отрисовки создаём вспомогательное сжатое представление доски:
        pygame.transform.scale(self.visual_field, (self.size, self.size), self.compressed_visual_field)


class NetView(UIWindow):
    def __init__(self, net, position, ui_manager):
        super().__init__(pygame.Rect(position, (320, 240)), ui_manager, window_display_title='Neural Net',
                         object_id='#neural_net')
        self.net = net
        surface_size = self.get_container().get_size()
        self.size = surface_size
        self.surface_element = UIImage(pygame.Rect((0, 0), surface_size), pygame.Surface(surface_size).convert(),
                                       manager=ui_manager, container=self, parent_element=self)
        self.inactive_neuron_color = (50, 50, 50)
        self.active_neuron_color = (200, 200, 0)

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
                neuron_color = self.active_neuron_color if neuron.state == 1 else self.inactive_neuron_color
                pygame.draw.circle(self.surface_element.image, neuron_color, neuron.pos, radius)
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
        self.info_color = (255, 255, 100)
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
            scaled_cell_size = board_size / self.board.size

            self.board.draw()
            scaled_visual_field = pygame.transform.scale(self.board.visual_field, (board_size, board_size))
            self.screen.blit(scaled_visual_field, (0, 0))

            # self.screen.blit(self.board.compressed_visual_field, (board_size, 0))

            if self.show_grid:
                y = scaled_cell_size / 2.0
                for row in range(self.board.size):
                    x = scaled_cell_size / 2.0
                    for col in range(self.board.size):
                        point_rect = pygame.Rect(x, y, 1, 1)
                        pygame.draw.rect(self.screen, self.point_color, point_rect)
                        x += scaled_cell_size
                    y += scaled_cell_size

            agent = None
            if len(self.board.agents) > 0:
                agent = self.board.agents[0]
            if agent:
                p1 = (agent.position[0] * scaled_cell_size + scaled_cell_size / 2.0,
                      agent.position[1] * scaled_cell_size + scaled_cell_size / 2.0)
                p2 = (p1[0] + agent.orientation[0] * scaled_cell_size,
                      p1[1] + agent.orientation[1] * scaled_cell_size)
                pygame.draw.line(self.screen, self.info_color, p1, p2, 1)

                # draw agent's neural network
                self.net_window.set_net(agent.net)

        self.ui_manager.draw_ui(self.screen)
        pygame.display.update()



