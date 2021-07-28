import basis
import basis_ui
import cocos
import sys
import random
import time
import imgui
from imgui.integrations.pygame import PygameRenderer
import OpenGL.GL as gl


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
        self.board = None
        size = width, height = 640, 480
        self.point_color = (100, 100, 100)
        self.screen = pygame.display.set_mode(size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
        self.main_tool_panel = basis_ui.Panel(self.screen, pygame.Rect(300, 10, 200, 200))
        self.toggle_grid_button = basis_ui.Button(self.main_tool_panel, pygame.Rect(10, 10, 100, 20), "Grid")
        self.speed_increase_button = basis_ui.Button(self.main_tool_panel, pygame.Rect(10, 35, 40, 40), "SP +")
        self.speed_decrease_button = basis_ui.Button(self.main_tool_panel, pygame.Rect(55, 35, 40, 40), "SP -")
        self.show_grid = True
        self.delay = 0.5

        self.impl = PygameRenderer()
        io = imgui.get_io()
        io.display_size = size

    def set_board(self, board):
        self.board = board

    def step(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            self.impl.process_event(event)
            '''
            elif event.type == pygame.VIDEORESIZE:
                print("new size {}x{}".format(event.w, event.h))
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            '''

        imgui.new_frame()

        gl.glClearColor(0, 0, 1, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        actual_size = pygame.display.get_window_size()
        min_size = self.min_window_size()
        if actual_size[0] < min_size[0] or actual_size[1] < min_size[1]:
            pygame.display.flip()
            return

        '''
        self.main_tool_panel.set_pos((actual_size[0] - self.main_tool_panel.size()[0], 0))

        self.main_tool_panel.draw()

        self.toggle_grid_button.draw()
        self.toggle_grid_button.step()
        if self.toggle_grid_button.is_mouse_down():
            self.show_grid = not self.show_grid

        self.speed_increase_button.draw()
        self.speed_increase_button.step()
        if self.speed_increase_button.is_mouse_down():
            if self.delay > 0.01:
                self.delay -= 0.01

        self.speed_decrease_button.draw()
        self.speed_decrease_button.step()
        if self.speed_decrease_button.is_mouse_down():
            self.delay += 0.01
        '''

        imgui.begin("Imgui", True)
        imgui.text("Some text")
        imgui.end()

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

    def min_window_size(self):
        size = self.main_tool_panel.size()
        return size


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

