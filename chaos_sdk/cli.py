"""
CLI principal do Chaos SDK.

Comandos disponíveis:
    chaos-sdk new <nome>        - Cria novo plugin a partir de template
    chaos-sdk validate <arquivo> - Valida plugin
    chaos-sdk run <arquivo>      - Executa plugin localmente
    chaos-sdk docs              - Abre documentação
"""
import sys
import os
import shutil
from pathlib import Path


PLUGIN_TEMPLATE = '''"""
{name} - Plugin para Chaos Factory
{description}

Autor: {author}
Versão: 1.0.0
"""
from chaos_sdk import Plugin, command
from chaos_sdk.decorators import cooldown, require_mod, on_event
from chaos_sdk.utils import Emoji, RandomUtils


class {class_name}(Plugin):
    """
    {description}
    """
    
    name = "{name}"
    version = "1.0.0"
    author = "{author}"
    description = "{description}"
    
    # Permissões necessárias
    required_permissions = (
        "core:log",
        "chat:send",
        "points:read",
        "points:write",
    )
    
    def on_load(self):
        """Chamado quando o plugin é carregado."""
        self.log_info(f"{{self.name}} v{{self.version}} carregado!")
    
    def on_unload(self):
        """Chamado quando o plugin é descarregado."""
        self.log_info(f"{{self.name}} descarregado.")
    
    # ==================== COMANDOS ====================
    
    @command("!hello", description="Diz olá para o usuário")
    @cooldown(seconds=5)
    async def hello(self, ctx):
        """Comando de exemplo."""
        await ctx.reply(f"{{Emoji.HEART}} Olá, {{ctx.display_name}}!")
    
    @command("!dice", aliases=["d"], description="Rola um dado")
    @cooldown(seconds=3)
    async def dice(self, ctx):
        """Rola um dado de 6 lados."""
        result = RandomUtils.dice(6)[0]
        await ctx.reply(f"{{Emoji.DICE}} {{ctx.username}} rolou {{result}}!")
    
    @command("!points", description="Mostra seus pontos")
    async def points(self, ctx):
        """Mostra pontos do usuário."""
        if not self.context:
            await ctx.reply("{{Emoji.ERROR}} Sistema indisponível.")
            return
        
        points = self.context.get_points(ctx.username)
        await ctx.reply(f"{{Emoji.POINTS}} {{ctx.display_name}} tem {{points}} pontos!")
    
    # ==================== EVENTOS ====================
    
    @on_event("follow")
    async def on_follow(self, event):
        """Agradece novos seguidores."""
        # Descomentar para ativar:
        # await event.reply(f"{{Emoji.HEART}} Obrigado pelo follow, {{event.user}}!")
        pass
    
    @on_event("message")
    async def on_message(self, event):
        """Processa todas as mensagens."""
        # Exemplo: responder a palavra específica
        # if "boa noite" in event.message.lower():
        #     await event.reply(f"Boa noite, {{event.user}}! {{Emoji.PARTY}}")
        pass


# Para teste local
if __name__ == "__main__":
    print("Use 'chaos-sdk run {filename}' para testar este plugin.")
'''


