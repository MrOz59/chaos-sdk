"""
Ações de mouse para macros.
"""
from typing import Tuple, Optional


class MouseAction:
    """Ações de mouse."""
    
    @staticmethod
    def click(button: str = "left", count: int = 1) -> dict:
        """Clica com o mouse."""
        return {"type": "mouse_click", "button": button, "count": count}
    
    @staticmethod
    def move(x: int, y: int, relative: bool = False) -> dict:
        """Move o mouse."""
        return {"type": "mouse_move", "x": x, "y": y, "relative": relative}
    
    @staticmethod
    def scroll(amount: int, horizontal: bool = False) -> dict:
        """Rola o scroll."""
        return {"type": "mouse_scroll", "amount": amount, "horizontal": horizontal}
    
    @staticmethod
    def drag(
        start: Tuple[int, int],
        end: Tuple[int, int],
        button: str = "left",
        duration: float = 0.5
    ) -> dict:
        """Arrasta o mouse."""
        return {
            "type": "mouse_drag",
            "start": start,
            "end": end,
            "button": button,
            "duration": duration
        }
