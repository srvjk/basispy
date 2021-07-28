import basis
import sys
import random
from kivy.app import App


class Board(basis.Entity):
    def __init__(self):
        super().__init__()
        self.size = 100
        self.cell_size = 3
        self.back_color = (10, 10, 10)

    def size_in_cells(self):
        return self.size

    def size_in_pixels(self):
        return self.size * self.cell_size

    def draw(self):
        for ent in self.entities:
            if isinstance(ent, Agent):
                try:
                    p = ent.position
                    agent_pos = ent.position
                except AttributeError:
                    pass


class Viewer(basis.Entity):
    def __init__(self):
        super().__init__()
        self.board = None
        size = width, height = 640, 480
        self.show_grid = True
        self.delay = 0.5

    def set_board(self, board):
        self.board = board

    def step(self):
        '''
        if self.board:
            board_size = min(actual_size[0] - self.main_tool_panel.width(), actual_size[1])
            self.board.draw()
            scaled_visual_field = pygame.transform.scale(self.board.visual_field, (board_size, board_size))
            self.screen.blit(scaled_visual_field, (0, 0))

            if self.show_grid:
                scaled_cell_size = board_size / self.board.size
                y = scaled_cell_size / 2.0
                for row in range(self.board.size):
                    x = scaled_cell_size / 2.0
                    for col in range(self.board.size):
                        point_rect = pygame.Rect(x, y, 1, 1)
                        pygame.draw.rect(self.screen, self.point_color, point_rect)
                        x += scaled_cell_size
                    y += scaled_cell_size

        imgui.render()
        self.impl.render(imgui.get_draw_data())

        pygame.display.flip()

        #time.sleep(self.delay)
        '''


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
        self.position[0] = min(self.position[0], self.board.size - 1)
        self.position[1] += random.choice([-1, 0, 1])
        self.position[1] = max(0, self.position[1])
        self.position[1] = min(self.position[1], self.board.size - 1)

