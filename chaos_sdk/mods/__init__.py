"""
Chaos SDK - Game Mod Integration System
========================================

This module provides tools for game mod developers to integrate
their mods with the Chaos platform, enabling rich interactions
beyond simple macros.

Architecture:
    
    ┌─────────────────┐         ┌─────────────────┐
    │   Chaos Bot     │◄───────►│   Game Mod      │
    │   (Plugin)      │ WebSocket│   (Any Engine)  │
    └────────┬────────┘         └────────┬────────┘
             │                           │
             │                           │
    ┌────────▼────────┐         ┌────────▼────────┐
    │  ChaosPlugin    │         │  ChaosModClient │
    │  (Python)       │         │  (C#/Lua/C++)   │
    └─────────────────┘         └─────────────────┘

Communication Protocol:
    - WebSocket for real-time events
    - JSON messages with typed actions
    - Bidirectional: Bot can trigger mod, Mod can trigger bot

Supported Game Engines:
    - Unity (C#)
    - Unreal Engine (C++/Blueprints)
    - Godot (GDScript/C#)
    - Custom engines (via generic SDK)
    - Minecraft (Java/Fabric/Forge)
    - Lua-based games (Garry's Mod, Roblox, etc.)

Usage (Plugin Side):
    from chaos_sdk.mods import ModBridgePlugin, mod_event
    
    class MyGamePlugin(ModBridgePlugin):
        game_id = "my_game"
        
        @mod_event("player_died")
        def on_player_died(self, data):
            return f"{data['player']} morreu!"
        
        def cmd_spawn_enemy(self, username, args, **kwargs):
            self.send_to_mod("spawn_enemy", {
                "type": "zombie",
                "count": 5,
                "triggered_by": username
            })
"""

from .bridge import ModBridgePlugin, ModConnection
from .protocol import (
    ModMessage,
    ModEvent,
    ModCommand,
    ModResponse,
    MessageType,
)
from .decorators import mod_event, mod_command, on_mod_connect, on_mod_disconnect
from .registry import ModRegistry

__all__ = [
    # Core
    "ModBridgePlugin",
    "ModConnection",
    
    # Protocol
    "ModMessage",
    "ModEvent", 
    "ModCommand",
    "ModResponse",
    "MessageType",
    
    # Decorators
    "mod_event",
    "mod_command",
    "on_mod_connect",
    "on_mod_disconnect",
    
    # Registry
    "ModRegistry",
]

__version__ = "1.0.0"
