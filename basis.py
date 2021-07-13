import importlib
import importlib.util
import inspect
import logging


class Entity:
    system = None

    def __init__(self, name=""):
        self.name = name
        if self.system is not None:
            ok = self.system.add_entity(self)
            if not ok:
                logging.warning("failed to add entity to System")
        else:
            logging.warning("creating Entity before system_connect")

    @classmethod
    def system_connect(cls, system):
        cls.system = system

    def rename(self, new_name) -> bool:
        old_name = self.name
        self.name = new_name
        result = self.system.on_entity_renamed(self, old_name, new_name)

        return result


class System:
    def __init__(self):
        self.entities = set()         # all entities
        self.active_entities = set()  # active entities, i.e. those for which step() should be called
        self.entity_name_index = dict()  # entity index with name as a key

    def load(self, module_name, dir_path='.'):
        module_full_path = dir_path + '/' + module_name

        module_spec = importlib.util.spec_from_file_location(module_name, module_full_path)
        if module_spec is None:
            print('Module {} not found in {}'.format(module_name, dir_path))
            return None
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        # set connection with System for each class derived from Entity:
        symbols = dir(module)
        for s in symbols:
            cls = getattr(module, s)
            if not inspect.isclass(cls):
                continue
            if issubclass(cls, Entity):
                cls.system_connect(self)
                print('system connect for {} ok'.format(s))

        return module

    def add_entity(self, entity) -> bool:
        if not isinstance(entity, Entity):
            return False
        if entity.name is not None:
            if entity.name in self.entity_name_index:
                return False  # entity with this name already exists
        if entity in self.entities:
            return True  # ok, already added

        self.entities.add(entity)
        self.entity_name_index[entity.name] = entity

        return True

    def find_entity_by_name(self, name):
        return self.entity_name_index.get(name)

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

    def step(self):
        for entity in self.active_entities:
            entity.step()

    def operate(self):
        while True:
            self.step()


def main():
    system = System()
    system.operate()


if __name__ == "__main__":
    main()
