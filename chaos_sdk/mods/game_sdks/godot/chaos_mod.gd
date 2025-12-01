"""
Chaos Mod SDK for Godot (GDScript)
==================================

File: chaos_mod.gd
Put this in your project's autoload.

Usage:
    # In your game script:
    ChaoseMod.connect_to_server("ws://localhost:8080/mod")
    
    ChaoseMod.on_command("spawn_enemy", self, "_on_spawn_enemy")
    
    func _on_spawn_enemy(cmd):
        var enemy_type = cmd.get_string("type", "zombie")
        var count = cmd.get_int("count", 1)
        spawn_enemies(enemy_type, count)
        cmd.respond(true, "Spawned!")
    
    # When something happens:
    ChaosMod.player_died("PlayerName", "zombie")
"""

# chaos_mod.gd
extends Node

signal connected
signal disconnected
signal error(message)
signal message_received(data)

# Configuration
var game_id: String = "godot_game"
var mod_name: String = "Chaos Integration"
var mod_version: String = "1.0.0"
var capabilities: Array = ["spawn", "effects", "items"]
var auto_reconnect: bool = true
var reconnect_delay: float = 5.0
var debug: bool = false

# Internal
var _ws: WebSocketClient
var _connected: bool = false
var _server_url: String = ""
var _command_handlers: Dictionary = {}

func _ready():
    _ws = WebSocketClient.new()
    _ws.connect("connection_established", self, "_on_connected")
    _ws.connect("connection_closed", self, "_on_disconnected")
    _ws.connect("connection_error", self, "_on_error")
    _ws.connect("data_received", self, "_on_data")
    
    set_process(true)

func _process(delta):
    if _ws:
        _ws.poll()

# =============================================================================
# Public API
# =============================================================================

func connect_to_server(url: String, config: Dictionary = {}) -> void:
    """Connect to Chaos server."""
    _server_url = url
    
    if config.has("game_id"):
        game_id = config.game_id
    if config.has("mod_name"):
        mod_name = config.mod_name
    if config.has("capabilities"):
        capabilities = config.capabilities
    
    _log("Connecting to " + url)
    
    var err = _ws.connect_to_url(url)
    if err != OK:
        _log("Connection failed: " + str(err), true)
        emit_signal("error", "Connection failed")

func disconnect_from_server() -> void:
    """Disconnect from Chaos server."""
    if _ws:
        _ws.disconnect_from_host()
    _connected = false

func is_connected() -> bool:
    """Check if connected."""
    return _connected

func on_command(command_name: String, target: Object, method: String) -> void:
    """Register a command handler."""
    _command_handlers[command_name] = {
        "target": target,
        "method": method
    }
    _log("Registered handler for: " + command_name)

# =============================================================================
# Send Events
# =============================================================================

func send_event(event_type: String, data: Dictionary = {}, player: String = "", position = null) -> void:
    """Send an event to the Chaos plugin."""
    if not _connected:
        _log("Not connected, event not sent", true)
        return
    
    var pos_dict = null
    if position != null:
        if position is Vector3:
            pos_dict = {"x": position.x, "y": position.y, "z": position.z}
        elif position is Vector2:
            pos_dict = {"x": position.x, "y": position.y, "z": 0}
    
    var message = {
        "type": "event",
        "id": _generate_id(),
        "timestamp": OS.get_unix_time(),
        "game_id": game_id,
        "data": {
            "event_type": event_type,
            "event_data": data,
            "player": player,
            "position": pos_dict
        }
    }
    
    _send(message)
    _log("Sent event: " + event_type)

# Convenience methods

func player_died(player_name: String, cause: String = "", position = null) -> void:
    send_event("player_died", {"cause": cause}, player_name, position)

func player_respawned(player_name: String, position = null) -> void:
    send_event("player_respawned", {}, player_name, position)

func enemy_killed(player_name: String, enemy_type: String, position = null) -> void:
    send_event("enemy_killed", {"enemy_type": enemy_type}, player_name, position)

func boss_defeated(boss_name: String, players: Array, duration: float) -> void:
    send_event("boss_defeated", {
        "boss_name": boss_name,
        "players": players,
        "duration": duration
    })

func item_collected(player_name: String, item_id: String, count: int = 1) -> void:
    send_event("item_collected", {
        "item_id": item_id,
        "count": count
    }, player_name)

func achievement_unlocked(player_name: String, achievement_id: String, achievement_name: String) -> void:
    send_event("achievement_unlocked", {
        "achievement_id": achievement_id,
        "name": achievement_name
    }, player_name)

