import importlib
import importlib.util
import inspect
import logging
from collections import deque


class Entity:
    def __init__(self, system, name=""):
        self.name = name
        self.system = system          # ссылка на систему
        self.parent = None            # ссылка на родительскую сущность
        self.entities = set()         # вложенные сущности
        self.active_entities = set()  # active nested entities, i.e. those for which step() should be called
        self.entity_name_index = dict()  # nested entity index with name as a key
        self.step_divider = 1  # this entity will be activated every step_divider steps
        self.step_counter = 0  # счетчик шагов индивидуален для каждой сущности

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

        return True

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

    def set_step_divider(self, div_value):
        if div_value < 1:
            return
        self.step_divider = div_value

    def step(self):
        self.step_counter += 1


class System(Entity):
    def __init__(self):
        super().__init__(system=None)
        self.system = self
        self.recent_errors = deque(maxlen=10)
        self.step_counter = 0
        self.should_stop = False

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

    def step(self):
        super().step()
        for entity in self.active_entities:
            if self.step_counter % entity.step_divider == 0:
                entity.step()

    def operate(self):
        self.step_counter = 0
        self.should_stop = False

        while not self.should_stop:
            self.step_counter += 1
            self.step()

        print("System finished operation")

    def shutdown(self):
        print("System shutdown request")
        self.should_stop = True

    def report_error(self, error_description):
        self.recent_errors.append(error_description)


def main():
    system = System()
    system.operate()


if __name__ == "__main__":
    main()
