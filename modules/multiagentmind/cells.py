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
from collections.abc import Sequence


class AgentAction(Enum):
    NoAction = 0,
    MoveForward = 1,
    TurnLeft = 2,
    TurnRight = 3


class Obstacle(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.position = glm.ivec2(0, 0)


class Link:
    """
    Межнейронная связь.
    """
    def __init__(self):
        self.src_id = None   # идентификатор нейрона-источника
        self.dst_id = None   # идентификатор нейрона-приёмника
        self.active = False  # флаг активности пресинаптического нейрона
        self.strength = 0    # сила связи
        self.polarity = 0    # полярность связи ( > 0 для возбуждающих связей, < 0 для тормозящих )


class NamedMutableSequence(Sequence):
    __slots__ = ()

    def __init__(self, *a, **kw):
        slots = self.__slots__
        for k in slots:
            setattr(self, k, kw.get(k))

        if a:
            for k, v in zip(slots, a):
                setattr(self, k, v)

    def __str__(self):
        cls_name = self.__class__.__name__
        values = ', '.join('%s=%r' % (k, getattr(self, k))
                           for k in self.__slots__)
        return '%s(%s)' % (cls_name, values)

    __repr__ = __str__

    def __getitem__(self, item):
        return getattr(self, self.__slots__[item])

    def __setitem__(self, item, value):
        return setattr(self, self.__slots__[item], value)

    def __len__(self):
        return len(self.__slots__)


class Point(NamedMutableSequence):
    __slots__ = ('x', 'y', 'z')


class Neuron:
    """
    Нейрон.
    """
    def __init__(self):
        self.input = 0.0  # входной буфер (накапливает значение активности)
        self.output = 0   # выходной буфер (содержит выходное значение активности)
        self.threshold = 1.0  # порог активации
        self.position = Point(0.0, 0.0, 0.0)  # координаты нейрона в нейросети
        self.size = Point(30.0, 30.0, 0.0)    # отображаемые размеры нейрона

    def is_active(self) -> bool:
        return self.output > 0

    def do_activation(self, memory):
        """
        Активация нейрона.
        :param memory: ссылка на память - контейнер, содержащий другие нейроны (для работы со связями)
        :return:
        """
        if self.is_active():
            self.input = 0

        rand_range = 1000
        rand_ridge = 10
        if self.input > self.threshold:
            rand_ridge = 800

        r = random.randint(0, rand_range)
        if r < rand_ridge:
            self.output = 1
        else:
            self.output = 0

    def set_input_active(self):
        """ Принудительная активация нейрона по входу через установку входного значения выше порога """
        self.input = self.threshold * 1.1


class ObstacleAhead(basis.Entity):
    """
    Событие 'впереди препятствие'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.neuron = self.new_facet(Neuron)


class ObstacleCollision(basis.Entity):
    """
    Событие 'столкновения' c препятствием.
    """
    def __init__(self, system):
        super().__init__(system)
        self.neuron = self.new_facet(Neuron)


class Action:
    """
    Абстрактное действие.
    """
    def __init__(self):
        self.object = None    # объект действия


class StayIdleAction(basis.Entity):
    """
    Действие 'стоять на месте'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = self.new_facet(Action)
        self.neuron = self.new_facet(Neuron)


class Fidget(basis.Entity):
    """
    "Непоседа" - сущность, активирующаяся у агента при длительном простое и побуждающая его к действиям.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = self.new_facet(Action)
        self.neuron = self.new_facet(Neuron)
        self.no_activity_steps = 0  # счетчик шагов без какой-либо активности вокруг
        self.activity_steps = 0  # счетчик шагов с активностью этого нейрона
        self.activity_steps_threshold = 100
        self.no_activity_steps_threshold = 20

    def step(self):
        if not super().step():
            return False

        obj = self.action.object
        if not obj:
            return False

        # Fidget активируется, если за последние несколько шагов активность сущностей-действий в памяти была
        # ниже некоторого порогового уровня
        memory = self.container
        if memory.last_step_activity > 1:  # 1, а не 0, чтобы учесть активность самого Fidget'a
            self.no_activity_steps = 0
        else:
            self.no_activity_steps += 1

        if self.neuron.is_active():
            self.activity_steps += 1

        # если Fidget уже достаточно долго активен, его надо погасить
        if self.activity_steps > self.activity_steps_threshold:
            self.neuron.input = 0
            self.activity_steps = 0

        if self.no_activity_steps > self.no_activity_steps_threshold:
            self.neuron.input = self.neuron.threshold + 1  # для безусловной активации
            self.no_activity_steps = 0

        return True


class MoveForwardAction(basis.Entity):
    """
    Действие 'двигаться вперёд'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = self.new_facet(Action)
        self.neuron = self.new_facet(Neuron)

    def step(self):
        if not super().step():
            return False

        if not self.neuron.is_active():
            return False

        obj = self.action.object
        if not obj:
            return False

        obj.position = glm.ivec2(
            obj.board.normalized_coordinates(
                *((obj.position + obj.orientation).to_tuple()),
            )
        )

        return True


class TurnLeftAction(basis.Entity):
    """
    Действие 'повернуть влево на 90 градусов'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = self.new_facet(Action)
        self.neuron = self.new_facet(Neuron)

    def step(self):
        if not super().step():
            return False

        if not self.neuron.is_active():
            return False

        obj = self.action.object
        if not obj:
            return False

        vr = glm.rotate(glm.vec2(obj.orientation), glm.pi() / 2.0)
        obj.orientation = glm.ivec2(round(vr.x), round(vr.y))

        return True


class TurnRightAction(basis.Entity):
    """
    Действие 'повернуть вправо на 90 градусов'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = self.new_facet(Action)
        self.neuron = self.new_facet(Neuron)

    def step(self):
        if not super().step():
            return False

        if not self.neuron.is_active():
            return False

        obj = self.action.object
        if not obj:
            return False

        vr = glm.rotate(glm.vec2(obj.orientation), -glm.pi() / 2.0)
        obj.orientation = glm.ivec2(round(vr.x), round(vr.y))

        return True


class Memory(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.links = dict()
        self.last_step_activity = 0  # уровень активности сущностей-действий на прошлом шаге

    def new_link(self, src_id, dst_id):
        """
        Создать новую межнейронную связь.
        :param src_id: идентификатор нейрона-источника
        :param dst_id: идентификатор нейрона-приёмника
        :return: новая связь
        """
        lnk = Link()
        lnk.src_id = src_id
        lnk.dst_id = dst_id
        self.links[(src_id, dst_id)] = lnk

        return lnk

    def remove_link(self, link):
        """
        Удалить межнейронную связь.
        :param link:
        :return:
        """
        del self.links[(link.src_id, link.dst_id)]

    def step(self):
        if not super().step():
            return False

        return True


class Agent(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.board = None
        self.position = glm.ivec2(0, 0)
        self.orientation = glm.ivec2(1, 0)
        self.memory = self.add_new(Memory, "Memory")
        self.collision_count = 0  # счетчик столкновений с препятствиями
        self.logger = logging.getLogger("multiagentmind")
        self.logger.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(stream_handler)

    def create(self, source=None):
        super().create(source)

        self.memory.make_active()

        obst_ahead = self.memory.add_new(ObstacleAhead, "ObstacleAheadSensor")
        self.memory.add_new(ObstacleCollision, "ObstacleCollisionSensor")

        lft = self.memory.add_new(TurnLeftAction, "TurnLeftAction")
        lft.action.object = self
        lft.make_active()

        fwd = self.memory.add_new(MoveForwardAction, "MoveForwardAction")
        fwd.action.object = self
        fwd.make_active()

        fgt = self.memory.add_new(Fidget, "Fidget")
        fgt.action.object = self
        fgt.make_active()

        # устанавливаем межнейронные связи
        lnk = self.memory.new_link(fgt.uuid, fwd.uuid)
        lnk.strength = 2.0  # делаем наиболее вероятным движение вперед
        lnk.polarity = 1.0

        lnk = self.memory.new_link(fgt.uuid, lft.uuid)
        lnk.strength = 1.0
        lnk.polarity = 1.0

        lnk = self.memory.new_link(fwd.uuid, lft.uuid)
        lnk.strength = 1.0
        lnk.polarity = -1.0

        lnk = self.memory.new_link(lft.uuid, fwd.uuid)
        lnk.strength = 1.0
        lnk.polarity = -1.0

        lnk = self.memory.new_link(obst_ahead.uuid, fwd.uuid)
        lnk.strength = 2.0
        lnk.polarity = -1.0

        lnk = self.memory.new_link(obst_ahead.uuid, lft.uuid)
        lnk.strength = 2.0
        lnk.polarity = 1.0

        #TODO придумать что-нибудь поумнее, чем случайное размещение
        for ent in self.memory.entities:
            neuron = ent.get_facet(Neuron)
            if neuron:
                neuron.position.x = random.randint(-250, 250)
                neuron.position.y = random.randint(-250, 250)

    def set_board(self, board):
        self.board = board
        self.board.add_agent(self)

    def do_step(self):
        x_ahead, y_ahead = self.board.normalized_coordinates(
            *((self.position + self.orientation).to_tuple())
            )

        # проверка на наличие препятствия прямо по курсу
        ent = basis.first_of(self.memory.get_entities_by_type(ObstacleAhead))
        if ent:
            if self.board.is_obstacle(x_ahead, y_ahead):
                ent.neuron.set_input_active()
                self.logger.debug("obstacle ahead at step {}: ({}, {})".format(self._local_step_counter,
                                                                               x_ahead, y_ahead))

        # проверка на "столкновение" с препятствием (агент и препятствие на одной клетке)
        ent = basis.first_of(self.memory.get_entities_by_type(ObstacleCollision))
        if ent:
            if self.board.is_obstacle(self.position.x, self.position.y):
                ent.neuron.set_input_active()
                self.logger.debug("collision at step {}: ({}, {})".format(self._local_step_counter, self.position.x,
                                                                          self.position.y))
                self.collision_count += 1

        self.memory.last_step_activity = 0

        # ищем в памяти агента сущности-нейроны и активируем их, если нужно
        for e in self.memory.entities.copy():
            neuron = e.get_facet(Neuron)
            if neuron:
                neuron.do_activation(self.memory)

        # обновляем входящие буферы нейронов (для следующей итерации)
        for (key, lnk) in self.memory.links.items():
            src_ent = self.memory.get_entity_by_id(lnk.src_id)
            src_neuron = src_ent.get_facet(Neuron)
            if not src_neuron:
                continue
            dst_ent = self.memory.get_entity_by_id(lnk.dst_id)
            dst_neuron = dst_ent.get_facet(Neuron)
            if not dst_neuron:
                continue
            d = 0
            if src_neuron.is_active():
                d = lnk.strength * lnk.polarity
            dst_neuron.input += d

        # ищем внутри агента сущности с набором граней (Action, Neuron); если они активны как нейроны, выполняем их как
        # действия
        entities = self.memory.get_entities(lambda x: x.has_facet(Action) and x.has_facet(Neuron))
        for e in entities:
            neuron = e.get_facet(Neuron)
            if neuron.is_active():
                e.step()
                self.memory.last_step_activity += 1

    def step(self):
        if not super().step():
            return False

        if not self.board:
            return False

        self.do_step()

        return True


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


def unit_test():
    return True


if __name__ == "__main__":
    res = unit_test()
    if res:
        print("cells.py: test ok")
    else:
        print("cells.py: test FAILED")


