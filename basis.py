import sys
import importlib
import importlib.util
from collections import deque
import uuid
import time
from enum import Enum
import inspect
import logging
import gc


def first_of(lst):
    if not lst:
        return None

    return lst[0]

def short_class_name(self):
    """
    Возвращает короткое имя класса (не включая имя модуля).
    :return: строковое представление короткого имени класса
    """
    return self.__class__.__name__

def qual_class_name(self):
    """
    Возвращает квалифицированное имя класса (включая имя модуля).
    :return: строковое представление полного имени класса
    """
    return "{}.{}".format(self.__module__, self.__class__.__name__)


class BasisException(Exception):
    pass


class Entity:
    def __init__(self, system, name=""):
        self.uuid = uuid.uuid4()         # глобально уникальный, случайно генерируемый идентификатор сущности
        self.name = name                 # имя сущности (д.б. локально-уникальным, т.е. в пределах сущности-контейнера)
        self.system = system             # ссылка на систему
        self.base = None                 # ссылка на базовую сущность (для граней) TODO не объединить ли с container ?
        self.container = None            # ссылка на контейнер (для вложенных сущностей)
        self.entities = set()            # вложенные сущности
        self.entity_name_index = dict()  # индекс вложенных сущностей с доступом по имени
        self.may_be_paused = True        # можно ли ставить эту сущность на паузу
        self.step_min_time_period = 0.0  # минимальный период между шагами для этой сущности (для управления скоростью)
        self.last_time_stamp = 0         # предыдущая отметка времени (для управления скоростью)
        self._local_step_counter = 0     # локальный счетчик шагов данной сущности

    def create(self, source=None):
        """
        Создать экземпляр сущности. Возможно, из внешнего источника.
        :param source: если задано, будет использовано в качестве внешнего источника для создания сущности
        :return:
        """
        pass

    def clear(self):
        self.entity_name_index.clear()

        for ent in self.entities.copy():
            ent.abolish()

    def abolish(self):
        """
        'Упразднить' данную сущность, т.е. очистить, удалить из родительской сущности и вычеркнуть из системного
        реестра.
        'Упразднённая' сущность может продолжать физически существовать некоторое время, пока на неё имеются ссылки
        из других объектов.
        :return:
        """
        self.clear()

        before = self.system.get_entities_total()
        type_name = type(self)

        if self.container:
            self.container.remove_entity(self)
        if self.system:
            self.system.unregister_entity(self)
        after = self.system.get_entities_total()
        self.system.logger.debug(">>> entity removed: {} {} -> {}".format(type_name, before, after))

    def abolish_children(self, condition):
        """
        'Упразднить' все вложенные сущности, удовлетворяющие заданному условию.
        :param condition:
        :return:
        """
        for ent in self.entities.copy():
            if condition(ent):
                ent.abolish()

    def add_entity(self, entity) -> (bool, str):
        if not isinstance(entity, Entity):
            self.system.report_error("not an Entity")
            return False
        if entity.name:
            if entity.name in self.entity_name_index:
                self.system.report_error("name '{}' already exists".format(entity.name))
                return False
        if entity in self.entities:
            return True

        entity.container = self
        entity.system = self.system
        self.entities.add(entity)
        if entity.name:
            self.entity_name_index[entity.name] = entity

        return True

    def remove_entity(self, entity):
        if not isinstance(entity, Entity):
            self.system.report_error("not an Entity")
            return
        if entity.name:
            if entity.name in self.entity_name_index:
                del self.entity_name_index[entity.name]
        self.entities.remove(entity)

    def add_new(self, class_name, entity_name=""):
        """
        Создать новую сущность и добавить её в список дочерних.
        :param class_name: имя класса создаваемой сущности
        :param entity_name: собственное имя новой сущности, уникальное только в пределах данного контейнера
        :return: созданная сущность
        """
        ent = self.system.new(class_name, entity_name)
        if not ent:
            return None
        self.add_entity(ent)

        return ent

    def get_entity_by_id(self, entity_uuid):
        return self.system.entity_uuid_index.get(entity_uuid)

    def get_entity_by_name(self, name):
        """ Найти вложенную сущность по ее уникальному имени, нерекурсивно """
        return self.entity_name_index.get(name)

    def get_entities_by_name_recursively(self, name):
        """ Найти рекурсивно все вложенные сущности c заданным именем """
        result = list()
        for ent in self.entities:
            if ent.name == name:
                result.append(ent)
            tmp_res = ent.get_entities_by_name_recursively(name)
            if tmp_res:
                result.extend(tmp_res)
        return result

    def get_entities_by_type(self, type_name):
        """ Найти (без рекурсии) все вложенные сущности заданного типа или его производных """
        result = list()
        for ent in self.entities:
            if isinstance(ent, type_name):
                result.append(ent)

        return result

    def get_entities_by_type_recursively(self, type_name):
        """ Найти рекурсивно все вложенные сущности заданного типа или его производных """
        result = list()
        for ent in self.entities:
            if isinstance(ent, type_name):
                result.append(ent)
            tmp_res = ent.get_entities_by_type_recursively(type_name)
            if tmp_res:
                result.extend(tmp_res)
        return result

    def get_entities(self, criterion):
        """ Найти все вложенные сущности, удовлетворяющие критерию criterion """
        result = list()
        for ent in self.entities:
            if criterion(ent):
                result.append(ent)

        return result

    def get_entities_recursively(self, criterion):
        """ Найти рекурсивно все вложенные сущности, удовлетворяющие критерию criterion """
        result = list()
        for ent in self.entities:
            if criterion(ent):
                result.append(ent)
            tmp_res = ent.get_entities_recursively(criterion)
            if tmp_res:
                result.extend(tmp_res)

        return result

    def siblings(self):
        """ Получить все другие вложенные сущности того же контейнера, в котором содержится данная сущность """
        if self.container:
            for e in self.container.entities.copy():
                if e.uuid != self.uuid:
                    yield e

    def on_entity_renamed(self, entity, old_name, new_name) -> bool:
        if entity not in self.entities:
            return False  # no such entity at all
        if new_name in self.entity_name_index:
            return False  # entity with new_name already exists in index

        prev_indexed_entity = self.entity_name_index.get(old_name)
        if prev_indexed_entity == entity:
            del self.entity_name_index[old_name]  # remove old record from index

        self.entity_name_index[new_name] = entity

        return True

    def is_empty(self):
        if self.entities:
            return False
        return True

    def print_entities(self):
        for ent in self.entities:
            print(ent)

    def rename(self, new_name) -> bool:
        old_name = self.name
        self.name = new_name
        result = self.system.on_entity_renamed(self, old_name, new_name)

        return result

    def full_name(self):
        """ Получить полное имя сущности, состоящее из её собственного имени и имён всех ее контейнеров """
        res = ""
        ent = self
        while ent:
            tmp_name = ent.name
            if not tmp_name:
                tmp_name = "?"
            if res:
                res = tmp_name + "." + res
            else:
                res = tmp_name
            ent = ent.container

        return res

    def has_one_of(self, condition):
        for ent in self.entities:
            if condition(ent):
                return True
        return False

    def get_local_step_counter(self):
        return self._local_step_counter

    def new_facet(self, type_name):
        fct = type_name()
        if not fct:
            return None
        fct.base = self

        return fct

    def get_facet(self, type_name):  #TODO временно, переделать!
        for k, v in inspect.getmembers(self):
            if isinstance(v, type_name):
                return v

        return None

    def has_facet(self, type_name):  #TODO временно, переделать!
        for k, v in inspect.getmembers(self):
            if isinstance(v, type_name):
                return True

        return False

    def make_step(self):
        now = time.monotonic_ns()
        time_delta = (now - self.last_time_stamp) / 1e9
        if time_delta < self.step_min_time_period:
            return False

        self.step()

        self.last_time_stamp = now
        self._local_step_counter += 1

        return True

    def step(self):
        for ent in self.entities:
            ent.make_step()


