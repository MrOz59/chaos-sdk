"""
Mod Integration Decorators
==========================

Decorators for handling mod events and commands.
"""
from __future__ import annotations

from functools import wraps
from typing import Callable, List, Optional, Union


def mod_event(event_type: str, priority: int = 0):
    """
    Decorator to mark a method as a mod event handler.
    
    Args:
        event_type: Event type to handle (e.g., "player_died")
        priority: Handler priority (higher = called first)
    
    Example:
        class MyPlugin(ModBridgePlugin):
            @mod_event("player_died")
            def on_player_died(self, mod, event):
                return f"{event.player} morreu!"
            
            @mod_event("boss_defeated", priority=10)
            async def on_boss_defeated(self, mod, event):
                # Async handlers are supported
                await self.send_to_mod_async("celebration_effect", {})
                return f"O boss {event.data['boss_name']} foi derrotado!"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Mark the function
        wrapper._mod_event_type = event_type
        wrapper._mod_event_priority = priority
        
        return wrapper
    return decorator


def mod_command(
    command_name: str = None,
    require_mod: bool = True,
    cooldown: float = 0,
):
    """
    Decorator for commands that interact with mods.
    
    Args:
        command_name: Command name in the mod (default: method name without 'cmd_')
        require_mod: If True, command fails if no mod is connected
        cooldown: Cooldown in seconds
    
    Example:
        class MyPlugin(ModBridgePlugin):
            @mod_command("spawn_zombie")
            def cmd_zombie(self, username, args, **kwargs):
                count = int(args[0]) if args else 1
                self.send_to_mod("spawn_enemy", {
                    "type": "zombie",
                    "count": count,
                })
                return f"{username} spawnou {count} zombies!"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, username, args, **kwargs):
            # Check if mod is required and connected
            if require_mod and not self.has_connected_mod:
                return "❌ Nenhum mod conectado ao jogo!"
            
            # Check cooldown
            # (would need access to cooldown manager)
            
            return func(self, username, args, **kwargs)
        
        # Store metadata
        wrapper._mod_command = command_name or func.__name__.replace('cmd_', '')
        wrapper._require_mod = require_mod
        wrapper._cooldown = cooldown
        
        return wrapper
    return decorator


def on_mod_connect(func: Callable) -> Callable:
    """
    Decorator to mark method as mod connect handler.
    
    Example:
        class MyPlugin(ModBridgePlugin):
            @on_mod_connect
            async def handle_connect(self, mod):
                print(f"Mod connected: {mod.mod_name}")
                await self.send_to_mod_async("init", {"plugin": self.name})
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    wrapper._on_mod_connect = True
    return wrapper


def on_mod_disconnect(func: Callable) -> Callable:
    """
    Decorator to mark method as mod disconnect handler.
    
    Example:
        class MyPlugin(ModBridgePlugin):
            @on_mod_disconnect
            async def handle_disconnect(self, mod):
                await self.broadcast("O mod desconectou :(")
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    wrapper._on_mod_disconnect = True
    return wrapper


def require_capability(*capabilities: str):
    """
    Decorator to require mod capabilities for a handler.
    
    Example:
        class MyPlugin(ModBridgePlugin):
            @mod_event("custom_event")
            @require_capability("advanced_spawning", "custom_effects")
            def on_custom(self, mod, event):
                # Only called if mod has both capabilities
                pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, mod, *args, **kwargs):
            # Check capabilities
            missing = [c for c in capabilities if not mod.has_capability(c)]
            if missing:
                return None  # Silently skip
            
            return func(self, mod, *args, **kwargs)
        
        wrapper._required_capabilities = list(capabilities)
        return wrapper
    return decorator


def broadcast_result(
    template: str = None,
    to_chat: bool = True,
    to_mod: bool = False,
):
    """
    Decorator to automatically broadcast the result of an event handler.
    
    Args:
        template: Message template (uses {result} placeholder)
        to_chat: Send to chat
        to_mod: Send back to mod as show_message
    
    Example:
        class MyPlugin(ModBridgePlugin):
            @mod_event("achievement_unlocked")
            @broadcast_result(
                template="🏆 {result}",
                to_chat=True,
                to_mod=True
            )
            def on_achievement(self, mod, event):
                return f"{event.player} desbloqueou: {event.data['name']}"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, mod, *args, **kwargs):
            result = func(self, mod, *args, **kwargs)
            
            import asyncio
            if asyncio.iscoroutine(result):
                result = await result
            
            if result and isinstance(result, str):
                message = template.format(result=result) if template else result
                
                if to_chat and hasattr(self, 'context') and self.context:
                    await self.context.send_chat(message)
                
                if to_mod:
                    self.send_to_mod("show_message", {
                        "text": message,
                        "duration": 5.0,
                    })
            
            return result
        
        return wrapper
    return decorator
