import importlib
import importlib.util


class System:
    def __init__(self):
        pass

    @staticmethod
    def load(module_name, dir_path='.'):
        module_full_path = dir_path + '/' + module_name

        module_spec = importlib.util.spec_from_file_location(module_name, module_full_path)
        if module_spec is None:
            print('Module {} not found in {}'.format(module_name, dir_path))
            return None
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module

    def create(self, entity_class_name):
        pass

    def animate(self, entity):
        pass

    def step(self):
        print("step")

    def operate(self):
        while True:
            self.step()


def main():
    system = System()
    system.operate()


if __name__ == "__main__":
    main()
