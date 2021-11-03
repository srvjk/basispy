import basis
import net
import sys
import random
from enum import Enum
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl
import glm
import graphics_opengl as gogl


class AgentAction(Enum):
    NoAction = 0,
    MoveForward = 1,
    TurnLeft = 2,
    TurnRight = 3


class Obstacle(basis.Entity):
    def __init__(self):
        super().__init__()
        self.position = glm.vec2(0, 0)


class Agent(basis.Entity):
    def __init__(self):
        super().__init__()
        self.board = None
        self.position = glm.vec2(0, 0)
        self.orientation = glm.vec2(1, 0)

        # neural net
        self.net = self.new(net.Net)
        layer1 = self.net.new_layer("in", 8, net.Sensor)
        layer2 = self.net.new_layer("mid", 4, net.Neuron)
        layer3 = self.net.new_layer("out", 2, net.Neuron)
        layer1.connect(layer2)
        layer2.connect(layer3)
        self.system.activate(self.net)

    def set_board(self, board):
        self.board = board
        self.board.add_agent(self)

    def step(self):
        if not self.board:
            return

        '''
        front_sensor_color = self.board.get_cell_color(
            self.position[0] + self.orientation[0], self.position[1] + self.orientation[1])
        sensor_active = False
        if front_sensor_color != self.board.back_color and front_sensor_color != self.board.color_no_color:
            sensor_active = True
        self.net.layers[0].neurons[0].set_activity(sensor_active)
        '''

        choice = random.choice(list(AgentAction))
        if choice == AgentAction.NoAction:
            pass
        if choice == AgentAction.MoveForward:
            self.position += self.orientation
            self.position.x = max(0, self.position.x)
            self.position.x = min(self.position.x, self.board.size - 1)
            self.position.y = max(0, self.position.y)
            self.position.y = min(self.position.y, self.board.size - 1)
        if choice == AgentAction.TurnLeft:
            self.orientation = glm.rotate(self.orientation, glm.pi() / 2.0)
        if choice == AgentAction.TurnRight:
            self.orientation = glm.rotate(self.orientation, -glm.pi() / 2.0)


def angle(vec1, vec2):
    """
    Вычислить ориентированный угол (в радианах) между двумя векторами.
    Положительное направление вращения - против часовой стрелки от vec1 к vec2.
    """
    sign = 1.0
    len_1_len_2 = glm.length(vec1) * glm.length(vec2)
    dot = glm.dot(vec1, vec2)

    epsilon = 1e-6
    if abs(dot) < epsilon:
        pseudo_dot = vec1.x * vec2.y - vec2.x * vec1.y
        sin_alpha = pseudo_dot / len_1_len_2
        if sin_alpha < 0:
            sign = -1.0

    ang = glm.acos(dot / len_1_len_2)
    double_pi = glm.pi() * 2.0
    n = glm.floor(ang / double_pi)
    if n > 0:
        ang -= n * double_pi

    return sign * ang


