# 🎮 Chaos Mod Integration Guide

Guia completo para integrar mods de jogos com a plataforma Chaos.

## Visão Geral

O sistema de mods permite comunicação **bidirecional** entre:
- **Plugins Chaos** (Python no servidor)
- **Mods de Jogos** (C#, Lua, Java, etc. dentro do jogo)

```
┌─────────────────────────────────────────────────────────────────┐
│                      FLUXO DE COMUNICAÇÃO                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   CHAT DO TWITCH              SERVIDOR CHAOS                    │
│   ┌────────────┐             ┌────────────────┐                │
│   │ !spawn 5   │────────────►│   Plugin       │                │
│   │ zombies    │             │   (Python)     │                │
│   └────────────┘             └───────┬────────┘                │
│                                      │                          │
│                              WebSocket JSON                     │
│                                      │                          │
│                              ┌───────▼────────┐                │
│                              │   Game Mod     │                │
│                              │   (C#/Lua)     │                │
│                              └───────┬────────┘                │
│                                      │                          │
│                              ┌───────▼────────┐                │
│                              │   5 zombies    │                │
│                              │   spawned! 🧟  │                │
│                              └────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Componentes

### 1. Plugin Chaos (Python)

O plugin roda no servidor Chaos e:
- Recebe comandos do chat
- Envia comandos para o mod
- Recebe eventos do mod
- Responde no chat

```python
from chaos_sdk.mods import ModBridgePlugin, mod_event

class MeuJogoPlugin(ModBridgePlugin):
    name = "Meu Jogo Chaos"
    game_id = "meu_jogo"
    
    @mod_event("player_died")
    def on_player_died(self, mod, event):
        return f"💀 {event.player} morreu!"
    
    def cmd_spawn(self, username, args, **kwargs):
        self.send_to_mod("spawn_enemy", {
            "type": args[0] if args else "zombie",
            "count": 5
        }, triggered_by=username)
        return f"{username} spawnou inimigos!"
```

### 2. Mod do Jogo (C#/Lua/etc.)

O mod roda dentro do jogo e:
- Conecta via WebSocket ao servidor
- Recebe comandos e executa ações no jogo
- Envia eventos quando coisas acontecem

```csharp
// Unity C#
var client = new ChaosModClient("meu_jogo");

client.OnCommand("spawn_enemy", cmd => {
    var type = cmd.GetString("type");
    var count = cmd.GetInt("count");
    SpawnEnemies(type, count);
    cmd.Respond(true, "Spawned!");
});

client.Connect("ws://servidor:8080/mod/ws");

// Quando o jogador morre:
client.PlayerDied("NomeJogador", "zombie");
```

## Protocolo de Comunicação

### Formato das Mensagens

Todas as mensagens são JSON via WebSocket:

```json
{
    "type": "message_type",
    "id": "unique_id",
    "timestamp": 1234567890,
    "game_id": "minecraft",
    "data": { ... }
}
```

### Tipos de Mensagem

| Tipo | Direção | Descrição |
|------|---------|-----------|
| `handshake` | Mod → Server | Identificação inicial |
| `handshake_ack` | Server → Mod | Confirmação |
| `ping` | Mod → Server | Heartbeat |
| `pong` | Server → Mod | Resposta heartbeat |
| `event` | Mod → Server | Evento do jogo |
| `event_ack` | Server → Mod | Confirmação do evento |
| `command` | Server → Mod | Comando para executar |
| `command_result` | Mod → Server | Resultado do comando |

### Exemplo: Handshake

```json
// Mod → Server
{
    "type": "handshake",
    "game_id": "minecraft",
    "mod_id": "minecraft_chaos_1",
    "game_name": "Minecraft",
    "mod_name": "Chaos Integration",
    "mod_version": "1.0.0",
    "protocol_version": "1.0",
    "capabilities": ["spawn", "items", "effects"]
}

// Server → Mod
{
    "type": "handshake_ack",
    "status": "connected",
    "server_time": 1234567890,
    "mod_id": "minecraft_chaos_1"
}
```

### Exemplo: Evento

```json
// Mod → Server
{
    "type": "event",
    "id": "evt_abc123",
    "game_id": "minecraft",
    "data": {
        "event_type": "player_died",
        "event_data": {
            "cause": "zombie"
        },
        "player": "Steve",
        "position": {"x": 100, "y": 64, "z": -50}
    }
}
```

### Exemplo: Comando

```json
// Server → Mod
{
    "type": "command",
    "id": "cmd_xyz789",
    "game_id": "minecraft",
    "data": {
        "command": "spawn_enemy",
        "params": {
            "type": "zombie",
            "count": 5,
            "near_player": true
        },
        "triggered_by": "viewer123",
        "priority": 0,
        "timeout": 30
    }
}

// Mod → Server
{
    "type": "command_result",
    "game_id": "minecraft",
    "data": {
        "original_id": "cmd_xyz789",
        "success": true,
        "message": "Spawned 5 zombies",
        "execution_time": 0.05
    }
}
```

## SDKs Disponíveis

### Unity (C#)

```csharp
using ChaosMod;

public class GameChaos : MonoBehaviour
{
    private ChaosModClient client;
    
    void Start()
    {
        client = new ChaosModClient("unity_game");
        
        // Registrar handlers
        client.OnCommand("spawn_enemy", SpawnEnemy);
        client.OnCommand("give_item", GiveItem);
        client.OnCommand("show_message", ShowMessage);
        
        // Callbacks
        client.OnConnected += () => Debug.Log("Chaos conectado!");
        client.OnDisconnected += () => Debug.Log("Chaos desconectado!");
        
        // Conectar
        client.Connect("ws://localhost:8080/mod/ws");
    }
    
    void SpawnEnemy(ModCommand cmd)
    {
        string type = cmd.GetString("type", "zombie");
        int count = cmd.GetInt("count", 1);
        Vector3 pos = cmd.GetPosition();
        
        for (int i = 0; i < count; i++)
        {
            Instantiate(enemyPrefab, pos + Random.insideUnitSphere * 5, Quaternion.identity);
        }
        
        cmd.Respond(true, $"Spawned {count} {type}");
    }
    
    // Enviar eventos
    public void OnPlayerDeath(string playerName, string cause)
    {
        client.PlayerDied(playerName, cause, transform.position);
    }
    
    public void OnBossKilled(string bossName, float fightTime)
    {
        client.BossDefeated(bossName, new List<string>{"Player1"}, fightTime);
    }
}
```

### Godot (GDScript)

```gdscript
extends Node

var chaos = preload("res://addons/chaos_mod/chaos_mod.gd").new()

func _ready():
    add_child(chaos)
    
    # Registrar handlers
    chaos.on_command("spawn_enemy", self, "_on_spawn_enemy")
    chaos.on_command("give_item", self, "_on_give_item")
    
    # Conectar
    chaos.connect_to_server("ws://localhost:8080/mod/ws", {
        "game_id": "my_godot_game",
        "mod_name": "Chaos Integration"
    })

func _on_spawn_enemy(cmd):
    var enemy_type = cmd.get_string("type", "zombie")
    var count = cmd.get_int("count", 1)
    
    for i in range(count):
        spawn_enemy(enemy_type)
    
    cmd.respond(true, "Spawned %d %s" % [count, enemy_type])

# Enviar eventos
func player_died():
    chaos.player_died(player_name, "enemy", player.position)

func boss_defeated():
    chaos.boss_defeated("Dragon", ["Player1"], fight_time)
```

### Lua (Garry's Mod)

```lua
local ChaosMod = require("chaos_mod")

local chaos = ChaosMod.new({
    game_id = "gmod",
    mod_name = "Chaos TTT",
    debug = true
})

-- Registrar handlers
chaos:OnCommand("spawn_npc", function(cmd)
    local npc_type = cmd.params.type or "npc_zombie"
    local count = cmd.params.count or 1
    
    for i = 1, count do
        local npc = ents.Create(npc_type)
        npc:SetPos(player.GetAll()[1]:GetPos() + Vector(0, 0, 100))
        npc:Spawn()
    end
    
    cmd:Respond(true, "Spawned " .. count .. " " .. npc_type)
end)

-- Conectar
chaos:Connect("ws://localhost:8080/mod/ws")

-- Hooks do GMod
hook.Add("PlayerDeath", "ChaosMod", function(victim, inflictor, attacker)
    chaos:PlayerDied(victim:Nick(), attacker:GetClass())
end)
```

## Eventos Padrão

| Evento | Descrição | Dados |
|--------|-----------|-------|
| `player_died` | Jogador morreu | `player`, `cause`, `position` |
| `player_respawned` | Jogador renasceu | `player`, `position` |
| `enemy_killed` | Inimigo morto | `player`, `enemy_type` |
| `boss_defeated` | Boss derrotado | `boss_name`, `players`, `duration` |
| `item_collected` | Item coletado | `player`, `item_id`, `count` |
| `achievement_unlocked` | Conquista | `player`, `achievement_id`, `name` |
| `custom` | Evento customizado | Qualquer dado |

## Comandos Padrão

| Comando | Descrição | Parâmetros |
|---------|-----------|------------|
| `spawn_enemy` | Spawnar inimigo | `type`, `count`, `position?` |
| `give_item` | Dar item | `item_id`, `count`, `player?` |
| `heal_player` | Curar jogador | `amount`, `player?` |
| `damage_player` | Causar dano | `amount`, `player?` |
| `show_message` | Mostrar texto | `text`, `duration`, `color?` |
| `play_sound` | Tocar som | `sound_id`, `volume?` |
| `change_weather` | Mudar clima | `weather_type` |
| `spawn_effect` | Efeito visual | `type`, `position`, `params?` |
| `custom` | Comando custom | Qualquer parâmetro |

## Criando Seu Mod

### Passo 1: Plugin Python

```python
# meu_jogo_plugin.py
from chaos_sdk.mods import ModBridgePlugin, mod_event

class MeuJogoPlugin(ModBridgePlugin):
    name = "Meu Jogo"
    game_id = "meu_jogo"  # Identificador único
    
    def on_load(self):
        # Registrar comandos do chat
        self.register_command("spawn", self.cmd_spawn)
        self.register_command("item", self.cmd_item)
    
    @mod_event("player_died")
    def on_death(self, mod, event):
        return f"💀 {event.player} morreu!"
    
    def cmd_spawn(self, username, args, **kwargs):
        if not self.has_connected_mod:
            return "❌ Jogo não conectado!"
        
        self.send_to_mod("spawn_enemy", {"type": "zombie", "count": 3})
        return f"🧟 {username} spawnou zombies!"

Plugin = MeuJogoPlugin
```

### Passo 2: Mod do Jogo

Use o SDK da sua engine e:

1. Conectar ao servidor via WebSocket
2. Enviar handshake com `game_id` igual ao plugin
3. Registrar handlers para comandos
4. Enviar eventos quando coisas acontecem

### Passo 3: Testar

1. Iniciar o servidor Chaos
2. Carregar o plugin
3. Iniciar o jogo com o mod
4. Usar comandos no chat!

## Boas Práticas

### Segurança

- Validar todos os parâmetros recebidos
- Limitar quantidade de spawns para evitar lag
- Implementar cooldowns em comandos custosos
- Não expor comandos sensíveis (admin, debug)

### Performance

- Usar timeouts em comandos longos
- Não bloquear o jogo esperando respostas
- Processar eventos em batches se muitos

### UX

- Responder comandos com feedback visual
- Anunciar conexão/desconexão no chat
- Mostrar erros de forma amigável

## Troubleshooting

### Mod não conecta

- Verificar URL do WebSocket
- Verificar se porta está aberta
- Checar logs do servidor

### Comandos não funcionam

- Verificar `game_id` igual no plugin e mod
- Checar se handler está registrado
- Ver logs para erros

### Eventos não chegam

- Verificar se mod está conectado
- Checar se plugin tem handler para o evento
- Ver logs do servidor

---

*Chaos Mod Integration v1.0.0*
