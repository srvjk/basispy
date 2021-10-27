import basis


class Board(basis.Entity):
    def __init__(self):
        super().__init__()


class Viewer(basis.Entity):
    def step(self):
        print("-> viewer")


class Agent:
    def step(self):
        pass