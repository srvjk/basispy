import basis
import sys
import random
from enum import Enum
import glm
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


class Symbol:
    """
    Абстрактный символ.
    """
    def __init__(self):
        pass

class Actor:
    """
    Деятель - сущность, которая может быть активирована и может выполнить какое-либо действие.
    """
    min_rating = -100
    max_rating = 100

    def __init__(self):
        self.rating = 0

    def modify_rating(self, d):
        tmp = self.rating + d
        if Actor.min_rating <= tmp <= Actor.max_rating:
            self.rating = tmp
        elif tmp < Actor.min_rating:
            self.rating = Actor.min_rating
        elif tmp > Actor.max_rating:
            self.rating = Actor.max_rating


class ObstacleAhead(basis.Entity):
    """
    Событие 'впереди препятствие'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.symbol = self.new_facet(Symbol)


class ObstacleCollision(basis.Entity):
    """
    Событие 'столкновения' c препятствием.
    """
    def __init__(self, system):
        super().__init__(system)
        self.symbol = self.new_facet(Symbol)


class ObstacleSensor(basis.Entity):
    """
    Датчик препятствия на следующей клетке прямо по курсу.
    """
    def __init__(self, system):
        super().__init__(system)
        self.actor = self.new_facet(Actor)

    def step(self):
        board = basis.first_of(self.system.get_entities_by_type(Board))
        if not board:
            return
        agent = basis.first_of(board.get_entities_by_type(Agent))
        if not agent:
            return
        x_ahead, y_ahead = board.normalized_coordinates(
            *((agent.position + agent.orientation).to_tuple())
        )
        is_obstacle = board.is_obstacle(x_ahead, y_ahead)
        if not is_obstacle:
            return
        s = agent.memory.add_new(ObstacleAhead)
        agent.memory.put_symbol(s)


class CollisionSensor(basis.Entity):
    """
    Датчик столкновения с препятствием.
    """
    def __init__(self, system):
        super().__init__(system)
        self.actor = self.new_facet(Actor)

    def step(self):
        board = basis.first_of(self.system.get_entities_by_type(Board))
        if not board:
            return
        agent = basis.first_of(board.get_entities_by_type(Agent))
        if not agent:
            return
        x, y = agent.position.to_tuple()
        is_obstacle = board.is_obstacle(x, y)
        if not is_obstacle:
            return
        s = agent.memory.add_new(ObstacleCollision)
        agent.memory.put_symbol(s)


class Analyzer(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.actor = self.new_facet(Actor)

    def step(self):
        #TODO надо упростить процедуры поиска сущностей, доступа к граням, а также родителям, сиблингам и т.п.
        board = basis.first_of(self.system.get_entities_by_type(Board))
        if not board:
            return
        agent = basis.first_of(board.get_entities_by_type(Agent))
        if not agent:
            return
        collision = basis.first_of(agent.memory.get_symbols_by_type(ObstacleCollision))
        if collision:  # наскочили на препятствие, т.е. стоим на одной клетке с ним
            idle = basis.first_of(agent.get_entities_by_type(StayIdleAction))
            if idle:
                actor = idle.get_facet(Actor)
                actor.modify_rating(-100)

        fwd = basis.first_of(agent.get_entities_by_type(MoveForwardAction))
        left = basis.first_of(agent.get_entities_by_type(TurnLeftAction))
        #right = basis.first_of(agent.get_entities_by_type(TurnRightAction))

        obst_ahd = basis.first_of(agent.memory.get_symbols_by_type(ObstacleAhead))
        if not obst_ahd:  # впереди нет препятствия - двигаемся вперед
            fwd.actor.modify_rating(100)
            left.actor.modify_rating(-20)
        else:  # впереди препятствие - выбираем другие варианты действий
            fwd.actor.modify_rating(-100)
            left.actor.modify_rating(50)


class Action:
    """
    Абстрактное действие.
    """
    def __init__(self):
        self.object = None  # объект действия


class StayIdleAction(basis.Entity):
    """
    Действие 'стоять на месте'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = self.new_facet(Action)
        self.actor = self.new_facet(Actor)


