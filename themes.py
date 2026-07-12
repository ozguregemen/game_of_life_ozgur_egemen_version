import pygame

# Color themes
THEMES = {
    "classic": {
        "background": (0, 0, 0),
        "grid": (40, 40, 40),
        "cell": (0, 255, 0),
        "text": (255, 255, 255),
        "info_bar": (30, 30, 30),
        "stats_bar": (20, 20, 20),
        "menu": (50, 50, 50),
        "menu_text": (200, 200, 200),
        "button": (60, 60, 60),
        "button_hover": (80, 80, 80),
        "button_text": (255, 255, 255)
    },
    "neon": {
        "background": (0, 0, 0),
        "grid": (30, 0, 30),
        "cell": (0, 255, 255),
        "text": (255, 255, 255),
        "info_bar": (20, 0, 20),
        "stats_bar": (15, 0, 15),
        "menu": (40, 0, 40),
        "menu_text": (255, 200, 255),
        "button": (50, 0, 50),
        "button_hover": (70, 0, 70),
        "button_text": (255, 255, 255)
    },
    "pastel": {
        "background": (255, 255, 255),
        "grid": (200, 200, 200),
        "cell": (255, 182, 193),
        "text": (100, 100, 100),
        "info_bar": (240, 240, 240),
        "stats_bar": (230, 230, 230),
        "menu": (245, 245, 245),
        "menu_text": (80, 80, 80),
        "button": (220, 220, 220),
        "button_hover": (200, 200, 200),
        "button_text": (100, 100, 100)
    }
}

# Age-based colors (for cell age visualization)
def get_age_color(age, theme="classic"):
    if theme == "classic":
        if age <= 0:
            return THEMES[theme]["background"]
        elif age < 5:
            return (0, 100 + age * 30, 0)
        elif age < 10:
            return (age * 20, 255, 0)
        else:
            return (255, 255, 0)
    elif theme == "neon":
        if age <= 0:
            return THEMES[theme]["background"]
        elif age < 5:
            return (0, 100 + age * 30, 100 + age * 30)
        elif age < 10:
            return (age * 20, 255, 255)
        else:
            return (255, 255, 255)
    elif theme == "pastel":
        if age <= 0:
            return THEMES[theme]["background"]
        elif age < 5:
            return (255, 200 - age * 20, 200 - age * 20)
        elif age < 10:
            return (255, 150 - age * 10, 150 - age * 10)
        else:
            return (255, 100, 100)

# Button class for UI elements
class Button:
    def __init__(self, x, y, width, height, text, theme="classic"):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.theme = theme
        self.is_hovered = False

    def draw(self, screen, font):
        color = THEMES[self.theme]["button_hover"] if self.is_hovered else THEMES[self.theme]["button"]
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, THEMES[self.theme]["button_text"], self.rect, 2)
        
        text_surface = font.render(self.text, True, THEMES[self.theme]["button_text"])
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered:
                return True
        return False

# Menu class for UI elements
class Menu:
    def __init__(self, x, y, width, height, theme="classic"):
        self.rect = pygame.Rect(x, y, width, height)
        self.theme = theme
        self.buttons = []
        self.visible = False

    def add_button(self, text, callback):
        button_height = 30
        button_margin = 5
        y = self.rect.y + len(self.buttons) * (button_height + button_margin) + 10
        self.buttons.append({
            "button": Button(self.rect.x + 10, y, self.rect.width - 20, button_height, text, self.theme),
            "callback": callback
        })

    def draw(self, screen, font):
        if not self.visible:
            return

        # Draw menu background
        pygame.draw.rect(screen, THEMES[self.theme]["menu"], self.rect)
        pygame.draw.rect(screen, THEMES[self.theme]["menu_text"], self.rect, 2)

        # Draw buttons
        for button_data in self.buttons:
            button_data["button"].draw(screen, font)

    def handle_event(self, event):
        if not self.visible:
            return

        for button_data in self.buttons:
            if button_data["button"].handle_event(event):
                button_data["callback"]()
                return True
        return False 