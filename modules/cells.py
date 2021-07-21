import basis
import basis_ui
import pygame
import sys
import random


class Board(basis.Entity):
    def __init__(self):
        super().__init__()
        self.size = self.width, self.height = 100, 100
        self.cell_size = 3
        self.visual_field = pygame.Surface(self.size_in_pixels())
        self.back_color = (10, 10, 10)

    def size_in_cells(self):
        return self.size

    def size_in_pixels(self):
        return self.width * self.cell_size, self.height * self.cell_size

    def draw(self):
        self.visual_field.fill(self.back_color)

        for ent in self.entities:
            if isinstance(ent, Agent):
                try:
                    p = ent.position
                    agent_pos = ent.position
                    agent_rect = pygame.Rect(agent_pos[0] * self.cell_size, agent_pos[1] * self.cell_size,
                                             self.cell_size, self.cell_size)
                    pygame.draw.rect(self.visual_field, (100, 0, 0), agent_rect)
                except AttributeError:
                    pass


class Viewer(basis.Entity):
    def __init__(self):
        super().__init__()
        pygame.init()
        self.board = None
        size = width, height = 640, 480
        self.point_color = (100, 100, 100)
        self.screen = pygame.display.set_mode(size)
        self.toggle_grid_button = basis_ui.Button(self.screen, pygame.Rect(400, 10, 100, 20), "Grid")
        self.show_grid = True

    def set_board(self, board):
        self.board = board

    def step(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        self.screen.fill((0, 0, 0))

        self.toggle_grid_button.draw()
        self.toggle_grid_button.step()
        if self.toggle_grid_button.is_mouse_down():
            self.show_grid = not self.show_grid

        if not self.board:
            return

        self.board.draw()
        self.screen.blit(self.board.visual_field, (0, 0))

        if self.show_grid:
            y = self.board.cell_size / 2.0
            for row in range(self.board.height):
                x = self.board.cell_size / 2.0
                for col in range(self.board.width):
                    point_rect = pygame.Rect(x, y, 1, 1)
                    pygame.draw.rect(self.screen, self.point_color, point_rect)
                    x += self.board.cell_size
                y += self.board.cell_size

        pygame.display.flip()


class Agent(basis.Entity):
    def __init__(self):
        super().__init__()
        self.board = None
        self._position = [0, 0]

    def set_board(self, board):
        self.board = board
        self.board.add_entity(self)

    @property
    def position(self):
        return self._position

    def step(self):
        if not self.board:
            return

        self.position[0] += random.choice([-1, 0, 1])
        self.position[0] = max(0, self.position[0])
        self.position[0] = min(self.position[0], self.board.size[0] - 1)
        self.position[1] += random.choice([-1, 0, 1])
        self.position[1] = max(0, self.position[1])
        self.position[1] = min(self.position[1], self.board.size[1] - 1)

