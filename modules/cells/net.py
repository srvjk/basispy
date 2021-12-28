import basis
import random


class Link:
    def __init__(self):
        self.weight = 0
        self.src_neuron = None
        self.dst_neuron = None
        self.weight = 1.0  # вес связи без учета её знака
        self.sign = 1  # знак связи (+1 для возбуждающих и -1 для тормозящих связей)


class Neuron(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.out_links = list()
        self.pos = [0, 0, 0]                  # положение нейрона в сети (в большинстве случаев 2D, т.е. pos[2] = 0)
        self.pre_mediator_quantity = 0
        self.post_mediator_quantity = 0
        self.firing_mediator_threshold = 1.0  # порог количества медиатора, необходимый для срабатывания
        self.out_mediator_quantum = 0.1       # количество медиатора, которое будет отправлено нейронам-получателям

    def set_activity(self, activity):
        if activity:
            self.post_mediator_quantity = self.firing_mediator_threshold
        else:
            self.post_mediator_quantity = 0

    def is_active(self):
        if self.post_mediator_quantity >= self.firing_mediator_threshold:
            return True
        return False

    def add_mediator(self, mediator_quantity):
        self.pre_mediator_quantity += mediator_quantity

    def fire(self):
        """
        Рабочая функция нейрона - 'выстрел' потенциала действия

        Раздаёт медиатор по всем исходящим связям с учетом их весов и полярностей.
        Кол-во медиатора фиксировано для данного нейрона, но при передаче умножается на вес и полярность связи,
        так что разные постсинаптические нейроны получат разное итоговое кол-во медиатора.
        """
        if self.post_mediator_quantity >= self.firing_mediator_threshold:
            for link in self.out_links:
                link.dst_neuron.add_mediator(self.out_mediator_quantum * link.weight * link.sign)

    def swap_mediator_buffers(self):
        self.post_mediator_quantity = self.pre_mediator_quantity
        self.pre_mediator_quantity = 0


class Net(basis.Entity):
    def __init__(self, system):
        super().__init__(system)
        self.selected = False

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
            if not isinstance(neuron, Neuron):
                continue
            neuron.fire()

        # фаза 2: поменять местами буферы накопления активности для следующей итерации
        for neuron in self.entities:
            if not isinstance(neuron, Neuron):
                continue
            neuron.swap_mediator_buffers()

