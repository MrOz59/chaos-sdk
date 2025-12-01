"""
Mod Communication Protocol
==========================

Defines the message format for communication between
Chaos plugins and game mods.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional, List


class MessageType(Enum):
    """Types of messages in the protocol."""
    
    # Connection
    HANDSHAKE = "handshake"
    HANDSHAKE_ACK = "handshake_ack"
    PING = "ping"
    PONG = "pong"
    DISCONNECT = "disconnect"
    
    # Events (Mod → Plugin)
    EVENT = "event"
    EVENT_ACK = "event_ack"
    
    # Commands (Plugin → Mod)  
    COMMAND = "command"
    COMMAND_RESULT = "command_result"
    
    # State sync
    STATE_UPDATE = "state_update"
    STATE_REQUEST = "state_request"
    
    # Errors
    ERROR = "error"


@dataclass
class ModMessage:
    """Base message for mod communication."""
    
    type: MessageType
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    game_id: str = ""
    mod_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        d = asdict(self)
        d['type'] = self.type.value
        return json.dumps(d)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ModMessage':
        """Deserialize from JSON string."""
        d = json.loads(json_str)
        d['type'] = MessageType(d['type'])
        return cls(**d)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['type'] = self.type.value
        return d


@dataclass
class HandshakeMessage(ModMessage):
    """Initial handshake from mod to plugin."""
    
    type: MessageType = MessageType.HANDSHAKE
    game_name: str = ""
    mod_name: str = ""
    mod_version: str = ""
    protocol_version: str = "1.0"
    capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            'game_name': self.game_name,
            'mod_name': self.mod_name,
            'mod_version': self.mod_version,
            'protocol_version': self.protocol_version,
            'capabilities': self.capabilities,
        })
        return d


@dataclass 
class ModEvent:
    """Event sent from mod to plugin."""
    
    event_type: str  # e.g., "player_died", "item_collected"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    # Optional metadata
    player: Optional[str] = None
    position: Optional[Dict[str, float]] = None  # x, y, z
    
    def to_message(self, game_id: str, mod_id: str) -> ModMessage:
        """Convert to ModMessage."""
        return ModMessage(
            type=MessageType.EVENT,
            game_id=game_id,
            mod_id=mod_id,
            data={
                'event_type': self.event_type,
                'event_data': self.data,
                'player': self.player,
                'position': self.position,
            }
        )


@dataclass
class ModCommand:
    """Command sent from plugin to mod."""
    
    command: str  # e.g., "spawn_enemy", "give_item"
    params: Dict[str, Any] = field(default_factory=dict)
    
    # Execution options
    priority: int = 0  # Higher = more urgent
    timeout: float = 30.0  # Seconds to wait for result
    require_ack: bool = True
    
    # Metadata
    triggered_by: str = ""  # Username who triggered
    reason: str = ""  # Why this command was sent
    
    def to_message(self, game_id: str, mod_id: str) -> ModMessage:
        """Convert to ModMessage."""
        return ModMessage(
            type=MessageType.COMMAND,
            game_id=game_id,
            mod_id=mod_id,
            data={
                'command': self.command,
                'params': self.params,
                'priority': self.priority,
                'timeout': self.timeout,
                'require_ack': self.require_ack,
                'triggered_by': self.triggered_by,
                'reason': self.reason,
            }
        )


@dataclass
class ModResponse:
    """Response from mod after executing a command."""
    
    success: bool
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    execution_time: float = 0.0
    
    def to_message(self, original_msg_id: str, game_id: str, mod_id: str) -> ModMessage:
        """Convert to ModMessage."""
        return ModMessage(
            type=MessageType.COMMAND_RESULT,
            game_id=game_id,
            mod_id=mod_id,
            data={
                'original_id': original_msg_id,
                'success': self.success,
                'message': self.message,
                'response_data': self.data,
                'error_code': self.error_code,
                'execution_time': self.execution_time,
            }
        )


# Common event types
class CommonEvents:
    """Standard event types that mods can emit."""
    
    # Player events
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    PLAYER_DIED = "player_died"
    PLAYER_RESPAWNED = "player_respawned"
    PLAYER_LEVEL_UP = "player_level_up"
    PLAYER_DAMAGED = "player_damaged"
    PLAYER_HEALED = "player_healed"
    
    # Game events
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    GAME_PAUSED = "game_paused"
    GAME_RESUMED = "game_resumed"
    ROUND_STARTED = "round_started"
    ROUND_ENDED = "round_ended"
    
    # Item events
    ITEM_COLLECTED = "item_collected"
    ITEM_USED = "item_used"
    ITEM_DROPPED = "item_dropped"
    
    # Combat events
    ENEMY_KILLED = "enemy_killed"
    BOSS_SPAWNED = "boss_spawned"
    BOSS_DEFEATED = "boss_defeated"
    
    # Achievement events
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    MILESTONE_REACHED = "milestone_reached"
    
    # Custom
    CUSTOM = "custom"


# Common command types
class CommonCommands:
    """Standard commands that mods can receive."""
    
    # Spawning
    SPAWN_ENEMY = "spawn_enemy"
    SPAWN_ITEM = "spawn_item"
    SPAWN_EFFECT = "spawn_effect"
    
    # Player manipulation
    HEAL_PLAYER = "heal_player"
    DAMAGE_PLAYER = "damage_player"
    TELEPORT_PLAYER = "teleport_player"
    GIVE_ITEM = "give_item"
    TAKE_ITEM = "take_item"
    SET_PLAYER_STAT = "set_player_stat"
    
    # World manipulation
    CHANGE_WEATHER = "change_weather"
    CHANGE_TIME = "change_time"
    TRIGGER_EVENT = "trigger_event"
    
    # Game state
    START_MINIGAME = "start_minigame"
    END_MINIGAME = "end_minigame"
    SET_DIFFICULTY = "set_difficulty"
    
    # Visual/Audio
    PLAY_SOUND = "play_sound"
    SHOW_MESSAGE = "show_message"
    SHAKE_SCREEN = "shake_screen"
    
    # Custom
    CUSTOM = "custom"
