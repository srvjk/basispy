import importlib
import importlib.util
from collections import deque
import uuid
import time
from enum import Enum


class BasisException(Exception):
    pass


class Entity:
    def __init__(self, system, name=""):
        self.uuid = uuid.uuid4()         # глобально уникальный, случайно генерируемый идентификатор сущности
        self.name = name                 # имя сущности (не обязано быть уникальным)
        self.system = system             # ссылка на систему
        self.parent = None               # ссылка на родительскую сущность
        self.entities = set()            # вложенные сущности
        self.active_entities = set()     # active nested entities, i.e. those for which step() should be called
        self.entity_name_index = dict()  # nested entity index with name as a key
        self.may_be_paused = True        # можно ли ставить эту сущность на паузу

    def new(self, class_name, entity_name=""):
        item = class_name(self.system)
        if not item:
            self.system.report_error("'{}' is not a class name".format(class_name))
            return None
        if not isinstance(item, Entity):
            self.system.report_error("not an Entity")
            return None
        item.name = entity_name
        if self.add_entity(item):
            return item

        self.system.report_error("unknown error")
        return None

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

        entity.parent = self
        entity.system = self.system
        self.entities.add(entity)
        if entity.name:
            self.entity_name_index[entity.name] = entity

        self.system.register_entity(entity)  # заносим сущность в общесистемный реестр

        return True

    def get_entity_by_id(self, entity_uuid):
        return self.system.entity_uuid_index.get(entity_uuid)

    def get_entity_by_name(self, name):
        """ Найти вложенную сущность по ее уникальному имени, нерекурсивно """
        return self.entity_name_index.get(name)

    def get_entities_by_name_recursively(self, name):
        """ Найти рекурсивно все вложенные сущности c заданным коротким именем """
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

    def print_entities(self):
        for ent in self.entities:
            print(ent)

    def activate(self, entity):
        if not isinstance(entity, Entity):
            return False
        if entity in self.active_entities:
            return True  # ok, already activated
        self.active_entities.add(entity)
        return True

    def rename(self, new_name) -> bool:
        old_name = self.name
        self.name = new_name
        result = self.system.on_entity_renamed(self, old_name, new_name)

        return result

    def step(self):
        pass


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

class System(Entity):
    def __init__(self):
        super().__init__(system=None)
        self.system = self
        self.entity_uuid_index = dict()        # индекс всех сущностей в системе с доступом по UUID
        self.recent_errors = deque(maxlen=10)
        self.should_stop = False
        self._step_counter = 0                 # счетчик шагов индивидуален для каждой сущности
        self._fps = 0.0                        # мгновенная частота шагов/кадров (кадров в секунду)
        self._last_step_counter = 0            # последнее сохраненное значение счетчика шагов
        self._last_time_stamp = 0              # последняя сделанная временная отметка, нс
        self._fps_probe_interval = int(1e9)    # интервал между замерами FPS, нс
        self._last_fps_time_stamp = 0          # последняя отметка времени для измерения FPS, нс
        self._model_time_ns = 0                # модельное время (от первого System.step()), нс
        self.pause = False                     # флаг режима "Пауза/пошаговый"
        self.step_time_delta_ns = 1000000      # длительность 1 шага модельного времени, нс
        #self.timing_mode = TimingMode.UnrealTime # режим исчисления модельного времени
        self.timing_mode = TimingMode.RealTime # режим исчисления модельного времени
        self.model_time_speed = 1.0

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

    def register_entity(self, entity):
        old = self.entity_uuid_index.get(entity.uuid, None)
        if old:
            if old == entity:
                return  # эта сущность уже в списке
            else:
                msg = "trying to register entity with UUID={}, but item already exists".format(entity.uuid)
                raise EntityCollisionException(msg)

        self.entity_uuid_index[entity.uuid] = entity

    def unregister_entity(self, entity):
        pass

    def step(self):
        super().step()

        for entity in self.active_entities.copy():
            skip_entity = False
            if self.pause:
                if entity.may_be_paused:
                    skip_entity = True
            if not skip_entity:
                entity.step()

        # измерения модельного времени
        if self.timing_mode == TimingMode.UnrealTime:
            if not self.pause:
                self._model_time_ns += self.step_time_delta_ns
        elif self.timing_mode == TimingMode.RealTime:
            time_now = time.monotonic_ns()
            if self._step_counter == 0:
                self._last_time_stamp = time_now  # на первом шаге только делается стартовая отметка времени
            time_delta = 0
            if not self.pause:
                time_delta = time_now  - self._last_time_stamp  # время паузы мы просто пропускаем
            self._last_time_stamp = time_now
            self._model_time_ns += time_delta
        else:
            raise UnsupportedTimingModeException()

        if not self.pause:
            self._step_counter += 1
        step_diff = self._step_counter - self._last_step_counter
        time_now = time.monotonic_ns()
        t_diff = time_now - self._last_fps_time_stamp
        if t_diff > self._fps_probe_interval:
            t_diff_seconds = t_diff / 1e9
            self._fps = step_diff / t_diff_seconds
            self._last_step_counter = self._step_counter
            self._last_fps_time_stamp = time_now

    def operate(self):
        self._step_counter = 0
        self._fps = 0.0
        self._last_step_counter = 0
        self._last_time_stamp = 0
        self._fps_probe_interval = int(1e9)
        self._last_fps_time_stamp = 0
        self._model_time_ns = 0
        self.should_stop = False

        while not self.should_stop:
            self.step()

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

    def get_step_counter(self):
        return self._step_counter

    def get_fps(self):
        return self._fps


def main():
    system = System()
    system.operate()


if __name__ == "__main__":
    main()
