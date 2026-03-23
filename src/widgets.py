import customtkinter as ctk
import time
import threading
from typing import Optional, Tuple, Callable
from config import THEME, COLORS

class GlowFrame(ctk.CTkFrame):
    """Frame with a glowing border effect."""
    def __init__(self, master, glow_color: str = COLORS["accent"], **kwargs):
        super().__init__(master, **kwargs)
        self.glow_color = glow_color
        self.configure(border_width=2, border_color=glow_color)

class PremiumCard(ctk.CTkFrame):
    """A card with a deep surface color and subtle border."""
    def __init__(self, master, **kwargs):
        defaults = {
            "fg_color": THEME["bg_card"],
            "corner_radius": 32,          # Muito mais arredondado ("fofo")
            "border_width": 2,            # Borda um pouco mais espessa
            "border_color": THEME["border"]
        }
        # Safely inject optional overrides from kwargs without duplication
        for key, default_val in defaults.items():
            kwargs.setdefault(key, default_val)
            
        super().__init__(master, **kwargs)

class AnimatedProgressBar(ctk.CTkProgressBar):
    """Progress bar with smooth transition animations (thread-safe)."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._target_value = 0
        self._current_value = 0
        self._anim_step = 0
        self._anim_steps_total = 20

    def set_animated(self, value: float, duration: float = 0.5):
        self._target_value = max(0, min(1, value))
        self._anim_start_val = self.get()
        self._anim_diff = self._target_value - self._anim_start_val
        self._anim_step = 0
        self._anim_steps_total = 20
        self._anim_interval = int((duration / self._anim_steps_total) * 1000)
        self._animate_step()

    def _animate_step(self):
        """Animate using after() for thread-safety with Tk."""
        self._anim_step += 1
        if self._anim_step > self._anim_steps_total:
            return
        try:
            new_val = self._anim_start_val + (self._anim_diff * (self._anim_step / self._anim_steps_total))
            self.set(new_val)
            self.after(self._anim_interval, self._animate_step)
        except Exception:
            pass  # Widget destroyed

class IconButton(ctk.CTkButton):
    """Button optimized for icons with a premium hover effect."""
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            corner_radius=16,          # Mais circular
            height=36,
            width=36,
            fg_color=THEME["bg_card"],
            hover_color=THEME["primary"],
            text_color=THEME["text_main"],
            **kwargs
        )

def create_glow_effect(widget, color: str = COLORS["accent"]):
    """Applies a temporary glow effect to a widget (thread-safe)."""
    try:
        original_border = widget.cget("border_color")
        widget.configure(border_color=color)
        widget.after(1000, lambda: _restore_border(widget, original_border))
    except Exception:
        pass

def _restore_border(widget, original_border):
    """Restores original border color safely."""
    try:
        widget.configure(border_color=original_border)
    except Exception:
        pass
