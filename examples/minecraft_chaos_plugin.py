"""
Example: Minecraft Chaos Plugin
===============================

This example shows how to create a plugin that integrates
with a Minecraft mod for viewer-controlled chaos.

The mod (Java/Fabric) connects via WebSocket and can:
- Receive commands: spawn mobs, give items, change weather
- Send events: player deaths, boss kills, achievements

Usage:
    1. Install this plugin on the Chaos server
    2. Install the companion Minecraft mod
    3. Connect to Minecraft and join a world
    4. Viewers can use commands to affect the game!
"""

from chaos_sdk.mods import (
    ModBridgePlugin,
    ModConnection,
    ModEvent,
    mod_event,
    mod_command,
    broadcast_result,
)


class MinecraftChaosPlugin(ModBridgePlugin):
    """
    Chaos integration plugin for Minecraft.
    """
    
    name = "Minecraft Chaos"
    version = "1.0.0"
    author = "Chaos Community"
    description = "Controle o Minecraft com comandos do chat!"
    
    game_id = "minecraft"
    
    required_permissions = [
        "mod:bridge",
        "chat:send",
        "points:read",
        "points:write",
    ]
    
    # =========================================================================
    # Mod Event Handlers
    # =========================================================================
    
    @mod_event("player_died")
    @broadcast_result(template="💀 {result}")
    def on_player_died(self, mod: ModConnection, event: ModEvent):
        """Handle player death in Minecraft."""
        player = event.player or "Alguém"
        cause = event.data.get("cause", "motivo desconhecido")
        
        # Give chat consolation points
        if self.context:
            self.context.add_points("chat", 10, "Player morreu")
        
        return f"{player} morreu! Causa: {cause}"
    
    @mod_event("player_respawned")
    def on_player_respawned(self, mod: ModConnection, event: ModEvent):
        """Handle player respawn."""
        player = event.player or "Jogador"
        return f"🔄 {player} renasceu!"
    
    @mod_event("boss_defeated")
    @broadcast_result(template="🏆 {result}", to_chat=True, to_mod=True)
    def on_boss_defeated(self, mod: ModConnection, event: ModEvent):
        """Handle boss defeat - big celebration!"""
        boss_name = event.data.get("boss_name", "Boss")
        duration = event.data.get("duration", 0)
        
        # Give bonus points to chat
        if self.context:
            self.context.add_points("chat", 100, f"Boss {boss_name} derrotado!")
        
        return f"O boss {boss_name} foi derrotado em {duration:.1f}s! 🎉"
    
    @mod_event("advancement_unlocked")
    def on_advancement(self, mod: ModConnection, event: ModEvent):
        """Handle Minecraft advancement."""
        player = event.player or "Jogador"
        advancement = event.data.get("name", "Conquista")
        
        return f"⭐ {player} desbloqueou: {advancement}"
    
    @mod_event("item_collected")
    def on_item_collected(self, mod: ModConnection, event: ModEvent):
        """Handle item collection."""
        player = event.player or "Jogador"
        item = event.data.get("item_id", "item")
        count = event.data.get("count", 1)
        
        # Only announce rare items
        rare_items = ["diamond", "netherite", "elytra", "totem"]
        if any(rare in item.lower() for rare in rare_items):
            return f"💎 {player} encontrou {count}x {item}!"
        
        return None  # Don't announce common items
    
    # =========================================================================
    # Chat Commands -> Mod Actions
    # =========================================================================
    
    @mod_command()
    def cmd_spawn(self, username: str, args: list, **kwargs) -> str:
        """
        Spawn mobs in Minecraft.
        Usage: !spawn <mob_type> [count]
        Cost: 50 points
        """
        if not args:
            return "❌ Use: !spawn <mob> [quantidade]. Ex: !spawn zombie 5"
        
        mob_type = args[0].lower()
        count = min(int(args[1]) if len(args) > 1 else 1, 10)  # Max 10
        
        # Check points
        cost = count * 50
        if self.context:
            points = self.context.get_points(username)
            if points < cost:
                return f"❌ Você precisa de {cost} pontos (tem {points})"
            
            self.context.remove_points(username, cost, f"Spawn {count} {mob_type}")
        
        # Send to mod
        self.send_to_mod("spawn_enemy", {
            "type": mob_type,
            "count": count,
            "near_player": True,
        }, triggered_by=username)
        
        return f"🧟 {username} spawnou {count} {mob_type}! (-{cost} pontos)"
    
    @mod_command()
    def cmd_creeper(self, username: str, args: list, **kwargs) -> str:
        """Spawn a creeper near the player! Cost: 100 points"""
        if self.context:
            points = self.context.get_points(username)
            if points < 100:
                return f"❌ Precisa de 100 pontos (tem {points})"
            self.context.remove_points(username, 100, "Creeper spawn")
        
        self.send_to_mod("spawn_enemy", {
            "type": "creeper",
            "count": 1,
            "near_player": True,
            "charged": False,
        }, triggered_by=username)
        
        return f"💥 {username} spawnou um Creeper!"
    
    @mod_command()
    def cmd_charged(self, username: str, args: list, **kwargs) -> str:
        """Spawn a CHARGED creeper! Cost: 500 points"""
        if self.context:
            points = self.context.get_points(username)
            if points < 500:
                return f"❌ Precisa de 500 pontos (tem {points})"
            self.context.remove_points(username, 500, "Charged creeper")
        
        self.send_to_mod("spawn_enemy", {
            "type": "creeper",
            "count": 1,
            "near_player": True,
            "charged": True,
        }, triggered_by=username)
        
        return f"⚡💥 {username} spawnou um CHARGED CREEPER!"
    
    @mod_command()
    def cmd_item(self, username: str, args: list, **kwargs) -> str:
        """
        Give item to streamer.
        Usage: !item <item_id> [count]
        Cost: 30 points
        """
        if not args:
            return "❌ Use: !item <item> [quantidade]. Ex: !item diamond_sword"
        
        item_id = args[0].lower()
        count = min(int(args[1]) if len(args) > 1 else 1, 64)
        
        # Cost based on item
        expensive_items = ["netherite", "elytra", "enchanted"]
        cost = 200 if any(e in item_id for e in expensive_items) else 30
        
        if self.context:
            points = self.context.get_points(username)
            if points < cost:
                return f"❌ Precisa de {cost} pontos (tem {points})"
            self.context.remove_points(username, cost, f"Item: {item_id}")
        
        self.send_to_mod("give_item", {
            "item_id": f"minecraft:{item_id}",
            "count": count,
        }, triggered_by=username)
        
        return f"🎁 {username} deu {count}x {item_id}!"
    
    @mod_command()
    def cmd_weather(self, username: str, args: list, **kwargs) -> str:
        """
        Change weather.
        Usage: !weather <clear|rain|thunder>
        Cost: 20 points
        """
        valid = ["clear", "rain", "thunder"]
        weather = args[0].lower() if args else "rain"
        
        if weather not in valid:
            return f"❌ Use: !weather {{{'/'.join(valid)}}}"
        
        if self.context:
            points = self.context.get_points(username)
            if points < 20:
                return f"❌ Precisa de 20 pontos"
            self.context.remove_points(username, 20, f"Weather: {weather}")
        
        self.send_to_mod("change_weather", {
            "weather_type": weather,
        }, triggered_by=username)
        
        icons = {"clear": "☀️", "rain": "🌧️", "thunder": "⛈️"}
        return f"{icons[weather]} {username} mudou o clima para {weather}!"
    
    @mod_command()
    def cmd_time(self, username: str, args: list, **kwargs) -> str:
        """
        Change time.
        Usage: !time <day|night|noon|midnight>
        Cost: 15 points
        """
        valid = {"day": 1000, "noon": 6000, "night": 13000, "midnight": 18000}
        time_name = args[0].lower() if args else "day"
        
        if time_name not in valid:
            return f"❌ Use: !time {{{'/'.join(valid.keys())}}}"
        
        if self.context:
            points = self.context.get_points(username)
            if points < 15:
                return f"❌ Precisa de 15 pontos"
            self.context.remove_points(username, 15, f"Time: {time_name}")
        
        self.send_to_mod("change_time", {
            "time": valid[time_name],
        }, triggered_by=username)
        
        icons = {"day": "🌅", "noon": "☀️", "night": "🌙", "midnight": "🌑"}
        return f"{icons[time_name]} {username} mudou para {time_name}!"
    
    @mod_command()
    def cmd_explode(self, username: str, args: list, **kwargs) -> str:
        """Create an explosion near the player! Cost: 150 points"""
        power = min(float(args[0]) if args else 2.0, 4.0)  # Max power 4
        
        cost = int(power * 75)
        if self.context:
            points = self.context.get_points(username)
            if points < cost:
                return f"❌ Precisa de {cost} pontos"
            self.context.remove_points(username, cost, "Explosion")
        
        self.send_to_mod("spawn_effect", {
            "type": "explosion",
            "power": power,
            "fire": False,
        }, triggered_by=username)
        
        return f"💥 {username} causou uma explosão!"
    
    @mod_command()
    def cmd_msg(self, username: str, args: list, **kwargs) -> str:
        """
        Show message on streamer's screen.
        Usage: !msg <text>
        Cost: 10 points
        """
        if not args:
            return "❌ Use: !msg <sua mensagem>"
        
        text = " ".join(args)[:50]  # Max 50 chars
        
        if self.context:
            points = self.context.get_points(username)
            if points < 10:
                return f"❌ Precisa de 10 pontos"
            self.context.remove_points(username, 10, "In-game message")
        
        self.send_to_mod("show_message", {
            "text": f"[{username}]: {text}",
            "duration": 5.0,
            "color": "yellow",
        }, triggered_by=username)
        
        return f"📢 Mensagem enviada!"
    
    # =========================================================================
    # Connection Events
    # =========================================================================
    
    async def on_mod_connected(self, mod: ModConnection):
        """Called when Minecraft mod connects."""
        if self.context:
            await self.context.send_chat(
                f"🎮 Minecraft conectado! Mod: {mod.mod_name} v{mod.mod_version}"
            )
        
        # Send welcome message to game
        self.send_to_mod("show_message", {
            "text": "Chaos Mode ATIVADO! Chat pode controlar o jogo!",
            "duration": 10.0,
            "color": "green",
        })
    
    async def on_mod_disconnected(self, mod: ModConnection):
        """Called when Minecraft mod disconnects."""
        if self.context:
            await self.context.send_chat(
                "⚠️ Minecraft desconectou. Comandos de jogo indisponíveis."
            )


# Export for plugin loading
Plugin = MinecraftChaosPlugin
