import pygame
import numpy as np
from themes import THEMES

class Minimap:
    def __init__(self, x, y, width, height, grid_size, theme="classic"):
        self.rect = pygame.Rect(x, y, width, height)
        self.grid_size = grid_size
        self.theme = theme
        self.cell_size = min(width // grid_size[1], height // grid_size[0])
        self.offset_x = 0
        self.offset_y = 0
        self.zoom_level = 1

    def update(self, offset_x, offset_y, zoom_level):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.zoom_level = zoom_level

    def draw(self, screen, grid):
        # Draw minimap background
        pygame.draw.rect(screen, THEMES[self.theme]["menu"], self.rect)
        pygame.draw.rect(screen, THEMES[self.theme]["menu_text"], self.rect, 2)

        # Draw cells (2D support)
        for x in range(self.grid_size[0]):
            for y in range(self.grid_size[1]):
                if grid[x][y] > 0:
                    cell_rect = pygame.Rect(
                        self.rect.x + y * self.cell_size,
                        self.rect.y + x * self.cell_size,
                        self.cell_size,
                        self.cell_size
                    )
                    pygame.draw.rect(screen, THEMES[self.theme]["cell"], cell_rect)

        # Draw viewport rectangle
        # view_width = (self.rect.width / self.zoom_level)
        # view_height = (self.rect.height / self.zoom_level)
        # view_x = self.rect.x + (-self.offset_x / self.zoom_level)
        # view_y = self.rect.y + (-self.offset_y / self.zoom_level)
        # 
        # view_rect = pygame.Rect(
        #     view_x,
        #     view_y,
        #     view_width,
        #     view_height
        # )
        # pygame.draw.rect(screen, THEMES[self.theme]["button_hover"], view_rect, 2)

class CellTransition:
    def __init__(self, duration=0.2):
        self.duration = duration
        self.transitions = {}

    def start_transition(self, x, y, start_value, end_value):
        self.transitions[(x, y)] = {
            'start': start_value,
            'end': end_value,
            'progress': 0
        }

    def update(self, dt):
        to_remove = []
        for pos, transition in self.transitions.items():
            transition['progress'] += dt / self.duration
            if transition['progress'] >= 1:
                to_remove.append(pos)
        
        for pos in to_remove:
            del self.transitions[pos]

    def get_value(self, x, y):
        if (x, y) in self.transitions:
            t = self.transitions[(x, y)]
            progress = t['progress']
            return t['start'] + (t['end'] - t['start']) * progress
        return None

class GridOverlay:
    def __init__(self, cell_size, theme="classic"):
        self.cell_size = cell_size
        self.theme = theme
        self.show_coordinates = True
        self.show_quadrants = True

    def draw(self, screen, offset_x, offset_y, width, height):
        if not self.show_coordinates and not self.show_quadrants:
            return

        # Draw coordinates
        if self.show_coordinates:
            for x in range(0, width, self.cell_size):
                text = str(int((x - offset_x) / self.cell_size))
                text_surface = pygame.font.SysFont("Arial", 12).render(text, True, THEMES[self.theme]["text"])
                screen.blit(text_surface, (x, 0))
            
            for y in range(0, height, self.cell_size):
                text = str(int((y - offset_y) / self.cell_size))
                text_surface = pygame.font.SysFont("Arial", 12).render(text, True, THEMES[self.theme]["text"])
                screen.blit(text_surface, (0, y))

        # Draw quadrants
        if self.show_quadrants:
            center_x = width // 2
            center_y = height // 2
            pygame.draw.line(screen, THEMES[self.theme]["grid"], (center_x, 0), (center_x, height), 2)
            pygame.draw.line(screen, THEMES[self.theme]["grid"], (0, center_y), (width, center_y), 2)

def get_enhanced_age_color(age, theme="classic"):
    """Enhanced color function with smoother transitions and more vibrant colors"""
    if age <= 0:
        return THEMES[theme]["background"]
    
    if theme == "classic":
        # Smooth transition from green to yellow to red
        if age < 5:
            return (0, 100 + age * 30, 0)
        elif age < 10:
            return (age * 25, 255, 0)
        elif age < 15:
            return (255, 255 - (age - 10) * 25, 0)
        else:
            return (255, 0, 0)
    
    elif theme == "neon":
        # Glowing effect with color cycling
        hue = (age * 20) % 360
        color = pygame.Color(0, 0, 0)
        color.hsva = (hue, 100, 100, 100)
        return color
    
    elif theme == "pastel":
        # Soft pastel colors
        if age < 5:
            return (255, 200 - age * 20, 200 - age * 20)
        elif age < 10:
            return (255, 150 - age * 10, 150 - age * 10)
        else:
            return (255, 100, 100) 