func custom_event(event_type: String, data: Dictionary, player: String = "") -> void:
    send_event(event_type, data, player)

# =============================================================================
# Internal
# =============================================================================

func _on_connected(protocol: String) -> void:
    _connected = true
    _send_handshake()
    emit_signal("connected")
    _log("Connected!")

func _on_disconnected(was_clean: bool) -> void:
    _connected = false
    emit_signal("disconnected")
    _log("Disconnected")
    
    if auto_reconnect:
        _log("Reconnecting in " + str(reconnect_delay) + "s...")
        yield(get_tree().create_timer(reconnect_delay), "timeout")
        connect_to_server(_server_url)

func _on_error() -> void:
    _log("WebSocket error", true)
    emit_signal("error", "WebSocket error")

func _on_data() -> void:
    var data = _ws.get_peer(1).get_packet().get_string_from_utf8()
    _handle_message(data)

func _handle_message(raw: String) -> void:
    emit_signal("message_received", raw)
    
    var parsed = JSON.parse(raw)
    if parsed.error != OK:
        _log("Failed to parse message", true)
        return
    
    var message = parsed.result
    var msg_type = message.get("type", "")
    
    match msg_type:
        "command":
            _handle_command(message)
        "ping":
            _send({
                "type": "pong",
                "game_id": game_id,
                "timestamp": OS.get_unix_time()
            })
        "handshake_ack":
            _log("Handshake acknowledged")
        _:
            _log("Received: " + msg_type)

func _handle_command(message: Dictionary) -> void:
    var data = message.get("data", {})
    var command = data.get("command", "")
    
    if _command_handlers.has(command):
        var handler = _command_handlers[command]
        
        var cmd = ModCommand.new()
        cmd._client = self
        cmd._message_id = message.get("id", "")
        cmd.command = command
        cmd.params = data.get("params", {})
        cmd.triggered_by = data.get("triggered_by", "")
        
        if handler.target and handler.target.has_method(handler.method):
            handler.target.call(handler.method, cmd)
        else:
            _send_command_result(message.id, false, "Handler not found", "NO_HANDLER")
    else:
        _log("No handler for: " + command, true)
        _send_command_result(message.id, false, "Unknown command", "UNKNOWN")

func _send_handshake() -> void:
    _send({
        "type": "handshake",
        "game_id": game_id,
        "mod_id": game_id + "_" + mod_name.to_lower().replace(" ", "_"),
        "game_name": ProjectSettings.get_setting("application/config/name"),
        "mod_name": mod_name,
        "mod_version": mod_version,
        "protocol_version": "1.0",
        "capabilities": capabilities
    })

func _send(data: Dictionary) -> void:
    if _ws and _connected:
        var json = JSON.print(data)
        _ws.get_peer(1).put_packet(json.to_utf8())

func _send_command_result(original_id: String, success: bool, message: String = "", error_code: String = "", data: Dictionary = {}) -> void:
    _send({
        "type": "command_result",
        "game_id": game_id,
        "data": {
            "original_id": original_id,
            "success": success,
            "message": message,
            "error_code": error_code,
            "response_data": data
        }
    })

func _generate_id() -> String:
    var chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    var id = ""
    for i in range(8):
        id += chars[randi() % chars.length()]
    return id

func _log(message: String, is_error: bool = false) -> void:
    if debug or is_error:
        var prefix = "[ChaosMod ERROR]" if is_error else "[ChaosMod]"
        print(prefix + " " + message)

# =============================================================================
# ModCommand Class
# =============================================================================

class ModCommand:
    var _client
    var _message_id: String
    
    var command: String
    var params: Dictionary
    var triggered_by: String
    
    func get_string(key: String, default: String = "") -> String:
        return str(params.get(key, default))
    
    func get_int(key: String, default: int = 0) -> int:
        return int(params.get(key, default))
    
    func get_float(key: String, default: float = 0.0) -> float:
        return float(params.get(key, default))
    
    func get_bool(key: String, default: bool = false) -> bool:
        return bool(params.get(key, default))
    
    func get_vector3(key: String = "position") -> Vector3:
        var pos = params.get(key, {})
        if pos is Dictionary:
            return Vector3(
                float(pos.get("x", 0)),
                float(pos.get("y", 0)),
                float(pos.get("z", 0))
            )
        return Vector3.ZERO
    
    func respond(success: bool, message: String = "", error_code: String = "", data: Dictionary = {}) -> void:
        _client._send_command_result(_message_id, success, message, error_code, data)
