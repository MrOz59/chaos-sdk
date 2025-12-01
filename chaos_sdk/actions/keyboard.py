"""
Ações de teclado para macros.
"""
from typing import List, Optional


class KeyboardAction:
    """Ações de teclado."""
    
    @staticmethod
    def press(key: str, duration: float = 0.1) -> dict:
        """Pressiona uma tecla."""
        return {"type": "key_press", "key": key, "duration": duration}
    
    @staticmethod
    def hold(key: str, duration: float = 1.0) -> dict:
        """Segura uma tecla por um tempo."""
        return {"type": "key_hold", "key": key, "duration": duration}
    
    @staticmethod
    def release(key: str) -> dict:
        """Solta uma tecla."""
        return {"type": "key_release", "key": key}
    
    @staticmethod
    def type_text(text: str, delay: float = 0.05) -> dict:
        """Digita um texto."""
        return {"type": "type_text", "text": text, "delay": delay}
    
    @staticmethod
    def combo(keys: List[str]) -> dict:
        """Executa combo de teclas (ex: Ctrl+C)."""
        return {"type": "key_combo", "keys": keys}
