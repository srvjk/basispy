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
import logging


class AgentAction(Enum):
    NoAction = 0,
    MoveForward = 1,
    TurnLeft = 2,
    TurnRight = 3


class Obstacle(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.position = glm.ivec2(0, 0)


class Neuron:
    """
    Нейрон.
    """
    def __init__(self):
        self.active = False

    def do_activation(self):
        self.active = (random.randint(1, 100) > 70)


class Boredom(basis.Entity):
    """
    "Скука" - сущность, появляющаяся у агента в состоянии бездействия и побуждающая его что-то делать.
    """
    def __init__(self, system):
        super().__init__(system)


class ObstacleAhead(basis.Entity):
    """
    Событие 'впереди препятствие'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.neuron = Neuron()


class ObstacleCollision(basis.Entity):
    """
    Событие 'столкновения' c препятствием.
    """
    def __init__(self, system):
        super().__init__(system)
        self.neuron = Neuron()


class Action:
    """
    Абстрактное действие.
    """
    def __init__(self):
        self.is_done = False  # было ли действие уже выполнено
        self.object = None    # объект действия


class StayIdleAction(basis.Entity):
    """
    Действие 'стоять на месте'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = Action()
        self.neuron = Neuron()


class MoveForwardAction(basis.Entity):
    """
    Действие 'двигаться вперёд'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = Action()
        self.neuron = Neuron()

    def step(self):
        super().step()

        obj = self.action.object
        if not obj:
            return

        #obj.position += obj.orientation

        obj.position = glm.ivec2(
            obj.board.normalized_coordinates(
                *((obj.position + obj.orientation).to_tuple()),
            )
        )

        self.action.is_done = True


class TurnLeftAction(basis.Entity):
    """
    Действие 'повернуть влево на 90 градусов'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = Action()
        self.neuron = Neuron()

    def step(self):
        super().step()

        obj = self.action.object
        if not obj:
            return

        vr = glm.rotate(glm.vec2(obj.orientation), glm.pi() / 2.0)
        obj.orientation = glm.ivec2(round(vr.x), round(vr.y))

        self.action.is_done = True


class TurnRightAction(basis.Entity):
    """
    Действие 'повернуть вправо на 90 градусов'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = Action()
        self.neuron = Neuron()

    def step(self):
        super().step()

        obj = self.action.object
        if not obj:
            return

        vr = glm.rotate(glm.vec2(obj.orientation), -glm.pi() / 2.0)
        obj.orientation = glm.ivec2(round(vr.x), round(vr.y))

        self.action.is_done = True


class Memory(basis.Entity):
    def __init__(self, system):
        super().__init__(system)


class Agent(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.board = None
        self.position = glm.ivec2(0, 0)
        self.orientation = glm.ivec2(1, 0)
        self.memory = self.add_new(Memory)
        self.collision_count = 0  # счетчик столкновений с препятствиями
        self.message = None  # диагностическое сообщение (если есть)
        self.logger = logging.getLogger("multiagentmind")
        self.logger.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(stream_handler)

    def create(self, source=None):
        super().create(source)
        self.memory.add_new(ObstacleAhead)
        self.memory.add_new(ObstacleCollision)
        act = self.memory.add_new(StayIdleAction)
        act.action.object = self
        self.memory.activate(act)
        act = self.memory.add_new(TurnLeftAction)
        act.action.object = self
        self.memory.activate(act)
        act = self.memory.add_new(TurnRightAction)
        act.action.object = self
        self.memory.activate(act)
        act = self.memory.add_new(MoveForwardAction)
        act.action.object = self
        self.memory.activate(act)

    def set_board(self, board):
        self.board = board
        self.board.add_agent(self)

    def do_step(self):
        # выполнить действия, запланированные на предыдущем шаге:
        for ent in self.memory.entities.copy():
            action = ent.get_facet(Action)
            if not action:
                continue
            neuron = ent.get_facet(Neuron)
            if not neuron:
                continue
            if neuron.active:
                ent.step()

        x_ahead, y_ahead = self.board.normalized_coordinates(
            *((self.position + self.orientation).to_tuple())
            )

        # проверка на наличие препятствия прямо по курсу
        ent = basis.first_of(self.memory.get_entities_by_type(ObstacleAhead))
        if ent:
            ent.neuron.active = self.board.is_obstacle(x_ahead, y_ahead)
            if ent.neuron.active:
                self.logger.debug("obstacle ahead at step {}: ({}, {})".format(self._local_step_counter,
                                                                               x_ahead, y_ahead))

        # проверка на "столкновение" с препятствием (агент и препятствие на одной клетке)
        ent = basis.first_of(self.memory.get_entities_by_type(ObstacleCollision))
        if ent:
            ent.neuron.active = self.board.is_obstacle(self.position.x, self.position.y)
            if ent.neuron.active:
                self.logger.debug("collision at step {}: ({}, {})".format(self._local_step_counter, self.position.x,
                                                                          self.position.y))

        # ищем в памяти агента сущности-нейроны и активируем их, если нужно
        for e in self.memory.entities:
            neuron = e.get_facet(Neuron)
            if neuron:
                neuron.do_activation()

        # ищем внутри агента сущности с набором граней (Action, Neuron); если они активны как нейроны, выполняем их как
        # действия
        entities = self.memory.get_entities(lambda x: x.has_facet(Action) and x.has_facet(Neuron))
        for e in entities:
            neuron = e.get_facet(Neuron)
            if neuron.active:
                ent.step()


    # def do_step(self):
    #     # выполнить действия, запланированные на предыдущем шаге (шагах), ненужные затем удалить:
    #     for ent in self.memory.entities.copy():
    #         action = ent.get_facet(Action)  #TODO продумать механизм граней (как замену наследованию)
    #         if not action:
    #             continue
    #         ent.step()
    #         if action.is_done:
    #             ent.abolish()
    #
    #     x_ahead, y_ahead = self.board.normalized_coordinates(
    #         *((self.position + self.orientation).to_tuple())
    #         )
    #
    #     # проверка на наличие препятствия прямо по курсу
    #     if self.board.is_obstacle(x_ahead, y_ahead):
    #         self.logger.debug("obstacle ahead at step {}: ({}, {})".format(self._local_step_counter, x_ahead, y_ahead))
    #
    #         if not self.memory.has_one_of(condition=lambda x: basis.short_class_name(x)=='ObstacleAhead'):
    #             self.memory.add_new(ObstacleAhead)
    #     else:
    #         self.memory.abolish_children(condition=lambda x: basis.short_class_name(x)=='ObstacleAhead')
    #
    #     # проверка на "столкновение" с препятствием (агент и препятствие на одной клетке)
    #     if self.board.is_obstacle(self.position.x, self.position.y):
    #         self.collision_count += 1
    #         self.logger.debug("collision at step {}: ({}, {})".format(self._local_step_counter, self.position.x,
    #                                                                   self.position.y))
    #
    #         self.message = "Collision: obstacle at ({}, {})".format(self.position.x, self.position.y)
    #         if not self.memory.has_one_of(condition=lambda x: basis.short_class_name(x) == 'ObstacleCollision'):
    #             self.memory.add_new(ObstacleCollision)
    #     else:
    #         self.memory.abolish_children(condition=lambda x: basis.short_class_name(x) == 'ObstacleCollision')
    #
    #     self.logger.debug("Action for step {}:".format(self._local_step_counter))
    #
    #     choice = random.choice(list(AgentAction))
    #     if choice == AgentAction.NoAction:
    #         self.logger.debug("    no action")
    #         pass
    #     if choice == AgentAction.MoveForward:
    #         self.logger.debug("    move forward")
    #         fwd_act = self.memory.add_new(MoveForwardAction)
    #         fwd_act.action.object = self
    #     if choice == AgentAction.TurnLeft:
    #         self.logger.debug("    turn left")
    #         tl_act = self.memory.add_new(TurnLeftAction)
    #         tl_act.action.object = self
    #     if choice == AgentAction.TurnRight:
    #         self.logger.debug("    turn right")
    #         tr_act = self.memory.add_new(TurnRightAction)
    #         tr_act.action.object = self

    def step(self):
        super().step()

        self.message = None

        if not self.board:
            return

        self.do_step()


def angle(vector1, vector2):
    """
    Вычислить ориентированный угол (в радианах) между двумя векторами.
    Положительное направление вращения - против часовой стрелки от vec1 к vec2.
    """
    vec1 = glm.vec2(vector1)
    vec2 = glm.vec2(vector2)

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
        self.size = 50
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

    def normalized_coordinates(self, x, y):
        x_norm = (x + self.size) % self.size
        y_norm = (y + self.size) % self.size
        return x_norm, y_norm

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
        try:
            cell = self.cells[y][x]
        except IndexError:
            return False

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