class MoveForwardAction(basis.Entity):
    """
    Действие 'двигаться вперёд'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = self.new_facet(Action)
        self.actor = self.new_facet(Actor)

    def step(self):
        if not super().step():
            return False

        obj = self.action.object
        if not obj:
            return False

        obj.position = glm.ivec2(
            obj.board.normalized_coordinates(
                *((obj.position + obj.orientation).to_tuple()),
            )
        )

        self.system.logger.debug("Moving forward at step {}".format(self.system.get_global_step_counter()))

        return True


class TurnLeftAction(basis.Entity):
    """
    Действие 'повернуть влево на 90 градусов'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = self.new_facet(Action)
        self.actor = self.new_facet(Actor)

    def step(self):
        if not super().step():
            return False

        obj = self.action.object
        if not obj:
            return False

        vr = glm.rotate(glm.vec2(obj.orientation), glm.pi() / 2.0)
        obj.orientation = glm.ivec2(round(vr.x), round(vr.y))

        self.system.logger.debug("Turning left")

        return True


class TurnRightAction(basis.Entity):
    """
    Действие 'повернуть вправо на 90 градусов'.
    """
    def __init__(self, system):
        super().__init__(system)
        self.action = self.new_facet(Action)
        self.actor = self.new_facet(Actor)

    def step(self):
        if not super().step():
            return False

        obj = self.action.object
        if not obj:
            return False

        vr = glm.rotate(glm.vec2(obj.orientation), -glm.pi() / 2.0)
        obj.orientation = glm.ivec2(round(vr.x), round(vr.y))

        self.system.logger.debug("Turning right")

        return True


class MemoryBuffer(basis.Entity):
    """
    Буфер - контейнер для храниния символов в памяти.
    """
    def __init__(self, system):
        super().__init__(system)
        self.symbols = list()  # символы, хранимые в буфере

    def clear(self):
        self.symbols.clear()

    def count(self):
        return len(self.symbols)


class Memory(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.last_step_activity = 0  # уровень активности сущностей-действий на прошлом шаге
        self.front_buffer = self.add_new(MemoryBuffer, "membuf1")  # первичный буфер (для записи на текущем шаге)
        self.back_buffer = self.add_new(MemoryBuffer, "membuf2")  # задний буфер (для чтения инф. с прошлого шага)
        self.logger = logging.getLogger("lambert")
        self.logger.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(stream_handler)

    def put_symbol(self, symbol):
        """
        Поместить символ в рабочую память.
        :param symbol:
        :return:
        """
        self.front_buffer.symbols.append(symbol)

    def get_symbols_by_type(self, type_name):
        """
        Найти во вторичном буфере все символы заданного типа
        :param type_name:
        :return:
        """
        result = list()
        for s in self.back_buffer.symbols:
            if isinstance(s, type_name):
                result.append(s)

        return result

    def swap_buffers(self):
        """
        Переключить буферы, очистить новый первичный буфер.
        :return:
        """
        self.logger.debug(">>> step {}".format(self.system.get_global_step_counter()))
        self.logger.debug("before buf swap; front: {} ({}), back: {} ({})".format(
            self.front_buffer.name, self.front_buffer.count(),
            self.back_buffer.name, self.back_buffer.count())
        )

        self.front_buffer, self.back_buffer = self.back_buffer, self.front_buffer
        self.front_buffer.clear()

        self.logger.debug("after buf swap; front: {} ({}), back: {} ({})".format(
            self.front_buffer.name, self.front_buffer.count(),
            self.back_buffer.name, self.back_buffer.count())
        )

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
        self.message = None  # диагностическое сообщение (если есть)
        self.logger = logging.getLogger("lambert")
        self.logger.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(stream_handler)
        self.min_actor_rating = -100
        self.max_actor_rating = 100

    def create(self, source=None):
        super().create(source)

        self.add_new(ObstacleSensor, "ObstacleSensor")
        self.add_new(CollisionSensor, "CollisionSensor")
        analyzer = self.add_new(Analyzer, "Analyzer")
        analyzer.actor.rating = 100

        idl = self.add_new(StayIdleAction, "IdleAction")
        idl.actor.rating = 50

        lft = self.add_new(TurnLeftAction, "TurnLeftAction")
        lft.action.object = self
        lft.actor.rating = 50

        fwd = self.add_new(MoveForwardAction, "MoveForwardAction")
        fwd.action.object = self
        fwd.actor.rating = 50

    def set_board(self, board):
        self.board = board
        self.board.add_agent(self)

    def do_step(self):
        for ent in self.entities:
            actor = ent.get_facet(Actor)
            if actor:
                v = random.random() * self.max_actor_rating
                if v > actor.rating:
                    ent.step()

        self.memory.swap_buffers()

    def step(self):
        if not super().step():
            return False

        self.message = None

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


