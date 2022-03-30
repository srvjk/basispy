import basis
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
    def __init__(self, system):
        super().__init__(system)
        self.position = glm.vec2(0, 0)


class Boredom(basis.Entity):
    """
    "Скука" - сущность, появляющаяся у агента в состоянии бездействия и побуждающая его что-то делать.
    """
    def __init__(self, system):
        super().__init__(system)


class Frame(basis.Entity):
    """
    Кадр - основой структурный элемент памяти агента.
    """
    def __init__(self, system):
        super().__init__(system)
        self.ent_class_names = list()

    def make_trace_of(self, frame):
        """
        Создать в данном кадре 'след' другого кадра (в простейшем случае - запомнить имена классов сущностей)
        :param frame:
        :return:
        """
        for ent in frame.entities:
            self.ent_class_names.append(type(ent).__name__)


class FrameSequence(basis.Entity):
    """
    Последовательность кадров.
    """
    def __init__(self, system):
        super().__init__(system)
        self.max_capacity = 3
        self.frames = list()

    def size(self):
        return len(self.frames)

    def new_frame(self):
        """
        Добавить новый кадр. Если кадров слишком много, самый старый будет удалён.
        :return: только что созданный кадр
        """
        frame = self.add_new(Frame)
        self.frames.insert(0, frame)  # в начало
        if len(self.frames) > self.max_capacity:
            self.frames.pop()

        return frame

    def most_recent_frame(self):
        """
        Получить самый свежий кадр (последний добавленный).
        :return:
        """
        if self.frames:
            return self.frames[0]

        return None


class Agent(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.board = None
        self.position = glm.vec2(0, 0)
        self.orientation = glm.vec2(1, 0)
        self.short_memory = self.add_new(FrameSequence) # кратковременная память - последовательность кадров
        self.short_memory.max_capacity = 100
        self.long_memory = list()  # долговременная память - набор последовательностей кадров
        self.long_memory_capacity = 10  # ёмкость долговременной памяти (кол-во хранимых последовательностей кадров)
        self.current_frame = self.add_new(Frame)  # текущий (рабочий) кадр

    def set_board(self, board):
        self.board = board
        self.board.add_agent(self)

    def compare_frames(self, first, second):
        """
        Сравнить два кадра и вернуть степень подобия по 100-балльной шкале
        :param first:
        :param second:
        :return:
        """
        return 0

    def find_best_association(self, frame):
        """
        Найти наилучшую ассоциацию для данного кадра.
        :param frame:
        :return:
        """
        best_score = 0
        best_seq = None
        for seq in self.long_memory:
            if not seq:
                continue
            start_frame = seq[0]
            score = self.compare_frames(frame, start_frame)
            if score > best_score:
                best_seq = seq
                best_score = score

        return best_seq

    def short_to_long_memory(self):
        """
        Перенести содержимое оперативной памяти в долговременную.
        :return:
        """
        self.long_memory.insert(0, self.short_memory)
        if len(self.long_memory) > self.long_memory_capacity:
            self.long_memory.pop()

    def do_step(self):
        x_ahead = int(self.position[0] + self.orientation[0])
        y_ahead = int(self.position[1] + self.orientation[1])

        obstacle_sensor_active = False
        if self.board.is_obstacle(x_ahead, y_ahead):
            obstacle_sensor_active = True
        #self.net.layers[0].neurons[0].set_activity(obstacle_sensor_active)

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

    def step(self):
        if not self.board:
            return

        # создаем новый кадр в памяти
        prev_frame = self.short_memory.new_frame()
        # создаем в только что созданном кадре "следы" сущностей из текущего кадра
        prev_frame.make_trace_of(self.current_frame)

        if self.current_frame.is_empty():
            boredom = self.current_frame.add_new(Boredom)
            if boredom:
                self.current_frame.activate(boredom)

        boredom = basis.first_of(self.current_frame.get_entities_by_type(Boredom))
        if boredom:
            self.do_step()
            boredom.self_delete()

        # запомнить недавнюю последовательность кадров
        #self.short_to_long_memory()

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


class BoardCell:
    def __init__(self):
        self.objects = []


class Board(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.agents = list()
        self.obstacles = list()
        self.size = 100
        self.cell_size = 3
        #self.visual_field = pygame.Surface((self.size_in_pixels(), self.size_in_pixels()))
        #self.compressed_visual_field = pygame.Surface((self.size, self.size))  # поле, сжатое до 1 пиксела на клетку
        self.back_color = (10, 10, 10)
        self.color_no_color = (0, 0, 0)  # цвет для обозначения пространства за пределами поля и т.п.

        # инициализируем двумерный массив ячеек доски
        self.cells = []
        for y in range(self.size):
            row = []
            for x in range(self.size):
                row.append(BoardCell())
            self.cells.append(row)

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
            obstacle = self.add_new(Obstacle)
            obstacle.position = glm.vec2(x, y)
            self.obstacles.append(obstacle)
            self.cells[y][x].objects.append(obstacle)  # добавляем объект в матрицу ячеек доски

    def get_cell_color(self, x, y):
        if x < 0 or x >= self.size or y < 0 or y >= self.size:
            return self.color_no_color
        return self.compressed_visual_field.get_at((x, y))

    def is_obstacle(self, x, y):
        cell = self.cells[y][x]
        for obj in cell.objects:
            if isinstance(obj, Obstacle):
                return True
        return False

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


