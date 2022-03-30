import basis

system = basis.System()


class TestEntity1(basis.Entity):
    def __init__(self, name):
        super().__init__(name)
        self.int_data = 5

class TestEntity2(basis.Entity):
    def __init__(self, name):
        super().__init__(name)
        self.int_data_1 = 1
        self.string_data_1 = "some_text"

def test1() -> bool:
    # Тест на переименование сущностей
    test_entity_one = system.add_new(TestEntity1, "InitialName")
    if system.get_entity_by_name("InitialName") != test_entity_one:
        return False

    test_entity_one.rename("NewName")
    if system.get_entity_by_name("InitialName") is not None:
        return False
    if system.get_entity_by_name("NewName") != test_entity_one:
        return False

    system.clear()

    return True

def test2() -> bool:
    #TODO Тест на удаление сущностей
    return False

def test3() -> bool:
    # Тест на клонирование сущностей
    ent_orig = system.new(TestEntity2, "Original")
    ent_orig.add_new(TestEntity1, "Child1")
    ent_orig.add_new(TestEntity1, "Child2")

    ent_cloned = ent_orig.clone()
    if ent_cloned.int_data_1 != ent_orig.int_data_1:
        return False
    if ent_cloned.string_data_1 != ent_orig.string_data_1:
        return False

    # проверяем идентичность списков дочерних сущностей (с точностью до имён)
    if len(ent_cloned.entities) != len(ent_orig.entities):
        return False
    for child_orig in ent_orig.entities:
        name = child_orig.name + "*"
        child_cloned = ent_cloned.get_entity_by_name(name)
        if not child_cloned:
            return False
        if child_cloned.int_data != child_orig.int_data:
            return False

    system.clear()

    return True

def test_all() -> bool:
    passed = True
    tests = list()

    # add all unit tests here:
    tests.append(test1)
    tests.append(test2)
    tests.append(test3)

    # do all tests:
    print("*** Testing ***")
    for test in tests:
        res = test()
        print("{} : {}".format(test.__name__, "ok" if res else "fail"))
        if not res:
            passed = False

    return passed


def main():
    passed = test_all()
    if passed:
        print("all tests passed")
    else:
        print("not all tests passed!")


if __name__ == "__main__":
    main()
