import importlib
import importlib.util
import inspect


class Entity:
    system = None

    @classmethod
    def system_connect(cls, system):
        cls.system = system


class System:
    def __init__(self):
        self.active_entities = set()  # active entities, i.e. those for which step() should be called

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

    def create(self, entity_class_name):
        pass

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
