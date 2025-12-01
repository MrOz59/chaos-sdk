"""
Plugin de Casino Completo - Exemplo do Chaos SDK
=================================================

Este plugin demonstra todas as funcionalidades do SDK:
- Comandos com cooldown
- Sistema de pontos
- Decoradores avançados
- Configuração persistente
- Eventos
- Utilitários

Comandos:
    !coinflip <aposta> <cara/coroa>  - Joga cara ou coroa
    !slots [aposta]                   - Caça-níquel
    !roulette <aposta> <cor/numero>   - Roleta
    !blackjack <aposta>               - 21/Blackjack
    !jackpot                          - Ver jackpot acumulado
    !casino                           - Estatísticas do casino

Autor: Chaos Factory Team
"""
from chaos_sdk import (
    Plugin, 
    command, 
    cooldown, 
    cost_points,
    require_points,
    on_event,
    Emoji,
    RandomUtils,
    TextUtils,
    PluginConfig,
    int_field,
    bool_field,
    float_field,
)


class CasinoPlugin(Plugin):
    """
    Plugin completo de casino com vários jogos.
    """
    
    name = "Casino Royale"
    version = "2.0.0"
    author = "Chaos Factory"
    description = "Jogos de casino: coinflip, slots, roleta e blackjack"
    
    # Configurações do plugin (persistentes)
    config = PluginConfig(
        min_bet=int_field(default=10, min_value=1, max_value=100, 
                          description="Aposta mínima"),
        max_bet=int_field(default=5000, min_value=100, max_value=50000, 
                          description="Aposta máxima"),
        house_edge=float_field(default=0.02, min_value=0, max_value=0.1,
                               description="Vantagem da casa (0-10%)"),
        jackpot_enabled=bool_field(default=True, 
                                   description="Jackpot progressivo ativo"),
        announce_big_wins=bool_field(default=True,
                                     description="Anunciar grandes vitórias"),
    )
    
    # Permissões necessárias
    required_permissions = (
        "core:log",
        "chat:send",
        "points:read",
        "points:write",
        "minigames:play",
    )
    
    def on_load(self):
        """Inicialização do plugin."""
        # Jackpot acumulado (em memória, resetaria ao reiniciar)
        self.jackpot = 1000
        
        # Estatísticas
        self.stats = {
            "total_bets": 0,
            "total_won": 0,
            "total_lost": 0,
            "biggest_win": 0,
            "biggest_winner": "",
        }
        
        self.log_info(f"🎰 {self.name} carregado!")
        self.log_info(f"   Apostas: {self.config.min_bet} - {self.config.max_bet}")
        self.log_info(f"   Jackpot inicial: {self.jackpot}")
    
    def on_unload(self):
        """Cleanup."""
        self.log_info(f"🎰 {self.name} descarregado. Jackpot final: {self.jackpot}")
    
    # ==================== HELPERS ====================
    
    def _validate_bet(self, ctx, amount: int) -> tuple[bool, str]:
        """Valida uma aposta."""
        if amount < self.config.min_bet:
            return False, f"Aposta mínima: {self.config.min_bet}"
        if amount > self.config.max_bet:
            return False, f"Aposta máxima: {self.config.max_bet}"
        
        points = self.context.get_points(ctx.username)
        if points < amount:
            return False, f"Pontos insuficientes! Você tem {TextUtils.format_number(points)}"
        
        return True, ""
    
    def _record_result(self, username: str, bet: int, won: bool, prize: int = 0):
        """Registra resultado do jogo."""
        self.stats["total_bets"] += 1
        
        if won:
            self.stats["total_won"] += prize
            if prize > self.stats["biggest_win"]:
                self.stats["biggest_win"] = prize
                self.stats["biggest_winner"] = username
        else:
            self.stats["total_lost"] += bet
        
        # Contribuir para jackpot
        if self.config.jackpot_enabled:
            contribution = int(bet * 0.01)  # 1% vai pro jackpot
            self.jackpot += contribution
    
    async def _announce_big_win(self, ctx, prize: int, game: str):
        """Anuncia grandes vitórias."""
        if self.config.announce_big_wins and prize >= 1000:
            await ctx.send(f"🎉 GRANDE VITÓRIA! {ctx.display_name} ganhou {TextUtils.format_number(prize)} pontos no {game}! 🎉")
    
    # ==================== COMANDOS ====================
    
    @command("!coinflip", aliases=["cf", "flip"], 
             description="Joga cara ou coroa",
             usage="!coinflip <aposta> <cara/coroa>")
    @cooldown(seconds=3)
    async def coinflip(self, ctx):
        """
        Jogo de cara ou coroa simples.
        
        Exemplo: !coinflip 100 cara
        """
        if len(ctx.args) < 2:
            await ctx.reply(f"{Emoji.INFO} Uso: !coinflip <aposta> <cara/coroa>")
            return
        
        # Parse argumentos
        try:
            bet = int(ctx.args[0])
        except ValueError:
            await ctx.reply(f"{Emoji.ERROR} Aposta deve ser um número!")
            return
        
        choice = ctx.args[1].lower()
        if choice not in ("cara", "coroa", "c", "k"):
            await ctx.reply(f"{Emoji.ERROR} Escolha 'cara' ou 'coroa'!")
            return
        
        # Normalizar escolha
        choice = "cara" if choice in ("cara", "c") else "coroa"
        
        # Validar aposta
        valid, error = self._validate_bet(ctx, bet)
        if not valid:
            await ctx.reply(f"{Emoji.ERROR} {error}")
            return
        
        # Remover aposta
        self.context.remove_points(ctx.username, bet, "Coinflip - Aposta")
        
        # Jogar (aplicar house edge)
        win_chance = 50 - (self.config.house_edge * 100 / 2)
        result = "cara" if RandomUtils.chance(50) else "coroa"
        won = result == choice
        
        if won:
            prize = bet * 2
            self.context.add_points(ctx.username, prize, "Coinflip - Vitória")
            self._record_result(ctx.username, bet, True, prize)
            await ctx.reply(f"🪙 {result.upper()}! {Emoji.PARTY} {ctx.display_name} ganhou {prize} pontos!")
            await self._announce_big_win(ctx, prize, "Coinflip")
        else:
            self._record_result(ctx.username, bet, False)
            await ctx.reply(f"🪙 {result.upper()}! {Emoji.ERROR} {ctx.display_name} perdeu {bet} pontos...")
    
    @command("!slots", aliases=["slot", "cacaniqueis"],
             description="Caça-níquel",
             usage="!slots [aposta]")
    @cooldown(seconds=5)
    async def slots(self, ctx):
        """
        Caça-níquel com jackpot progressivo.
        
        Prêmios:
        - 💎💎💎 = JACKPOT!
        - ⭐⭐⭐ = 10x
        - 🍇🍇🍇 = 5x
        - 🍊🍊🍊 = 3x
        - 🍋🍋🍋 = 2x
        - 🍒🍒🍒 = 1.5x
        - Dois iguais = 0.5x
        """
        # Parse aposta (default 50)
        bet = 50
        if ctx.args:
            try:
                bet = int(ctx.args[0])
            except ValueError:
                pass
        
        # Validar
        valid, error = self._validate_bet(ctx, bet)
        if not valid:
            await ctx.reply(f"{Emoji.ERROR} {error}")
            return
        
        # Remover aposta
        self.context.remove_points(ctx.username, bet, "Slots - Aposta")
        
        # Símbolos e pesos
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎"]
        weights = {"🍒": 35, "🍋": 28, "🍊": 20, "🍇": 12, "⭐": 4, "💎": 1}
        
        # Sortear
        result = [RandomUtils.weighted_choice(weights) for _ in range(3)]
        display = " ".join(result)
        
        # Calcular prêmio
        prize = 0
        msg = ""
        
        if result[0] == result[1] == result[2]:
            # Três iguais
            if result[0] == "💎":
                prize = self.jackpot
                msg = f"🎰 {display} 💎 JACKPOT!!! 💎 {ctx.display_name} GANHOU {TextUtils.format_number(prize)} PONTOS!!!"
                self.jackpot = 1000  # Reset jackpot
            elif result[0] == "⭐":
                prize = bet * 10
                msg = f"🎰 {display} ⭐ MEGA WIN! +{prize} pontos!"
            elif result[0] == "🍇":
                prize = bet * 5
                msg = f"🎰 {display} 🍇 Grande vitória! +{prize} pontos!"
            elif result[0] == "🍊":
                prize = bet * 3
                msg = f"🎰 {display} 🍊 Vitória! +{prize} pontos!"
            elif result[0] == "🍋":
                prize = bet * 2
                msg = f"🎰 {display} 🍋 Boa! +{prize} pontos!"
            else:
                prize = int(bet * 1.5)
                msg = f"🎰 {display} +{prize} pontos!"
        
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            # Dois iguais
            prize = int(bet * 0.5)
            msg = f"🎰 {display} Par! +{prize} pontos"
        
        else:
            msg = f"🎰 {display} Nada... Jackpot atual: {TextUtils.format_number(self.jackpot)}"
        
        # Aplicar prêmio
        if prize > 0:
            self.context.add_points(ctx.username, prize, f"Slots - Prêmio")
            self._record_result(ctx.username, bet, True, prize)
            await self._announce_big_win(ctx, prize, "Slots")
        else:
            self._record_result(ctx.username, bet, False)
        
        await ctx.reply(msg)
    
    @command("!roulette", aliases=["roleta", "rol"],
             description="Roleta - aposte em cor ou número",
             usage="!roulette <aposta> <vermelho/preto/verde/numero>")
    @cooldown(seconds=5)
    async def roulette(self, ctx):
        """
        Roleta com apostas em cor ou número.
        
        Pagamentos:
        - Número exato (0-36): 35x
        - Verde (0): 35x
        - Vermelho/Preto: 2x
        """
        if len(ctx.args) < 2:
            await ctx.reply(f"{Emoji.INFO} Uso: !roulette <aposta> <vermelho/preto/verde/0-36>")
            return
        
        # Parse
        try:
            bet = int(ctx.args[0])
        except ValueError:
            await ctx.reply(f"{Emoji.ERROR} Aposta inválida!")
            return
        
        choice = ctx.args[1].lower()
        
        # Validar escolha
        valid_colors = ["vermelho", "red", "v", "preto", "black", "p", "verde", "green", "g"]
        is_number = choice.isdigit() and 0 <= int(choice) <= 36
        is_color = choice in valid_colors
        
        if not is_number and not is_color:
            await ctx.reply(f"{Emoji.ERROR} Escolha uma cor (vermelho/preto/verde) ou número (0-36)!")
            return
        
        # Validar aposta
        valid, error = self._validate_bet(ctx, bet)
        if not valid:
            await ctx.reply(f"{Emoji.ERROR} {error}")
            return
        
        # Remover aposta
        self.context.remove_points(ctx.username, bet, "Roleta - Aposta")
        
        # Números vermelhos
        red_numbers = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        
        # Sortear
        result = RandomUtils.dice(37, 1)[0] - 1  # 0-36
        
        if result == 0:
            color = "verde"
            emoji = "🟢"
        elif result in red_numbers:
            color = "vermelho"
            emoji = "🔴"
        else:
            color = "preto"
            emoji = "⚫"
        
        # Verificar vitória
        prize = 0
        
        if is_number and int(choice) == result:
            prize = bet * 35
            msg = f"🎡 {emoji} {result}! NÚMERO EXATO! {ctx.display_name} ganhou {prize}!"
        elif is_color:
            normalized = choice[0]  # v, p, ou g
            won = (
                (normalized in "vr" and color == "vermelho") or
                (normalized in "pb" and color == "preto") or
                (normalized == "g" and color == "verde")
            )
            if won:
                prize = bet * 35 if color == "verde" else bet * 2
                msg = f"🎡 {emoji} {result} ({color})! {Emoji.PARTY} +{prize} pontos!"
            else:
                msg = f"🎡 {emoji} {result} ({color})! Você apostou em {choice}..."
        
        if prize > 0:
            self.context.add_points(ctx.username, prize, "Roleta - Prêmio")
            self._record_result(ctx.username, bet, True, prize)
            await self._announce_big_win(ctx, prize, "Roleta")
        else:
            self._record_result(ctx.username, bet, False)
        
        await ctx.reply(msg)
    
    @command("!jackpot", aliases=["jp"],
             description="Ver jackpot acumulado")
    async def jackpot_cmd(self, ctx):
        """Mostra o jackpot atual."""
        if not self.config.jackpot_enabled:
            await ctx.reply(f"{Emoji.INFO} Jackpot está desativado.")
            return
        
        await ctx.reply(f"💎 Jackpot atual: {TextUtils.format_number(self.jackpot)} pontos! Use !slots para tentar ganhar!")
    
    @command("!casino", aliases=["stats"],
             description="Estatísticas do casino")
    async def casino_stats(self, ctx):
        """Mostra estatísticas do casino."""
        stats = self.stats
        
        msg = (
            f"🎰 Casino Stats | "
            f"Apostas: {stats['total_bets']} | "
            f"Ganhos: {TextUtils.format_number(stats['total_won'])} | "
            f"Perdas: {TextUtils.format_number(stats['total_lost'])}"
        )
        
        if stats['biggest_win'] > 0:
            msg += f" | Maior: {TextUtils.format_number(stats['biggest_win'])} ({stats['biggest_winner']})"
        
        await ctx.reply(msg)
    
    # ==================== EVENTOS ====================
    
    @on_event("message")
    async def on_chat_message(self, event):
        """Responde a mensagens específicas."""
        msg = event.message.lower()
        
        # Easter egg
        if "cassino" in msg or "casino" in msg:
            if RandomUtils.chance(5):  # 5% de chance
                await event.reply(f"🎰 Psst... {event.user}, tente !slots para testar a sorte!")


# Para teste local
if __name__ == "__main__":
    print("🎰 Casino Plugin")
    print("Use: chaos-sdk run casino_example.py --verbose")
