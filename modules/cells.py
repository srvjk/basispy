import basis
import pygame
import sys
import random


class Board(basis.Entity):
    def __init__(self):
        super().__init__()
        self.size = self.width, self.height = 100, 100
        self.cell_size = 3
        self.visual_field = pygame.Surface(self.size_in_pixels())

    def size_in_cells(self):
        return self.size

    def size_in_pixels(self):
        return self.width * self.cell_size, self.height * self.cell_size

    def draw(self):
        self.visual_field.fill((100, 100, 100))


class Viewer(basis.Entity):
    def __init__(self, board):
        super().__init__()
        pygame.init()
        self.board = board
        size = width, height = 640, 480
        self.screen = pygame.display.set_mode(size)

    def step(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        self.screen.fill((0, 0, 0))

        if not self.board:
            return

        self.board.draw()
        self.screen.blit(self.board.visual_field, (0, 0))

        for ent in self.system.entities:
            if isinstance(ent, Agent):
                try:
                    p = ent.position
                    pygame.draw.circle(self.screen, (100, 0, 0), p, 10)
                except AttributeError:
                    pass

        pygame.display.flip()


class Agent(basis.Entity):
    def __init__(self):
        super().__init__()
        self._position = [320, 240]

    @property
    def position(self):
        return self._position

    def step(self):
        self.position[0] += random.choice([-1, 0, 1])
        self.position[1] += random.choice([-1, 0, 1])
