import basis


class Link:
    def __init__(self):
        self.weight = 0
        self.src_neuron = None
        self.dst_neuron = None
        self.weight = 1.0  # вес связи без учета её знака
        self.sign = 1  # знак связи (+1 для возбуждающих и -1 для тормозящих связей)


class BasicNeuron:
    def __init__(self):
        self.out_links = list()
        self.pos = [0, 0]                     # "логическое" положение нейрона в сети
        self.geo_pos = [0, 0]                 # "географическое" положение нейрона, т.е. координаты (x, y)
        self.geo_size = [10, 10]              # физический размер нейрона
        self.pre_mediator_quantity = 0
        self.post_mediator_quantity = 0
        self.firing_mediator_threshold = 1.0  # порог количества медиатора, необходимый для срабатывания
        self.out_mediator_quantum = 0.1       # количество медиатора, которое будет отправлено нейронам-получателям

    def set_activity(self, activity):
        pass

    def is_active(self):
        if self.post_mediator_quantity >= self.firing_mediator_threshold:
            return True
        return False

    def add_mediator(self, mediator_quantity):
        pass

    def fire(self):
        pass

    def swap_mediator_buffers(self):
        pass


class Sensor(BasicNeuron):
    def __init__(self):
        super().__init__()

    def set_activity(self, activity):
        if activity:
            self.post_mediator_quantity = self.firing_mediator_threshold
        else:
            self.post_mediator_quantity = 0


class Neuron(BasicNeuron):
    def __init__(self):
        super().__init__()

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


class Layer:
    def __init__(self, name):
        self.name = name
        self.neurons = list()

    def create(self, neur_num, neur_class):
        self.neurons = [neur_class() for _ in range(neur_num)]

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


class Net(basis.Entity):
    def __init__(self):
        super().__init__()
        self.layers = list()

    def new_layer(self, layer_name, neur_num, neur_class):
        layer = Layer(layer_name)
        layer.create(neur_num, neur_class)
        self.layers.append(layer)
        return layer

    def neurons(self):
        """ Get all neurons in flat list """
        result = list()
        for layer in self.layers:
            for neuron in layer.neurons:
                result.append(neuron)

        return result

    def print(self):
        print("Layers: {}".format(len(self.layers)))
        for layer in self.layers:
            print("{}: {}".format(layer.name, len(layer.neurons)))

    def step(self):
        super().step()

        # фаза 1: пройтись во всем нейронам и активировать, какие надо
        # порядок обхода не имеет значения
        for layer in self.layers:
            for neuron in layer.neurons:
                neuron.fire()

        # фаза 2: поменять местами буферы накопления активности для следующей итерации
        for layer in self.layers:
            for neuron in layer.neurons:
                neuron.swap_mediator_buffers()

    def space_evenly(self):
        """ Distribute neurons evenly over the available space """

        cur_y = 0
        for layer in self.layers:
            cur_x = 0
            dy = 0  # высота строки нейронов (слоя)
            for neuron in layer.neurons:
                neuron.geo_pos[0] = cur_x
                neuron.geo_pos[1] = cur_y
                cur_x += neuron.geo_size[0]
                tmp_y = neuron.geo_size[1]
                if tmp_y > dy:
                    dy = tmp_y
            cur_y += dy
