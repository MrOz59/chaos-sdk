--[[
    Chaos Mod SDK for Lua (Garry's Mod, Roblox, etc.)
    ==================================================
    
    Integrate your Lua-based game with Chaos platform!
    
    Usage:
        local chaos = require("chaos_mod")
        
        chaos:Connect("ws://localhost:8080/mod", {
            game_id = "gmod",
            mod_name = "Chaos Integration",
            capabilities = {"spawn", "effects"}
        })
        
        chaos:OnCommand("spawn_enemy", function(cmd)
            SpawnNPC(cmd.params.type, cmd.params.count)
            cmd:Respond(true, "Spawned!")
        end)
        
        -- Later, when something happens:
        chaos:SendEvent("player_died", {cause = "zombie"}, "PlayerName")
]]

local ChaosMod = {}
ChaosMod.__index = ChaosMod

-- Dependencies (implement or use your game's libraries)
local json = require("json") or require("dkjson") or {
    encode = function(t) return "{}" end,
    decode = function(s) return {} end
}

-- WebSocket implementation varies by environment
-- For GMod, use GWSockets
-- For Roblox, use HttpService with WebSocket
local WebSocket = WebSocket or nil

--------------------------------------------------------------------------------
-- Configuration
--------------------------------------------------------------------------------

local DEFAULT_CONFIG = {
    game_id = "lua_game",
    mod_name = "Chaos Mod",
    mod_version = "1.0.0",
    protocol_version = "1.0",
    capabilities = {},
    auto_reconnect = true,
    reconnect_delay = 5,
    debug = false
}

--------------------------------------------------------------------------------
-- Constructor
--------------------------------------------------------------------------------

function ChaosMod.new(config)
    local self = setmetatable({}, ChaosMod)
    
    self.config = {}
    for k, v in pairs(DEFAULT_CONFIG) do
        self.config[k] = config and config[k] or v
    end
    
    self.ws = nil
    self.connected = false
    self.command_handlers = {}
    self.event_callbacks = {
        on_connect = {},
        on_disconnect = {},
        on_error = {},
        on_message = {}
    }
    
    return self
end

--------------------------------------------------------------------------------
-- Connection
--------------------------------------------------------------------------------

function ChaosMod:Connect(url, config)
    if config then
        for k, v in pairs(config) do
            self.config[k] = v
        end
    end
    
    self:Log("Connecting to " .. url)
    
    -- Create WebSocket connection
    if WebSocket then
        self.ws = WebSocket(url)
        
        self.ws.onOpen = function()
            self.connected = true
            self:SendHandshake()
            self:Emit("on_connect")
            self:Log("Connected!")
        end
        
        self.ws.onClose = function(code, reason)
            self.connected = false
            self:Emit("on_disconnect", code, reason)
            self:Log("Disconnected: " .. tostring(reason))
            
            if self.config.auto_reconnect then
                self:Log("Reconnecting in " .. self.config.reconnect_delay .. "s...")
                timer.Simple(self.config.reconnect_delay, function()
                    self:Connect(url)
                end)
            end
        end
        
        self.ws.onError = function(err)
            self:Emit("on_error", err)
            self:Log("Error: " .. tostring(err), true)
        end
        
        self.ws.onMessage = function(msg)
            self:HandleMessage(msg)
        end
        
        self.ws:open()
    else
        self:Log("WebSocket not available! Please provide a WebSocket implementation.", true)
    end
end

function ChaosMod:Disconnect()
    if self.ws then
        self.ws:close()
        self.ws = nil
    end
    self.connected = false
end

function ChaosMod:IsConnected()
    return self.connected
end

--------------------------------------------------------------------------------
-- Event Handlers
--------------------------------------------------------------------------------

function ChaosMod:On(event, callback)
    if self.event_callbacks[event] then
        table.insert(self.event_callbacks[event], callback)
    end
    return self
end

function ChaosMod:Emit(event, ...)
    if self.event_callbacks[event] then
        for _, callback in ipairs(self.event_callbacks[event]) do
            pcall(callback, ...)
        end
    end
end

--------------------------------------------------------------------------------
-- Command Registration
--------------------------------------------------------------------------------

function ChaosMod:OnCommand(command_name, handler)
    self.command_handlers[command_name] = handler
    self:Log("Registered handler for: " .. command_name)
    return self
end

--------------------------------------------------------------------------------
-- Sending Events
--------------------------------------------------------------------------------

function ChaosMod:SendEvent(event_type, data, player, position)
    if not self.connected then
        self:Log("Not connected, event not sent", true)
        return false
    end
    
    local message = {
        type = "event",
        id = self:GenerateId(),
        timestamp = os.time(),
        game_id = self.config.game_id,
        data = {
            event_type = event_type,
            event_data = data or {},
            player = player,
            position = position
        }
    }
    
    self:Send(message)
    self:Log("Sent event: " .. event_type)
    return true
end

-- Convenience methods

function ChaosMod:PlayerDied(player_name, cause, position)
    return self:SendEvent("player_died", {cause = cause}, player_name, position)
end

function ChaosMod:PlayerRespawned(player_name, position)
    return self:SendEvent("player_respawned", {}, player_name, position)
end

function ChaosMod:EnemyKilled(player_name, enemy_type, position)
    return self:SendEvent("enemy_killed", {enemy_type = enemy_type}, player_name, position)
end

function ChaosMod:BossDefeated(boss_name, players, duration)
    return self:SendEvent("boss_defeated", {
        boss_name = boss_name,
        players = players,
        duration = duration
    })
end

function ChaosMod:ItemCollected(player_name, item_id, count)
    return self:SendEvent("item_collected", {
        item_id = item_id,
        count = count or 1
    }, player_name)
end

function ChaosMod:Achievement(player_name, achievement_id, achievement_name)
    return self:SendEvent("achievement_unlocked", {
        achievement_id = achievement_id,
        name = achievement_name
    }, player_name)
end

function ChaosMod:Custom(event_type, data, player)
    return self:SendEvent(event_type, data, player)
end

--------------------------------------------------------------------------------
-- Message Handling
--------------------------------------------------------------------------------

function ChaosMod:HandleMessage(raw_message)
    self:Emit("on_message", raw_message)
    
    local success, message = pcall(json.decode, raw_message)
    if not success then
        self:Log("Failed to parse message: " .. tostring(message), true)
        return
    end
    
    local msg_type = message.type
    
    if msg_type == "command" then
        self:HandleCommand(message)
        
    elseif msg_type == "ping" then
        self:Send({
            type = "pong",
            game_id = self.config.game_id,
            timestamp = os.time()
        })
        
    elseif msg_type == "handshake_ack" then
        self:Log("Handshake acknowledged by server")
        
    else
        self:Log("Received: " .. msg_type)
    end
end

function ChaosMod:HandleCommand(message)
    local cmd_data = message.data or {}
    local command = cmd_data.command
    
    local handler = self.command_handlers[command]
    
    if handler then
        -- Create command object with response method
        local cmd = {
            id = message.id,
            command = command,
            params = cmd_data.params or {},
            triggered_by = cmd_data.triggered_by or "",
            priority = cmd_data.priority or 0,
            
            Respond = function(self_cmd, success, msg, error_code, data)
                self:SendCommandResult(message.id, success, msg, error_code, data)
            end
        }
        
        -- Make Respond work with : syntax
        setmetatable(cmd, {
            __index = function(t, k)
                if k == "Respond" then
                    return function(_, success, msg, error_code, data)
                        self:SendCommandResult(message.id, success, msg, error_code, data)
                    end
                end
            end
        })
        
        local success, err = pcall(handler, cmd)
        if not success then
            self:SendCommandResult(message.id, false, "Handler error: " .. tostring(err), "HANDLER_ERROR")
        end
    else
        self:Log("No handler for command: " .. command, true)
        self:SendCommandResult(message.id, false, "Unknown command: " .. command, "UNKNOWN_COMMAND")
    end
end

function ChaosMod:SendCommandResult(original_id, success, message, error_code, data)
    self:Send({
        type = "command_result",
        game_id = self.config.game_id,
        data = {
            original_id = original_id,
            success = success,
            message = message or "",
            error_code = error_code,
            response_data = data
        }
    })
end

--------------------------------------------------------------------------------
-- Internal
--------------------------------------------------------------------------------

function ChaosMod:SendHandshake()
    self:Send({
        type = "handshake",
        game_id = self.config.game_id,
        mod_id = self.config.game_id .. "_" .. self.config.mod_name:gsub("%s+", "_"):lower(),
        game_name = self.config.game_name or self.config.game_id,
        mod_name = self.config.mod_name,
        mod_version = self.config.mod_version,
        protocol_version = self.config.protocol_version,
        capabilities = self.config.capabilities
    })
end

function ChaosMod:Send(data)
    if self.ws and self.connected then
        local json_str = json.encode(data)
        self.ws:send(json_str)
    end
end

function ChaosMod:GenerateId()
    local chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    local id = ""
    for i = 1, 8 do
        local idx = math.random(1, #chars)
        id = id .. chars:sub(idx, idx)
    end
    return id
end

function ChaosMod:Log(message, is_error)
    if self.config.debug or is_error then
        local prefix = is_error and "[ChaosMod ERROR]" or "[ChaosMod]"
        print(prefix .. " " .. message)
    end
end

--------------------------------------------------------------------------------
-- Singleton / Global Instance
--------------------------------------------------------------------------------

local instance = nil

function ChaosMod.GetInstance(config)
    if not instance then
        instance = ChaosMod.new(config)
    end
    return instance
end

--------------------------------------------------------------------------------
-- Garry's Mod Specific Hooks
--------------------------------------------------------------------------------

if SERVER and hook then
    -- Auto-hook common GMod events
    local function SetupGModHooks(chaos)
        hook.Add("PlayerDeath", "ChaosMod_PlayerDeath", function(victim, inflictor, attacker)
            if chaos:IsConnected() then
                local cause = IsValid(attacker) and attacker:GetClass() or "unknown"
                chaos:PlayerDied(victim:Nick(), cause, victim:GetPos())
            end
        end)
        
        hook.Add("PlayerSpawn", "ChaosMod_PlayerSpawn", function(ply)
            if chaos:IsConnected() then
                chaos:PlayerRespawned(ply:Nick(), ply:GetPos())
            end
        end)
        
        hook.Add("OnNPCKilled", "ChaosMod_NPCKilled", function(npc, attacker, inflictor)
            if chaos:IsConnected() and IsValid(attacker) and attacker:IsPlayer() then
                chaos:EnemyKilled(attacker:Nick(), npc:GetClass(), npc:GetPos())
            end
        end)
    end
    
    ChaosMod.SetupGModHooks = SetupGModHooks
end

--------------------------------------------------------------------------------
-- Export
--------------------------------------------------------------------------------

return ChaosMod
