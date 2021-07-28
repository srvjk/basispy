import basis
import pygame
import sys
import random
import pygame_gui


class Board(basis.Entity):
    def __init__(self):
        super().__init__()
        self.size = 100
        self.cell_size = 3
        self.visual_field = pygame.Surface((self.size_in_pixels(), self.size_in_pixels()))
        self.back_color = (10, 10, 10)

    def size_in_cells(self):
        return self.size

    def size_in_pixels(self):
        return self.size * self.cell_size

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
        pygame.display.set_caption('Cells')
        self.board = None
        size = width, height = 640, 480
        self.point_color = (100, 100, 100)
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.show_grid = True
        self.delay = 0.5
        self.ui_manager = pygame_gui.UIManager(size)
        self.clock = pygame.time.Clock()

        button_layout_rect = pygame.Rect(0, 0, 100, 20)
        button_layout_rect.topright = (-10, 10)
        self.toggle_grid_button = pygame_gui.elements.UIButton(relative_rect=button_layout_rect,
                                                               text='Grid', manager=self.ui_manager,
                                                               anchors={'left': 'right',
                                                                        'right': 'right',
                                                                        'top': 'top',
                                                                        'bottom': 'bottom'})

    def set_board(self, board):
        self.board = board

    def step(self):
        time_delta = self.clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.VIDEORESIZE:
                print("new size {}x{}".format(event.w, event.h))
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.toggle_grid_button:
                        self.show_grid = not self.show_grid

            self.ui_manager.process_events(event)

        self.ui_manager.update(time_delta)

        actual_size = pygame.display.get_window_size()

        if self.board:
            board_size = min(actual_size[0], actual_size[1])
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

        self.ui_manager.draw_ui(self.screen)
        #pygame.display.flip()
        pygame.display.update()


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

