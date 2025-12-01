"""
Mod Bridge Plugin
=================

Base class for plugins that communicate with game mods.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from ..core.plugin import BasePlugin
from .protocol import (
    ModMessage, 
    ModEvent, 
    ModCommand, 
    ModResponse,
    MessageType,
    HandshakeMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class ModConnection:
    """Represents a connected game mod."""
    
    mod_id: str
    game_id: str
    game_name: str
    mod_name: str
    mod_version: str
    protocol_version: str
    capabilities: List[str]
    
    # Connection state
    connected_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)
    is_alive: bool = True
    
    # WebSocket reference (set by bridge)
    websocket: Any = None
    
    # Stats
    messages_sent: int = 0
    messages_received: int = 0
    commands_pending: Dict[str, float] = field(default_factory=dict)
    
    def has_capability(self, cap: str) -> bool:
        """Check if mod has a capability."""
        return cap in self.capabilities
    
    @property
    def latency_ms(self) -> float:
        """Estimated latency based on ping."""
        return (time.time() - self.last_ping) * 1000


class ModBridgePlugin(BasePlugin):
    """
    Base class for plugins that bridge Chaos with game mods.
    
    Example:
        class MinecraftPlugin(ModBridgePlugin):
            name = "Minecraft Chaos"
            game_id = "minecraft"
            
            @mod_event("player_died")
            def on_player_died(self, mod: ModConnection, event: ModEvent):
                return f"{event.player} morreu no Minecraft!"
            
            def cmd_spawn(self, username, args, **kwargs):
                self.send_to_mod("spawn_enemy", {
                    "type": args[0] if args else "zombie",
                    "count": int(args[1]) if len(args) > 1 else 1,
                })
                return f"{username} spawnou inimigos!"
    """
    
    # Override in subclass
    game_id: str = "unknown"
    
    # Auto-set
    required_permissions = ["mod:bridge", "chat:send"]
    
    def __init__(self):
        super().__init__()
        
        # Connected mods
        self._mods: Dict[str, ModConnection] = {}
        
        # Event handlers (set by decorators)
        self._event_handlers: Dict[str, Callable] = {}
        
        # Pending command responses
        self._pending_commands: Dict[str, asyncio.Future] = {}
        
        # Collect decorated methods
        self._collect_handlers()
    
    def _collect_handlers(self):
        """Collect methods decorated with @mod_event."""
        for name in dir(self):
            method = getattr(self, name, None)
            if callable(method):
                if hasattr(method, '_mod_event_type'):
                    event_type = method._mod_event_type
                    self._event_handlers[event_type] = method
                    logger.debug(f"Registered event handler: {event_type} -> {name}")
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    @property
    def connected_mods(self) -> List[ModConnection]:
        """Get list of connected mods."""
        return [m for m in self._mods.values() if m.is_alive]
    
    @property
    def has_connected_mod(self) -> bool:
        """Check if any mod is connected."""
        return len(self.connected_mods) > 0
    
    def get_mod(self, mod_id: str) -> Optional[ModConnection]:
        """Get a specific mod by ID."""
        return self._mods.get(mod_id)
    
    async def handle_mod_connect(self, websocket, handshake: HandshakeMessage):
        """Handle a new mod connection."""
        mod = ModConnection(
            mod_id=handshake.mod_id or f"{handshake.game_id}_{handshake.mod_name}",
            game_id=handshake.game_id,
            game_name=handshake.game_name,
            mod_name=handshake.mod_name,
            mod_version=handshake.mod_version,
            protocol_version=handshake.protocol_version,
            capabilities=handshake.capabilities,
            websocket=websocket,
        )
        
        self._mods[mod.mod_id] = mod
        
        # Send acknowledgment
        ack = ModMessage(
            type=MessageType.HANDSHAKE_ACK,
            game_id=self.game_id,
            data={
                'status': 'connected',
                'server_time': time.time(),
                'plugin_name': self.name,
                'plugin_version': self.version,
            }
        )
        await self._send_raw(mod, ack)
        
        # Call hook
        await self.on_mod_connected(mod)
        
        logger.info(f"Mod connected: {mod.mod_name} v{mod.mod_version} ({mod.game_name})")
        
        return mod
    
    async def handle_mod_disconnect(self, mod_id: str):
        """Handle mod disconnection."""
        mod = self._mods.pop(mod_id, None)
        if mod:
            mod.is_alive = False
            await self.on_mod_disconnected(mod)
            logger.info(f"Mod disconnected: {mod.mod_name}")
    
    async def on_mod_connected(self, mod: ModConnection):
        """Called when a mod connects. Override for custom logic."""
        pass
    
    async def on_mod_disconnected(self, mod: ModConnection):
        """Called when a mod disconnects. Override for custom logic."""
        pass
    
    # =========================================================================
    # Message Handling
    # =========================================================================
    
    async def handle_message(self, mod: ModConnection, message: ModMessage):
        """Handle incoming message from mod."""
        mod.messages_received += 1
        mod.last_ping = time.time()
        
        msg_type = message.type
        
        if msg_type == MessageType.PING:
            await self._send_raw(mod, ModMessage(
                type=MessageType.PONG,
                game_id=self.game_id,
                data={'server_time': time.time()}
            ))
        
        elif msg_type == MessageType.EVENT:
            await self._handle_event(mod, message)
        
        elif msg_type == MessageType.COMMAND_RESULT:
            self._handle_command_result(message)
        
        elif msg_type == MessageType.STATE_UPDATE:
            await self.on_state_update(mod, message.data)
        
        elif msg_type == MessageType.DISCONNECT:
            await self.handle_mod_disconnect(mod.mod_id)
        
        elif msg_type == MessageType.ERROR:
            logger.error(f"Mod error from {mod.mod_name}: {message.data}")
    
    async def _handle_event(self, mod: ModConnection, message: ModMessage):
        """Handle an event from mod."""
        event_type = message.data.get('event_type', '')
        event_data = message.data.get('event_data', {})
        
        event = ModEvent(
            event_type=event_type,
            data=event_data,
            player=message.data.get('player'),
            position=message.data.get('position'),
        )
        
        # Find handler
        handler = self._event_handlers.get(event_type)
        
        if handler:
            try:
                result = handler(mod, event)
                if asyncio.iscoroutine(result):
                    result = await result
                
                # Send acknowledgment
                await self._send_raw(mod, ModMessage(
                    type=MessageType.EVENT_ACK,
                    game_id=self.game_id,
                    data={
                        'original_id': message.id,
                        'handled': True,
                        'result': result,
                    }
                ))
                
                # If handler returned a string, send to chat
                if isinstance(result, str) and result:
                    await self._broadcast_chat(result)
                    
            except Exception as e:
                logger.exception(f"Error handling event {event_type}")
                await self._send_raw(mod, ModMessage(
                    type=MessageType.EVENT_ACK,
                    game_id=self.game_id,
                    data={
                        'original_id': message.id,
                        'handled': False,
                        'error': str(e),
                    }
                ))
        else:
            # No specific handler, call generic
            await self.on_mod_event(mod, event)
    
    def _handle_command_result(self, message: ModMessage):
        """Handle command result from mod."""
        original_id = message.data.get('original_id')
        if original_id in self._pending_commands:
            future = self._pending_commands.pop(original_id)
            
            response = ModResponse(
                success=message.data.get('success', False),
                message=message.data.get('message', ''),
                data=message.data.get('response_data', {}),
                error_code=message.data.get('error_code'),
                execution_time=message.data.get('execution_time', 0),
            )
            
            if not future.done():
                future.set_result(response)
    
    async def on_mod_event(self, mod: ModConnection, event: ModEvent):
        """Called for unhandled events. Override for generic handling."""
        logger.debug(f"Unhandled event from {mod.mod_name}: {event.event_type}")
    
    async def on_state_update(self, mod: ModConnection, state: Dict[str, Any]):
        """Called when mod sends state update. Override for custom logic."""
        pass
    
    # =========================================================================
    # Sending Commands to Mod
    # =========================================================================
    
    def send_to_mod(
        self, 
        command: str, 
        params: Dict[str, Any] = None,
        mod_id: str = None,
        triggered_by: str = "",
        priority: int = 0,
        timeout: float = 30.0,
    ) -> Optional[asyncio.Future]:
        """
        Send a command to the game mod.
        
        Args:
            command: Command name (e.g., "spawn_enemy")
            params: Command parameters
            mod_id: Specific mod to target (or all if None)
            triggered_by: Username who triggered this
            priority: Higher = more urgent
            timeout: Seconds to wait for response
        
        Returns:
            Future that resolves to ModResponse, or None if no mods connected
        
        Example:
            future = self.send_to_mod("spawn_enemy", {
                "type": "zombie",
                "count": 5,
            }, triggered_by=username)
            
            # Optionally wait for result
            response = await future
            if response.success:
                return "Spawned!"
        """
        if not self.has_connected_mod:
            logger.warning(f"No mods connected to receive command: {command}")
            return None
        
        cmd = ModCommand(
            command=command,
            params=params or {},
            priority=priority,
            timeout=timeout,
            triggered_by=triggered_by,
        )
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        
        # Send to specific mod or all
        target_mods = []
        if mod_id:
            mod = self.get_mod(mod_id)
            if mod:
                target_mods = [mod]
        else:
            target_mods = self.connected_mods
        
        for mod in target_mods:
            message = cmd.to_message(self.game_id, mod.mod_id)
            self._pending_commands[message.id] = future
            
            # Schedule timeout
            asyncio.get_event_loop().call_later(
                timeout,
                lambda mid=message.id: self._command_timeout(mid)
            )
            
            # Send async
            asyncio.create_task(self._send_raw(mod, message))
        
        return future
    
    def _command_timeout(self, message_id: str):
        """Handle command timeout."""
        if message_id in self._pending_commands:
            future = self._pending_commands.pop(message_id)
            if not future.done():
                future.set_result(ModResponse(
                    success=False,
                    message="Command timed out",
                    error_code="TIMEOUT",
                ))
    
    async def send_to_mod_async(
        self,
        command: str,
        params: Dict[str, Any] = None,
        **kwargs
    ) -> ModResponse:
        """Send command and wait for response."""
        future = self.send_to_mod(command, params, **kwargs)
        if future is None:
            return ModResponse(
                success=False,
                message="No mods connected",
                error_code="NO_MODS",
            )
        return await future
    
    # =========================================================================
    # Internal
    # =========================================================================
    
    async def _send_raw(self, mod: ModConnection, message: ModMessage):
        """Send raw message to mod."""
        if mod.websocket and mod.is_alive:
            try:
                await mod.websocket.send(message.to_json())
                mod.messages_sent += 1
            except Exception as e:
                logger.error(f"Failed to send to {mod.mod_name}: {e}")
                mod.is_alive = False
    
    async def _broadcast_chat(self, message: str):
        """Send message to chat (if context available)."""
        if self.context:
            try:
                await self.context.send_chat(message)
            except Exception as e:
                logger.error(f"Failed to broadcast: {e}")
    
    # =========================================================================
    # Utility Methods for Subclasses
    # =========================================================================
    
    def spawn_enemy(
        self, 
        enemy_type: str, 
        count: int = 1, 
        position: Dict[str, float] = None,
        triggered_by: str = "",
    ):
        """Convenience method to spawn enemies."""
        return self.send_to_mod("spawn_enemy", {
            "type": enemy_type,
            "count": count,
            "position": position,
        }, triggered_by=triggered_by)
    
    def give_item(
        self,
        item_id: str,
        count: int = 1,
        player: str = None,
        triggered_by: str = "",
    ):
        """Convenience method to give items."""
        return self.send_to_mod("give_item", {
            "item_id": item_id,
            "count": count,
            "player": player,
        }, triggered_by=triggered_by)
    
    def show_message(
        self,
        text: str,
        duration: float = 5.0,
        triggered_by: str = "",
    ):
        """Convenience method to show in-game message."""
        return self.send_to_mod("show_message", {
            "text": text,
            "duration": duration,
        }, triggered_by=triggered_by)
    
    def trigger_effect(
        self,
        effect_type: str,
        params: Dict[str, Any] = None,
        triggered_by: str = "",
    ):
        """Convenience method to trigger visual/audio effects."""
        return self.send_to_mod("trigger_effect", {
            "type": effect_type,
            "params": params or {},
        }, triggered_by=triggered_by)
