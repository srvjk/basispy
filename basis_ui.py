import pygame
from enum import Enum

def darken(color):
    return tuple(0.8*x for x in color)


def lighten(color):
    return tuple(min(1.2*x, 255) for x in color)


class Panel:
    def __init__(self, screen, rect):
        self.screen = screen
        self.rect = rect
        self.base_color = (10, 10, 10)

    def draw(self):
        pygame.draw.rect(self.screen, self.base_color, self.rect)

    def size(self):
        return self.rect.size

    def width(self):
        return self.rect.width

    def height(self):
        return self.rect.height

    def set_pos(self, pos):
        self.rect.topleft = pos


class CaptionPolicy(Enum):
    Clip = 1,
    Fit = 2


class HorAlignment(Enum):
    Center = 1,
    Left = 2,
    Right = 3


class Button:
    def __init__(self, panel, rect, caption):
        self.panel = panel
        self.rect = rect
        self.caption = caption
        self.base_color = (0, 100, 100)
        self.base_text_color = (200, 200, 200)
        self.mouse_down_color = darken(self.base_color)
        self.mouse_down_text_color = darken(self.base_text_color)
        self.preferred_text_size = 12
        self.font = pygame.font.SysFont('Courier New', self.preferred_text_size)
        self.prev_pressed = False
        self.now_pressed = False
        self.mouse_down = False
        self.mouse_up = False
        self.caption_policy = CaptionPolicy.Clip
        self.caption_margins = (0, 0)
        self.set_size(self.rect.size)

    def step(self):
        if not self.panel:
            return

        rect = self.rect.copy()
        rect.left += self.panel.rect.left
        rect.top += self.panel.rect.top

        self.now_pressed = False
        self.mouse_down = False
        self.mouse_up = False
        pressed_mouse_buttons = pygame.mouse.get_pressed()
        if pressed_mouse_buttons[0]:
            pos = pygame.mouse.get_pos()
            if rect.collidepoint(pos):
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
        if not self.panel:
            return

        color = self.base_color
        text_color = self.base_text_color

        if self.now_pressed:
            color = self.mouse_down_color
            text_color = self.mouse_down_text_color

        rect = self.rect.copy()
        rect.left += self.panel.rect.left
        rect.top += self.panel.rect.top

        pygame.draw.rect(self.panel.screen, color, rect)

        text_surface = self.font.render(self.caption, False, text_color)
        self.panel.screen.blit(text_surface, (rect.left + self.caption_margins[0], rect.top + self.caption_margins[1]))

    def size(self):
        return self.rect.size

    def set_size(self, new_size):
        self.rect.size = new_size
        if self.caption_policy == CaptionPolicy.Clip:
            text_size = self.font.size(self.caption)
            hor_margin = (self.rect.width - text_size[0]) / 2.0
            ver_margin = (self.rect.height - text_size[1]) / 2.0
            self.caption_margins = (hor_margin, ver_margin)

