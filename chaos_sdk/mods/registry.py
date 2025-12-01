"""
Mod Registry
============

Central registry for game mod integrations.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GameModInfo:
    """Information about a registered game mod."""
    
    game_id: str
    game_name: str
    description: str = ""
    
    # Supported features
    supported_events: List[str] = field(default_factory=list)
    supported_commands: List[str] = field(default_factory=list)
    
    # SDK availability
    sdk_languages: List[str] = field(default_factory=list)  # e.g., ["csharp", "lua"]
    sdk_download_url: str = ""
    documentation_url: str = ""
    
    # Metadata
    icon_url: str = ""
    category: str = "other"  # action, adventure, survival, etc.
    
    # Stats
    active_connections: int = 0


class ModRegistry:
    """
    Central registry for game mod integrations.
    
    This tracks which games have mod support and what
    capabilities each mod provides.
    """
    
    _instance: Optional['ModRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._games: Dict[str, GameModInfo] = {}
            cls._instance._init_builtin_games()
        return cls._instance
    
    def _init_builtin_games(self):
        """Initialize with built-in game support."""
        
        # Minecraft
        self.register_game(GameModInfo(
            game_id="minecraft",
            game_name="Minecraft",
            description="Integração com Minecraft Java Edition via Fabric/Forge",
            supported_events=[
                "player_joined", "player_left", "player_died",
                "player_respawned", "item_collected", "enemy_killed",
                "boss_defeated", "achievement_unlocked", "chat_message",
            ],
            supported_commands=[
                "spawn_enemy", "give_item", "teleport_player",
                "change_weather", "change_time", "show_message",
                "play_sound", "spawn_effect", "set_difficulty",
            ],
            sdk_languages=["java"],
            category="survival",
        ))
        
        # GTA V (FiveM/RageMP)
        self.register_game(GameModInfo(
            game_id="gtav",
            game_name="GTA V",
            description="Integração com GTA V via FiveM ou RageMP",
            supported_events=[
                "player_died", "player_respawned", "vehicle_destroyed",
                "mission_completed", "wanted_level_changed",
            ],
            supported_commands=[
                "spawn_vehicle", "spawn_ped", "give_weapon",
                "teleport_player", "set_weather", "set_wanted_level",
                "show_message", "play_sound",
            ],
            sdk_languages=["lua", "csharp"],
            category="action",
        ))
        
        # Terraria
        self.register_game(GameModInfo(
            game_id="terraria",
            game_name="Terraria",
            description="Integração com Terraria via tModLoader",
            supported_events=[
                "player_died", "boss_spawned", "boss_defeated",
                "item_collected", "npc_killed", "invasion_started",
            ],
            supported_commands=[
                "spawn_enemy", "spawn_boss", "give_item",
                "spawn_invasion", "change_time", "show_message",
            ],
            sdk_languages=["csharp"],
            category="survival",
        ))
        
        # Garry's Mod
        self.register_game(GameModInfo(
            game_id="gmod",
            game_name="Garry's Mod",
            description="Integração com Garry's Mod via Lua",
            supported_events=[
                "player_died", "player_spawned", "prop_spawned",
                "round_started", "round_ended",
            ],
            supported_commands=[
                "spawn_entity", "spawn_npc", "give_weapon",
                "spawn_effect", "play_sound", "show_message",
            ],
            sdk_languages=["lua"],
            category="sandbox",
        ))
        
        # Unity (Generic)
        self.register_game(GameModInfo(
            game_id="unity",
            game_name="Unity Game",
            description="SDK genérico para jogos Unity",
            supported_events=["custom"],
            supported_commands=["custom"],
            sdk_languages=["csharp"],
            category="other",
        ))
        
        # Unreal Engine (Generic)
        self.register_game(GameModInfo(
            game_id="unreal",
            game_name="Unreal Engine Game",
            description="SDK genérico para jogos Unreal Engine",
            supported_events=["custom"],
            supported_commands=["custom"],
            sdk_languages=["cpp", "blueprints"],
            category="other",
        ))
        
        # Godot (Generic)
        self.register_game(GameModInfo(
            game_id="godot",
            game_name="Godot Game",
            description="SDK genérico para jogos Godot",
            supported_events=["custom"],
            supported_commands=["custom"],
            sdk_languages=["gdscript", "csharp"],
            category="other",
        ))
    
    def register_game(self, info: GameModInfo):
        """Register a game for mod support."""
        self._games[info.game_id] = info
        logger.debug(f"Registered game: {info.game_name} ({info.game_id})")
    
    def get_game(self, game_id: str) -> Optional[GameModInfo]:
        """Get info about a registered game."""
        return self._games.get(game_id)
    
    def list_games(self) -> List[GameModInfo]:
        """List all registered games."""
        return list(self._games.values())
    
    def list_games_by_category(self, category: str) -> List[GameModInfo]:
        """List games by category."""
        return [g for g in self._games.values() if g.category == category]
    
    def get_supported_events(self, game_id: str) -> List[str]:
        """Get events supported by a game."""
        game = self.get_game(game_id)
        return game.supported_events if game else []
    
    def get_supported_commands(self, game_id: str) -> List[str]:
        """Get commands supported by a game."""
        game = self.get_game(game_id)
        return game.supported_commands if game else []
    
    def update_connections(self, game_id: str, delta: int):
        """Update active connection count."""
        game = self.get_game(game_id)
        if game:
            game.active_connections = max(0, game.active_connections + delta)


# Global instance
registry = ModRegistry()
