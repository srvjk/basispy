import pygame


def darken(color):
    return tuple(0.8*x for x in color)


def lighten(color):
    return tuple(min(1.2*x, 255) for x in color)


class Button:
    def __init__(self, screen, rect, caption):
        self.rect = rect
        self.caption = caption
        self.screen = screen
        self.base_color = (0, 100, 100)
        self.mouse_down_color = darken(self.base_color)
        self.base_text_color = (200, 200, 200)
        self.mouse_down_text_color = darken(self.base_text_color)
        self.font = pygame.font.SysFont('Courier New', 12)
        self.prev_pressed = False
        self.now_pressed = False
        self.mouse_down = False
        self.mouse_up = False

    def step(self):
        self.now_pressed = False
        self.mouse_down = False
        self.mouse_up = False
        pressed_mouse_buttons = pygame.mouse.get_pressed()
        if pressed_mouse_buttons[0]:
            pos = pygame.mouse.get_pos()
            if self.rect.collidepoint(pos):
                self.now_pressed = True
        if self.now_pressed:
            if not self.prev_pressed:
                self.mouse_down = True
        else:
            if self.prev_pressed:
                self.mouse_up = True
        self.prev_pressed = self.now_pressed

    def is_mouse_down(self):
        return self.mouse_down

    def is_mouse_up(self):
        return self.mouse_up

    def draw(self):
        if not self.screen:
            return

        color = self.base_color
        text_color = self.base_text_color
        if self.now_pressed:
            color = self.mouse_down_color
            text_color = self.mouse_down_text_color

        pygame.draw.rect(self.screen, color, self.rect)

        text_surface = self.font.render(self.caption, False, text_color)
        self.screen.blit(text_surface, self.rect.topleft)