GAME_PLUGIN_TEMPLATE = '''"""
{name} - Plugin de Jogo para Chaos Factory
{description}

Autor: {author}
Versão: 1.0.0
"""
from chaos_sdk import Plugin, command
from chaos_sdk.decorators import cooldown, cost_points, on_event
from chaos_sdk.utils import Emoji, RandomUtils, TextUtils
from chaos_sdk.config import PluginConfig, int_field, bool_field


class {class_name}(Plugin):
    """
    Plugin de jogo: {description}
    """
    
    name = "{name}"
    version = "1.0.0"
    author = "{author}"
    description = "{description}"
    
    # Configurações do plugin
    config = PluginConfig(
        min_bet=int_field(default=10, min_value=1, description="Aposta mínima"),
        max_bet=int_field(default=1000, max_value=10000, description="Aposta máxima"),
        enabled=bool_field(default=True, description="Plugin ativo"),
    )
    
    required_permissions = (
        "core:log",
        "chat:send",
        "points:read",
        "points:write",
        "minigames:play",
    )
    
    def on_load(self):
        self.log_info(f"{{self.name}} carregado! Min: {{self.config.min_bet}}, Max: {{self.config.max_bet}}")
    
    # ==================== COMANDOS ====================
    
    @command("!coinflip", aliases=["cf"], description="Joga cara ou coroa")
    @cooldown(seconds=5)
    async def coinflip(self, ctx):
        """
        Joga cara ou coroa.
        Uso: !coinflip <aposta> <cara/coroa>
        """
        if len(ctx.args) < 2:
            await ctx.reply(f"{{Emoji.INFO}} Uso: !coinflip <aposta> <cara/coroa>")
            return
        
        try:
            bet = int(ctx.args[0])
        except ValueError:
            await ctx.reply(f"{{Emoji.ERROR}} Aposta inválida!")
            return
        
        choice = ctx.args[1].lower()
        if choice not in ("cara", "coroa"):
            await ctx.reply(f"{{Emoji.ERROR}} Escolha 'cara' ou 'coroa'!")
            return
        
        # Validar aposta
        if bet < self.config.min_bet:
            await ctx.reply(f"{{Emoji.ERROR}} Aposta mínima: {{self.config.min_bet}}")
            return
        if bet > self.config.max_bet:
            await ctx.reply(f"{{Emoji.ERROR}} Aposta máxima: {{self.config.max_bet}}")
            return
        
        # Verificar pontos
        points = self.context.get_points(ctx.username)
        if points < bet:
            await ctx.reply(f"{{Emoji.ERROR}} Pontos insuficientes! Você tem {{points}}.")
            return
        
        # Jogar
        result = "cara" if RandomUtils.chance(50) else "coroa"
        won = result == choice
        
        if won:
            self.context.add_points(ctx.username, bet, "Coinflip - Vitória")
            await ctx.reply(f"{{Emoji.PARTY}} {{result.upper()}}! {{ctx.username}} ganhou {{bet}} pontos!")
        else:
            self.context.remove_points(ctx.username, bet, "Coinflip - Derrota")
            await ctx.reply(f"{{Emoji.DICE}} {{result.upper()}}! {{ctx.username}} perdeu {{bet}} pontos...")
    
    @command("!slots", description="Caça-níquel")
    @cooldown(seconds=10)
    @cost_points(50)
    async def slots(self, ctx):
        """
        Joga caça-níquel (custa 50 pontos).
        """
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎"]
        weights = {{"🍒": 30, "🍋": 25, "🍊": 20, "🍇": 15, "⭐": 8, "💎": 2}}
        
        # Sortear 3 símbolos
        result = [RandomUtils.weighted_choice(weights) for _ in range(3)]
        display = " | ".join(result)
        
        # Calcular prêmio
        prize = 0
        if result[0] == result[1] == result[2]:
            if result[0] == "💎":
                prize = 1000
                msg = "🎰 JACKPOT!!! 💎💎💎"
            elif result[0] == "⭐":
                prize = 500
                msg = "🎰 MEGA WIN! ⭐⭐⭐"
            else:
                prize = 200
                msg = f"🎰 VITÓRIA! {{display}}"
        elif result[0] == result[1] or result[1] == result[2]:
            prize = 75
            msg = f"🎰 Par! {{display}}"
        else:
            msg = f"🎰 {{display}} - Tente novamente!"
        
        if prize > 0:
            self.context.add_points(ctx.username, prize, f"Slots - Prêmio {{prize}}")
            msg += f" +{{prize}} pontos!"
        
        await ctx.reply(msg)


if __name__ == "__main__":
    print("Use 'chaos-sdk run {filename}' para testar este plugin.")
'''


