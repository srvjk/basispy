import basis
import pygame
import sys


class Board(basis.Entity):
    def __init__(self):
        super().__init__()


class Viewer(basis.Entity):
    def __init__(self):
        pygame.init()
        size = width, height = 640, 480
        self.screen = pygame.display.set_mode(size)

    def step(self):
        #print("-> viewer")
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        self.screen.fill((0, 0, 0))
        pygame.display.flip()


class Agent(basis.Entity):
    def __init__(self):
        self._position = [0, 0]

    @property
    def position(self):
        return self._position

    def step(self):
        pass