class Board(basis.Entity):
    def __init__(self):
        super().__init__()
        self.agents = list()
        self.obstacles = list()
        self.size = 100
        self.cell_size = 3
        #self.visual_field = pygame.Surface((self.size_in_pixels(), self.size_in_pixels()))
        #self.compressed_visual_field = pygame.Surface((self.size, self.size))  # поле, сжатое до 1 пиксела на клетку
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
            obstacle.position = glm.vec2(x, y)
            self.obstacles.append(obstacle)

    def get_cell_color(self, x, y):
        if x < 0 or x >= self.size or y < 0 or y >= self.size:
            return self.color_no_color
        return self.compressed_visual_field.get_at((x, y))

    def draw(self, renderer, pos, size):
        x0 = pos[0]
        y0 = pos[1]
        width = size[0]
        height = size[1]
        cell_width = width / self.size
        cell_height = height / self.size

        polygon = gogl.Polygon(gogl.resource_manager.get_shader("polygon"))
        polygon.set_points([
            glm.vec2(0.0, 0.0),
            glm.vec2(1.0, 0.0),
            glm.vec2(1.0, 1.0),
            glm.vec2(0.0, 1.0),
            glm.vec2(0.0, 0.0)
        ])
        polygon.draw(glm.vec2(x0, y0), glm.vec2(width, height), 0.0, glm.vec3(0.1, 0.1, 0.1), True)

        for obstacle in self.obstacles:
            if isinstance(obstacle, Obstacle):
                try:
                    renderer.draw_sprite(gogl.resource_manager.get_texture("obstacle"),
                                         glm.vec2(x0 + obstacle.position.x * cell_width,
                                                  y0 + obstacle.position.y * cell_height),
                                         glm.vec2(cell_width, cell_height), 0.0, glm.vec3(1.0))
                except AttributeError:
                    pass

        for agent in self.agents:
            if isinstance(agent, Agent):
                try:
                    ang = angle(glm.vec2(1, 0), agent.orientation)
                    renderer.draw_sprite(gogl.resource_manager.get_texture("agent"),
                                         glm.vec2(x0 + agent.position.x * cell_width,
                                                  y0 + agent.position.y * cell_height),
                                         glm.vec2(cell_width, cell_height), glm.degrees(ang), glm.vec3(1.0))
                except AttributeError:
                    pass

        # после всей отрисовки создаём вспомогательное сжатое представление доски:
        #pygame.transform.scale(self.visual_field, (self.size, self.size), self.compressed_visual_field)

        for agent in self.agents:
            if isinstance(agent, Agent):
                agent_center = glm.vec2(x0 + agent.position.x * cell_width + 0.5 * cell_width,
                                        y0 + agent.position.y * cell_height + 0.5 * cell_height)
                polygon = gogl.Polygon(gogl.resource_manager.get_shader("polygon"))
                polygon.set_points([
                    glm.vec2(0.0, 0.0),
                    agent.orientation
                ])
                polygon.draw(agent_center, glm.vec2(cell_width, cell_width), 0.0, glm.vec3(1.0, 1.0, 0.5), False)
                # polygon.set_points([
                #     glm.vec2(0.0, 0.0),
                #     glm.vec2(1.0, 1.0)
                # ])
                # polygon.draw(glm.vec2(x0, y0), glm.vec2(width, height), 0.0, glm.vec3(0.5, 0.5, 0.5), False)

'''

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
        self.show_net_view = True
        self.delay = 0.5
        self.clock = pygame.time.Clock()
        self.toggle_grid_button = None
        self.recreate_ui()

        # pgu initialization
        self.pgu_app = gui.App()
        gen_ctrl = GeneralControl()
        self.container = gui.Container(align=1, valign=-1)
        self.container.add(gen_ctrl, 0, 0)

        gen_ctrl.grid_btn.connect(gui.CLICK, self.toggle_grid)
        gen_ctrl.net_view_button.connect(gui.CLICK, self.toggle_net_view)
        gen_ctrl.info_view_button.connect(gui.CLICK, self.toggle_info_view)

        self.net_view = None
        self.info_view = None

        self.pgu_app.init(self.container)

    def recreate_ui(self):
        self.background_surface = pygame.Surface(self.screen.get_size()).convert()
        self.background_surface.fill(self.bk_color)

    def set_board(self, board):
        self.board = board

    def toggle_grid(self):
        self.show_grid = not self.show_grid

    def toggle_net_view(self):
        if self.net_view:
            self.container.remove(self.net_view)
            self.net_view = None
        else:
            self.net_view = NetView(width=320, height=240)
            self.container.add(self.net_view, 200, 200)
        self.container.repaint()

    def toggle_info_view(self):
        if self.info_view:
            self.container.remove(self.info_view)
            self.info_view = None
        else:
            self.info_view = InfoView(width=320, height=240)
            self.container.add(self.info_view, 200, 500)
        self.container.repaint()

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
                pass
            else:
                self.pgu_app.event(event)

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

        self.pgu_app.paint()
        pygame.display.update()
'''


def unit_test():
    a1 = angle(glm.vec2(1.0, 0.0), glm.vec2(0.0, 1.0))
    a2 = angle(glm.vec2(1.0, 0.0), glm.vec2(-1.0, 0.0))
    a3 = angle(glm.vec2(1.0, 0.0), glm.vec2(0.0, -1.0))

    return True


if __name__ == "__main__":
    res = unit_test()
    if res:
        print("cells.py: test ok")
    else:
        print("cells.py: test FAILED")


