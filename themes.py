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
    },
    "colorblind": {
        "background": (16, 24, 32),
        "grid": (72, 83, 94),
        "cell": (240, 228, 66),
        "text": (250, 250, 250),
        "info_bar": (25, 35, 45),
        "stats_bar": (20, 29, 38),
        "menu": (31, 43, 54),
        "menu_text": (230, 236, 240),
        "button": (43, 58, 70),
        "button_hover": (57, 76, 90),
        "button_text": (255, 255, 255)
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
    elif theme == "colorblind":
        if age <= 0:
            return THEMES[theme]["background"]
        brightness = min(1.0, 0.58 + age * 0.035)
        return tuple(int(channel * brightness) for channel in THEMES[theme]["cell"])

# Button class for UI elements
class Button:
    def __init__(
        self,
        x,
        y,
        width,
        height,
        text,
        theme="classic",
        accent=None,
        active=False,
        tooltip="",
    ):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.theme = theme
        self.accent = accent
        self.active = active
        self.tooltip = tooltip
        self.is_hovered = False

    def draw(self, screen, font):
        color = THEMES[self.theme]["button_hover"] if self.is_hovered else THEMES[self.theme]["button"]
        pygame.draw.rect(screen, color, self.rect)
        border_color = (
            self.accent
            if self.active and self.accent is not None
            else THEMES[self.theme]["button_text"]
        )
        pygame.draw.rect(screen, border_color, self.rect, 3 if self.active else 2)

        if self.accent is not None:
            swatch = pygame.Rect(
                self.rect.x + 8,
                self.rect.centery - 5,
                10,
                10,
            )
            pygame.draw.rect(screen, self.accent, swatch)
        
        text_surface = font.render(self.text, True, THEMES[self.theme]["button_text"])
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                return True
        return False

# Menu class for UI elements
class Menu:
    def __init__(self, x, y, width, height, theme="classic"):
        self.rect = pygame.Rect(x, y, width, height)
        self.theme = theme
        self.buttons = []
        self.visible = False
        self.header_text = ""
        self.header_height = 54
        self.button_height = 26
        self.button_margin = 2
        self.section_height = 23
        self.sections = []
        self.active_section = None
        self._expanded_state = {}
        self._hover_token = None
        self._hover_started = 0

    def set_header(self, text):
        self.header_text = text
        self.relayout()

    def clear_buttons(self):
        self.buttons.clear()
        self.sections.clear()
        self.active_section = None

    def begin_section(self, key, title, *, expanded=True, tooltip=""):
        """Start a persistent collapsible group for subsequent buttons."""
        section = {
            "key": key,
            "title": title,
            "expanded": self._expanded_state.get(key, expanded),
            "tooltip": tooltip,
            "rect": pygame.Rect(0, 0, 0, 0),
            "hovered": False,
        }
        self.sections.append(section)
        self.active_section = key
        self.relayout()

    def add_button(
        self,
        text,
        callback,
        *,
        accent=None,
        active=False,
        tooltip="",
    ):
        top = self.rect.y + (self.header_height if self.header_text else 10)
        y = top + len(self.buttons) * (self.button_height + self.button_margin)
        self.buttons.append({
            "button": Button(
                self.rect.x + 10,
                y,
                self.rect.width - 20,
                self.button_height,
                text,
                self.theme,
                accent,
                active,
                tooltip or f"Activate: {text}",
            ),
            "callback": callback,
            "section": self.active_section,
            "visible": True,
        })
        self.relayout()

    def _section(self, key):
        return next((section for section in self.sections if section["key"] == key), None)

    def toggle_section(self, key):
        section = self._section(key)
        if section is None:
            return False
        section["expanded"] = not section["expanded"]
        self._expanded_state[key] = section["expanded"]
        self.relayout()
        return True

    def relayout(self):
        top = self.rect.y + (self.header_height if self.header_text else 10)
        count = len(self.buttons)
        if not count:
            return
        available_height = max(1, self.rect.bottom - top - 8)
        margin = self.button_margin
        section_space = len(self.sections) * (self.section_height + margin)
        visible_count = sum(
            1
            for button_data in self.buttons
            if button_data["section"] is None
            or (
                self._section(button_data["section"]) is not None
                and self._section(button_data["section"])["expanded"]
            )
        )
        fitted_height = min(
            self.button_height,
            max(
                12,
                (
                    available_height
                    - section_space
                    - margin * max(0, visible_count - 1)
                )
                // max(1, visible_count),
            ),
        )
        y = top
        unsectioned = [data for data in self.buttons if data["section"] is None]
        for button_data in unsectioned:
            self._place_button(button_data, y, fitted_height)
            y += fitted_height + margin
        for section in self.sections:
            section["rect"] = pygame.Rect(
                self.rect.x + 8,
                y,
                self.rect.width - 16,
                self.section_height,
            )
            y += self.section_height + margin
            for button_data in self.buttons:
                if button_data["section"] != section["key"]:
                    continue
                button_data["visible"] = section["expanded"]
                if section["expanded"]:
                    self._place_button(button_data, y, fitted_height)
                    y += fitted_height + margin
                else:
                    button_data["button"].rect = pygame.Rect(
                        self.rect.x + 10,
                        y,
                        self.rect.width - 20,
                        0,
                    )

    def _place_button(self, button_data, y, height):
        button_data["visible"] = True
        button = button_data["button"]
        button.rect = pygame.Rect(
            self.rect.x + 10,
            y,
            self.rect.width - 20,
            height,
        )

    def draw(self, screen, font):
        if not self.visible:
            return

        # Draw menu background
        pygame.draw.rect(screen, THEMES[self.theme]["menu"], self.rect)
        pygame.draw.rect(screen, THEMES[self.theme]["menu_text"], self.rect, 2)

        if self.header_text:
            heading = font.render(
                self.header_text,
                True,
                THEMES[self.theme]["menu_text"],
            )
            screen.blit(heading, (self.rect.x + 12, self.rect.y + 14))
            pygame.draw.line(
                screen,
                THEMES[self.theme]["menu_text"],
                (self.rect.x + 10, self.rect.y + self.header_height - 9),
                (self.rect.right - 10, self.rect.y + self.header_height - 9),
                1,
            )

        for section in self.sections:
            color = (
                THEMES[self.theme]["button_hover"]
                if section["hovered"]
                else THEMES[self.theme]["stats_bar"]
            )
            pygame.draw.rect(screen, color, section["rect"], border_radius=4)
            marker = "-" if section["expanded"] else "+"
            label = font.render(
                f"{marker}  {section['title']}",
                True,
                THEMES[self.theme]["menu_text"],
            )
            screen.blit(label, (section["rect"].x + 8, section["rect"].y + 4))

        for button_data in self.buttons:
            if button_data["visible"]:
                button_data["button"].draw(screen, font)
        self._draw_tooltip(screen, font)

    def _draw_tooltip(self, screen, font):
        if self._hover_token is None or pygame.time.get_ticks() - self._hover_started < 450:
            return
        text = ""
        anchor = None
        if self._hover_token[0] == "section":
            section = self._section(self._hover_token[1])
            if section is not None:
                text = section["tooltip"] or f"Expand or collapse {section['title']}."
                anchor = section["rect"]
        else:
            index = self._hover_token[1]
            if 0 <= index < len(self.buttons):
                button = self.buttons[index]["button"]
                text = button.tooltip
                anchor = button.rect
        if not text or anchor is None:
            return
        max_width = min(280, max(160, self.rect.x - 20))
        words = text.split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and font.size(candidate)[0] > max_width - 20:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        width = min(max_width, max(font.size(line)[0] for line in lines) + 20)
        height = len(lines) * (font.get_height() + 2) + 14
        box = pygame.Rect(anchor.x - width - 8, anchor.y, width, height)
        box.clamp_ip(screen.get_rect())
        overlay = pygame.Surface(box.size, pygame.SRCALPHA)
        overlay.fill((15, 20, 28, 238))
        screen.blit(overlay, box)
        pygame.draw.rect(screen, (205, 215, 225), box, 1, border_radius=5)
        for index, line in enumerate(lines):
            screen.blit(
                font.render(line, True, (245, 247, 250)),
                (box.x + 10, box.y + 7 + index * (font.get_height() + 2)),
            )

    def _set_hover_token(self, token):
        if token != self._hover_token:
            self._hover_token = token
            self._hover_started = pygame.time.get_ticks()

    def handle_event(self, event):
        if not self.visible:
            return

        if event.type == pygame.MOUSEMOTION:
            token = None
            for section in self.sections:
                section["hovered"] = section["rect"].collidepoint(event.pos)
                if section["hovered"]:
                    token = ("section", section["key"])
            for index, button_data in enumerate(self.buttons):
                if button_data["visible"]:
                    button_data["button"].handle_event(event)
                    if button_data["button"].is_hovered:
                        token = ("button", index)
                else:
                    button_data["button"].is_hovered = False
            self._set_hover_token(token)
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for section in self.sections:
                if section["rect"].collidepoint(event.pos):
                    return self.toggle_section(section["key"])

        for button_data in self.buttons:
            if button_data["visible"] and button_data["button"].handle_event(event):
                button_data["callback"]()
                return True
        return False