def create_plugin(name: str, plugin_type: str = "basic"):
    """Cria um novo plugin a partir do template."""
    # Normalizar nome
    class_name = "".join(word.capitalize() for word in name.split())
    if not class_name.endswith("Plugin"):
        class_name += "Plugin"
    
    filename = name.lower().replace(" ", "_") + ".py"
    
    # Escolher template
    if plugin_type == "game":
        template = GAME_PLUGIN_TEMPLATE
    else:
        template = PLUGIN_TEMPLATE
    
    # Substituir placeholders
    content = template.format(
        name=name,
        class_name=class_name,
        author=os.getenv("USER", "Desenvolvedor"),
        description=f"Plugin {name}",
        filename=filename,
    )
    
    # Criar arquivo
    if os.path.exists(filename):
        print(f"❌ Arquivo já existe: {filename}")
        return False
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Plugin criado: {filename}")
    print(f"   Classe: {class_name}")
    print(f"\n💡 Próximos passos:")
    print(f"   1. Edite {filename} e adicione seus comandos")
    print(f"   2. Valide: chaos-sdk validate {filename}")
    print(f"   3. Teste: chaos-sdk run {filename}")
    return True


def validate_plugin(file_path: str):
    """Valida um plugin."""
    from chaos_sdk.validator import validate_plugin as _validate
    result = _validate(file_path)
    
    print("=" * 50)
    print(f"📋 Validação: {os.path.basename(file_path)}")
    print("=" * 50)
    
    if result.info:
        print(f"\n📦 Plugin: {result.info.get('name', 'N/A')} v{result.info.get('version', 'N/A')}")
        if result.info.get('commands'):
            print(f"🎮 Comandos: {', '.join(result.info['commands'])}")
    
    if result.errors:
        print(f"\n❌ ERROS ({len(result.errors)}):")
        for error in result.errors:
            print(f"   • {error}")
    
    if result.warnings:
        print(f"\n⚠️  AVISOS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"   • {warning}")
    
    print("")
    if result.valid:
        print("✅ Plugin válido!")
    else:
        print("❌ Plugin com erros")
    
    return result.valid


def run_plugin(file_path: str, verbose: bool = False):
    """Executa plugin no ambiente de teste."""
    # Importar runner
    try:
        from chaos_sdk.testing.runner import main as runner_main
        import asyncio
        
        args = ["runner", file_path]
        if verbose:
            args.append("--verbose")
        
        asyncio.run(runner_main(args))
    except ImportError as e:
        print(f"❌ Erro ao importar runner: {e}")
        print("Tente: python -m chaos_sdk.testing.runner " + file_path)


def show_help():
    """Mostra ajuda."""
    print("""
🎪 Chaos SDK - Kit de Desenvolvimento de Plugins
================================================

Comandos:
    chaos-sdk new <nome>         Cria novo plugin
    chaos-sdk new <nome> --game  Cria plugin de jogo
    chaos-sdk validate <arquivo> Valida plugin
    chaos-sdk run <arquivo>      Testa plugin localmente
    chaos-sdk docs               Abre documentação

Exemplos:
    chaos-sdk new "Meu Plugin"
    chaos-sdk new "Casino" --game
    chaos-sdk validate meu_plugin.py
    chaos-sdk run meu_plugin.py --verbose

Documentação: https://chaos.mroz.dev.br/docs/sdk
""")


def main():
    """Ponto de entrada CLI."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command in ("help", "-h", "--help"):
        show_help()
    
    elif command == "new":
        if len(sys.argv) < 3:
            print("❌ Uso: chaos-sdk new <nome> [--game]")
            return
        name = sys.argv[2]
        plugin_type = "game" if "--game" in sys.argv else "basic"
        create_plugin(name, plugin_type)
    
    elif command == "validate":
        if len(sys.argv) < 3:
            print("❌ Uso: chaos-sdk validate <arquivo.py>")
            return
        file_path = sys.argv[2]
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        validate_plugin(file_path)
    
    elif command == "run":
        if len(sys.argv) < 3:
            print("❌ Uso: chaos-sdk run <arquivo.py> [--verbose]")
            return
        file_path = sys.argv[2]
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        run_plugin(file_path, verbose)
    
    elif command == "docs":
        import webbrowser
        webbrowser.open("https://chaos.mroz.dev.br/docs/sdk")
        print("📖 Abrindo documentação no navegador...")
    
    else:
        print(f"❌ Comando desconhecido: {command}")
        show_help()


if __name__ == "__main__":
    main()
