# 🎮 Chaos Mod SDK - Game Integration

Este diretório contém SDKs para integrar mods de jogos com a plataforma Chaos.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                         CHAOS PLATFORM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐        WebSocket         ┌─────────────┐     │
│   │   Plugin    │◄────────────────────────►│   Mod SDK   │     │
│   │  (Python)   │     JSON Messages        │  (C#/Lua)   │     │
│   └──────┬──────┘                          └──────┬──────┘     │
│          │                                        │             │
│          │                                        │             │
│   ┌──────▼──────┐                          ┌──────▼──────┐     │
│   │  Bot/Chat   │                          │   In-Game   │     │
│   │  Commands   │                          │   Events    │     │
│   └─────────────┘                          └─────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## SDKs Disponíveis

| Engine/Jogo | Linguagem | Status |
|-------------|-----------|--------|
| Unity | C# | ✅ Pronto |
| Unreal Engine | C++ | 🚧 Em desenvolvimento |
| Godot | GDScript/C# | ✅ Pronto |
| Minecraft | Java (Fabric/Forge) | 🚧 Em desenvolvimento |
| Garry's Mod | Lua | ✅ Pronto |
| Genérico | WebSocket | ✅ Pronto |

## Quick Start

### 1. No Seu Plugin (Python)

```python
from chaos_sdk.mods import ModBridgePlugin, mod_event

class MeuJogoPlugin(ModBridgePlugin):
    name = "Meu Jogo Chaos"
    game_id = "meu_jogo"
    
    @mod_event("player_died")
    def on_player_died(self, mod, event):
        return f"💀 {event.player} morreu no jogo!"
    
    def cmd_spawn(self, username, args, **kwargs):
        enemy_type = args[0] if args else "zombie"
        count = int(args[1]) if len(args) > 1 else 1
        
        self.send_to_mod("spawn_enemy", {
            "type": enemy_type,
            "count": count,
        }, triggered_by=username)
        
        return f"{username} spawnou {count} {enemy_type}!"
```

### 2. No Seu Mod (C# Unity)

```csharp
using ChaosMod;

public class ChaosIntegration : MonoBehaviour
{
    private ChaosModClient client;
    
    void Start()
    {
        client = new ChaosModClient("meu_jogo", "ws://localhost:8080/mod");
        
        // Registrar handlers de comandos
        client.OnCommand("spawn_enemy", SpawnEnemy);
        
        client.Connect();
    }
    
    void SpawnEnemy(ModCommand cmd)
    {
        string type = cmd.GetString("type");
        int count = cmd.GetInt("count");
        
        // Spawnar inimigos no jogo
        EnemySpawner.Spawn(type, count);
        
        // Responder sucesso
        cmd.Respond(success: true, message: $"Spawned {count} {type}");
    }
    
    public void OnPlayerDied(string playerName)
    {
        // Enviar evento para o plugin
        client.SendEvent("player_died", new {
            player = playerName,
            position = player.position
        });
    }
}
```

## Protocolo de Comunicação

### Mensagens (JSON via WebSocket)

```json
// Handshake (Mod → Plugin)
{
    "type": "handshake",
    "game_id": "meu_jogo",
    "mod_name": "Chaos Integration",
    "mod_version": "1.0.0",
    "protocol_version": "1.0",
    "capabilities": ["spawn", "items", "effects"]
}

// Evento (Mod → Plugin)
{
    "type": "event",
    "event_type": "player_died",
    "data": {
        "player": "Jogador123",
        "cause": "zombie"
    }
}

// Comando (Plugin → Mod)
{
    "type": "command",
    "command": "spawn_enemy",
    "params": {
        "type": "zombie",
        "count": 5
    },
    "triggered_by": "viewer123"
}

// Resultado (Mod → Plugin)
{
    "type": "command_result",
    "original_id": "abc123",
    "success": true,
    "message": "Spawned 5 zombies"
}
```

## Eventos Padrão

| Evento | Descrição | Data |
|--------|-----------|------|
| `player_died` | Jogador morreu | `player`, `cause`, `position` |
| `player_respawned` | Jogador renasceu | `player`, `position` |
| `item_collected` | Item coletado | `player`, `item_id`, `count` |
| `enemy_killed` | Inimigo morto | `player`, `enemy_type`, `position` |
| `boss_defeated` | Boss derrotado | `boss_name`, `players`, `time` |
| `achievement_unlocked` | Conquista | `player`, `achievement_id`, `name` |

## Comandos Padrão

| Comando | Descrição | Params |
|---------|-----------|--------|
| `spawn_enemy` | Spawnar inimigo | `type`, `count`, `position?` |
| `give_item` | Dar item | `item_id`, `count`, `player?` |
| `heal_player` | Curar | `amount`, `player?` |
| `damage_player` | Causar dano | `amount`, `player?` |
| `show_message` | Mostrar mensagem | `text`, `duration` |
| `play_sound` | Tocar som | `sound_id`, `volume?` |
| `change_weather` | Mudar clima | `weather_type` |
| `spawn_effect` | Efeito visual | `effect_type`, `position`, `params?` |

## Links

- [Unity SDK](./unity/)
- [Godot SDK](./godot/)
- [Garry's Mod SDK](./gmod/)
- [Documentação Completa](../docs/mod-integration.md)

---

*Chaos Mod SDK v1.0.0*