class OnOffTrigger(Entity):
    def __init__(self, system):
        super().__init__(system)
        self.active = False
        self.caption_on = "On"
        self.caption_off = "Off"

    def caption(self):
        if self.active:
            return self.caption_on
        else:
            return self.caption_off

    def toggle(self):
        self.active = not self.active


class EntityCollisionException(BasisException):
    def __init__(self, message=""):
        super().__init__()
        self.message = message


class TimingMode(Enum):
    UnrealTime = 0
    RealTime = 1


class UnsupportedTimingModeException(BasisException):
    def __init__(self, message=""):
        super().__init__()
        self.message = message


class SystemStatistics:
    def __init__(self):
        self.counter_by_type = dict()  # для подсчета количества сущностей каждого типа
        self.total_obj_count = 0       # общее количество объектов в приложении (вывод функции dir())


class System(Entity):
    def __init__(self):
        super().__init__(system=None)
        self.system = self
        self.name = "System"
        self.entity_uuid_index = dict()        # индекс всех сущностей в системе с доступом по UUID
        self.entity_type_count = dict()
        self.recent_errors = deque(maxlen=10)
        self.should_stop = False
        self._step_counter = 0                 # глобальный счетчик шагов
        self._fps = 0.0                        # мгновенная частота шагов/кадров (кадров в секунду)
        self._last_step_counter = 0            # последнее сохраненное значение счетчика шагов
        self._last_time_stamp = 0              # последняя сделанная временная отметка, нс
        self._fps_probe_interval = int(1e9)    # интервал между замерами FPS, нс
        self._last_fps_time_stamp = 0          # последняя отметка времени для измерения FPS, нс
        self._last_stats_time_stamp = 0        # последняя отметка времени для сбора статистики, нс
        self._stats_probe_interval = int(1e9)  # интервал сбора статистики, нс
        self._model_time_ns = 0                # модельное время (от первого System.step()), нс
        self.pause = True                      # флаг режима "Пауза/пошаговый"
        self.step_time_delta_ns = 1000000      # длительность 1 шага модельного времени, нс
        #self.timing_mode = TimingMode.UnrealTime # режим исчисления модельного времени
        self.timing_mode = TimingMode.RealTime # режим исчисления модельного времени
        self.model_time_speed = 1.0
        self.do_single_step = False            # сделать один шаг в режиме "Пауза" (для пошагового режима)
        self.statistics = SystemStatistics()   # системная статистика
        self.logger = logging.getLogger("system")
        self.logger.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(stream_handler)

    def clear(self):
        super().clear()
        self.entity_uuid_index.clear()
        self.recent_errors.clear()

    def load(self, module_name, dir_path='.'):
        module_full_path = dir_path + '/' + module_name

        module_spec = importlib.util.spec_from_file_location(module_name, module_full_path)
        if module_spec is None:
            print('Module {} not found in {}'.format(module_name, dir_path))
            return None
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        # set connection with System for each class derived from Entity:
        # symbols = dir(module)
        # for s in symbols:
        #     cls = getattr(module, s)
        #     if not inspect.isclass(cls):
        #         continue

        return module

    def new(self, class_name, entity_name=""):
        """
        Создать новую сущность заданного класса и зарегистрировать её в системе.
        :param class_name:
        :param entity_name:
        :return:
        """
        item = class_name(self.system)
        if not item:
            self.system.report_error("'{}' is not a class name".format(class_name))
            return None
        if not isinstance(item, Entity):
            self.system.report_error("not an Entity")
            return None
        item.name = entity_name

        self.system.register_entity(item)

        return item

    def register_entity(self, entity):
        before = self.get_entities_total()
        old = self.entity_uuid_index.get(entity.uuid, None)
        if old:
            if old == entity:
                return  # эта сущность уже в списке
            else:
                msg = "trying to register entity with UUID={}, but item already exists".format(entity.uuid)
                raise EntityCollisionException(msg)

        self.entity_uuid_index[entity.uuid] = entity

        type_name = type(entity)
        cnt = self.statistics.counter_by_type.get(type_name, 0)
        cnt += 1
        self.statistics.counter_by_type[type_name] = cnt

        after = self.get_entities_total()
        self.logger.debug("*** entity registered: {} {} -> {}".format(type(entity), before, after))

    def unregister_entity(self, entity):
        if entity.uuid in self.entity_uuid_index:
           del self.entity_uuid_index[entity.uuid]

        type_name = type(entity)
        cnt = self.statistics.counter_by_type.get(type_name, 0)
        cnt -= 1
        self.statistics.counter_by_type[type_name] = cnt

    def step(self):
        #super().step()

        if self.do_single_step:
            pass

        # когда мы на паузе и при этом не в пошаговом режиме, пропускаем текущий шаг
        # для тех сущностей, для которых пауза разрешена
        skip_this_step = False
        if self.pause and not self.do_single_step:
            skip_this_step = True
        if self.do_single_step:
            self.do_single_step = False

        for entity in self.entities.copy():
            skip_entity = False
            if skip_this_step:
                if entity.may_be_paused:
                    skip_entity = True
            if not skip_entity:
                entity.step()

        # измерения модельного времени
        if self.timing_mode == TimingMode.UnrealTime:
            if not skip_this_step:
                self._model_time_ns += self.step_time_delta_ns
        elif self.timing_mode == TimingMode.RealTime:
            time_now = time.monotonic_ns()
            if self._step_counter == 0:
                self._last_time_stamp = time_now  # на первом шаге только делается стартовая отметка времени
            time_delta = 0
            if not skip_this_step:
                time_delta = time_now  - self._last_time_stamp  # время паузы мы просто пропускаем
            self._last_time_stamp = time_now
            self._model_time_ns += time_delta
        else:
            raise UnsupportedTimingModeException()

        if not skip_this_step:
            self._step_counter += 1
        step_diff = self._step_counter - self._last_step_counter
        time_now = time.monotonic_ns()
        t_diff = time_now - self._last_fps_time_stamp
        if t_diff > self._fps_probe_interval:
            t_diff_seconds = t_diff / 1e9
            self._fps = step_diff / t_diff_seconds
            self._last_step_counter = self._step_counter
            self._last_fps_time_stamp = time_now

        # измерения производительности
        time_now = time.monotonic_ns()
        t_diff = time_now - self._last_stats_time_stamp
        if t_diff > self._stats_probe_interval:
            counts = gc.get_count()
            self.statistics.total_obj_count = len(gc.garbage)
            self._last_stats_time_stamp = time_now

        return True

    def operate(self):
        self._step_counter = 0
        self._fps = 0.0
        self._last_step_counter = 0
        self._last_time_stamp = 0
        self._fps_probe_interval = int(1e9)
        self._stats_probe_interval = int(1e9)
        self._last_fps_time_stamp = 0
        self._last_stats_time_stamp = 0
        self._model_time_ns = 0
        self.should_stop = False

        while not self.should_stop:
            self.make_step()

        print("System finished operation")

    def shutdown(self):
        print("System shutdown request")
        self.should_stop = True

    def report_error(self, error_description):
        self.recent_errors.append(error_description)

    def model_time_ns(self):
        return self._model_time_ns

    def model_time_s(self):
        return self._model_time_ns / 1e9

    def get_global_step_counter(self):
        return self._step_counter

    def get_fps(self):
        return self._fps

    def get_entities_total(self):
        return len(self.entity_uuid_index)


def main():
    system = System()
    system.operate()


if __name__ == "__main__":
    main()
