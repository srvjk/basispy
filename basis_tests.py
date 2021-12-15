import basis

system = basis.System()


class TestEntity1(basis.Entity):
    def __init__(self, name):
        super().__init__(name)


def test1() -> bool:
    test_entity_one = system.new(TestEntity1, "InitialName")
    if system.get_entity_by_name("InitialName") != test_entity_one:
        return False

    test_entity_one.rename("NewName")
    if system.get_entity_by_name("InitialName") is not None:
        return False
    if system.get_entity_by_name("NewName") != test_entity_one:
        return False

    return True


def test_all() -> bool:
    passed = True
    tests = list()

    # add all unit tests here:
    tests.append(test1)

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
