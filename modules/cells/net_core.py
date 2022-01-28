import basis
import random
from rtree import index
from enum import IntEnum


class Link:
    def __init__(self):
        self.weight = 0
        self.src_neuron = None
        self.dst_neuron = None
        self.weight = 1.0  # вес связи без учета её знака
        self.sign = 1  # знак связи (+1 для возбуждающих и -1 для тормозящих связей)


class NeuronState(IntEnum):
    IDLE = 0,
    FIRING = 1


class Neuron(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.out_links = list()
        self.pos = [0, 0, 0]                    # положение нейрона в сети (в большинстве случаев 2D, т.е. pos[2] = 0)
        self.pre_mediator_quantity = 0.0
        self.post_mediator_quantity = 0.0
        self.firing_mediator_threshold = 100.0  # порог количества медиатора, необходимый для срабатывания
        self.out_mediator_quantum = 0.1         # количество медиатора, которое будет отправлено нейронам-получателям
        self.time_prev = -0.1                   # прошлая отметка времени
        self.mediator_decrease_speed = 100.0    # скорость убывания медиатора, ед./сек
        self.idle_potential_level = 0.0         # уровень потенциала покоя, у.е.
        self.action_potential_level = 1.0       # уровень потенциала действия, у.е.
        self.potential = self.idle_potential_level  # текущий уровень потенциала
        self.firing_start_time = 0.0            # время начала импульса
        self.spike_duration = 0.003             # длительность импульса, сек
        self.fires_count = 0                    # количество импульсов за время сеанса работы

    def set_activity(self, activity):
        if activity:
            self.post_mediator_quantity = self.firing_mediator_threshold * 1.01
        else:
            self.post_mediator_quantity = 0.0

    def is_active(self):
        if self.potential >= self.action_potential_level:
            return True
        return False

    def add_mediator(self, mediator_quantity):
        self.pre_mediator_quantity += mediator_quantity

    def operate(self):
        time_now = self.system.model_time_s()
        if self.time_prev < 0:
            self.time_prev = time_now
            return

        time_delta = time_now - self.time_prev

        # прежде всего уменьшаем кол-во медиатора в накопительном буфере, имитируя его рассевание и распад;
        # этот процесс происходит всегда, независимо от текущего состояния нейрона
        mediator_delta = self.mediator_decrease_speed * time_delta
        self.pre_mediator_quantity -= min(mediator_delta, self.pre_mediator_quantity)

        if not self.is_active():
            # если количество медиатора в РАБОЧЕМ буфере превышает порог срабатывания, повышаем потенциал
            # с потенциала покоя до потенциала действия
            if self.post_mediator_quantity >= self.firing_mediator_threshold:
                self.potential = self.action_potential_level
                self.firing_start_time = time_now  # фиксируем время начала импульса
                self.fires_count += 1

        if self.is_active():
            firing_end_time = self.firing_start_time + self.spike_duration

            # если мы всё еще в состоянии действия, раздаем медиатор по всем исходящим связям;
            # (порция раздаваемого медиатора постоянна для данного нейрона, но при передаче она умножается на вес и
            # полярность связи, так что разные постсинаптические нейроны получат разное кол-во медиатора)
            for link in self.out_links:
                link.dst_neuron.add_mediator(self.out_mediator_quantum * link.weight * link.sign)

            # проверяем, не пора ли снизить потенциал, т.е. закончить импульс
            if time_now > firing_end_time:
                self.potential = self.idle_potential_level

        self.time_prev = time_now


    def apply_mediator(self):
        """
        Скопировать медиатор из накопительного буфера в рабочий. Накопительный буфер при этом не обнуляется, и его
        значение переходит на следующий шаг.
        Это сделано для того, чтобы на каждом шаге нейроны работали с постоянным количеством медиатора, не зависящим
        от порядка их обхода алгоритмом.
        """
        self.post_mediator_quantity = self.pre_mediator_quantity


class Net(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.selected = False
        p = index.Property()
        p.dimension = 3
        self.spatial_index = index.Index(properties=p)

    def init_connections(self, pattern):
        excitatory_links_percent = 80  # процент возбуждающих связей (остальные - тормозящие)
        max_abs_weight = 10.0          # максимальное по абсолютной величине значение веса связи

        for neur_src in self.entities:
            if not isinstance(neur_src, Neuron):
                continue

            for neur_dst in self.entities:
                if not isinstance(neur_dst, Neuron):
                    continue

                if neur_dst != neur_src:
                    link = Link()
                    link.src_neuron = neur_src
                    link.dst_neuron = neur_dst

                    # выбираем вес связи случайным образом с учётом максимального:
                    link.weight = random.uniform(0, max_abs_weight)

                    # выбираем тип связи (возбуждающая или тормозящая) с учетом заданного соотношения:
                    rnd = random.randint(0, 100)
                    if rnd < excitatory_links_percent:
                        link.sign = 1
                    else:
                        link.sign = -1
                    neur_src.out_links.append(link)


    def print(self):
        pass

    def step(self):
        super().step()

        # фаза 1: пройтись во всем нейронам и активировать, какие надо
        # порядок обхода не имеет значения
        for neuron in self.entities:
            if isinstance(neuron, Neuron):
                neuron.operate()

        # фаза 2: обновить количество медиатора в рабочем буфере каждого нейрона для следующей итерации
        for neuron in self.entities:
            if isinstance(neuron, Neuron):
                neuron.apply_mediator()

