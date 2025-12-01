"""
Modelos de usuário.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Representa um usuário da plataforma."""
    
    id: str
    username: str
    display_name: str
    platform: str = "twitch"
    is_mod: bool = False
    is_subscriber: bool = False
    is_vip: bool = False
    is_broadcaster: bool = False


@dataclass  
class Viewer(User):
    """Representa um viewer no chat."""
    
    points: int = 0
    watch_time: int = 0  # em minutos
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
