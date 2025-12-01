"""
Exemplo de Plugin de Jogo
Demonstra como criar um plugin para integrar um jogo
"""

import sys
import os

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from chaos_sdk.plugins.base_plugin import GamePlugin, command
from chaos_sdk.plugins.permissions import PluginSecurityError


class ExampleGamePlugin(GamePlugin):
    """
    Plugin de exemplo para demonstração de integração com jogos.
    
    Este plugin demonstra como criar comandos básicos que interagem
    com o jogo através de teclas e cliques do mouse, além de gerenciar
    estado interno do jogo (HP, Mana).
    """
    
    name = "Example Game"
    version = "1.0.0"
    author = "StreamBot Team"
    description = "Plugin de exemplo mostrando comandos básicos: pular, atacar, curar e ver status do personagem"
    # Atualizado para o novo sistema seguro: apenas enfileirar macros via contexto
    required_permissions = ("macro:enqueue", "core:log")
    
    def on_load(self):
        """Registrar comandos quando plugin carregar"""
        self.log_info("Carregando Example Game Plugin...")
        
        # Registrar comandos manualmente
        self.register_commands({
            "jump": self.cmd_jump,
            "attack": self.cmd_attack,
            "heal": self.cmd_heal,
            "status": self.cmd_status
        })
        
        # Estado do jogo (exemplo)
        self.player_health = 100
        self.player_mana = 50
        
        self.log_info("Example Game Plugin carregado!")
    
    def cmd_jump(self, username: str, args: list, **kwargs) -> str:
        """
        Faz o personagem pular pressionando a tecla espaço.
        Comando simples sem custo ou requisitos.
        """
        # Usa macro_run_keys para acionar uma tecla (seguro, via fila do tenant)
        if self.context:
            # Exemplo: usamos a tecla 'w' como placeholder para pulo
            self.context.macro_run_keys(username=username, keys="w", delay=0.08, command="jump")
        return f"{username} fez o personagem pular! 🦘"
    
    def cmd_attack(self, username: str, args: list, **kwargs) -> str:
        """
        Executa um ataque clicando com o botão esquerdo do mouse.
        Consome 10 de mana por ataque. Se não houver mana suficiente, o ataque falha.
        """
        # Verificar se tem mana
        if self.player_mana < 10:
            return f"{username}, sem mana para atacar! ⚡"
        
        # Mouse não é exposto a plugins; use uma tecla de ataque configurável (ex.: 'f')
        if self.context:
            self.context.macro_run_keys(username=username, keys="f", delay=0.08, command="attack")
        self.player_mana -= 10
        
        return f"{username} atacou! ⚔️ (Mana: {self.player_mana})"
    
    def cmd_heal(self, username: str, args: list, **kwargs) -> str:
        """
        Cura o personagem pressionando a tecla H, restaurando 25 de HP.
        Apenas moderadores podem usar este comando.
        """
        # Verificar cooldown (apenas mods podem usar)
        if not kwargs.get('is_mod', False):
            return f"{username}, apenas mods podem usar !heal! 🚫"
        
        if self.context:
            self.context.macro_run_keys(username=username, keys="h", delay=0.08, command="heal")
        self.player_health = min(100, self.player_health + 25)
        
        return f"❤️ Personagem curado! HP: {self.player_health}"
    
    def cmd_status(self, username: str, args: list, **kwargs) -> str:
        """
        Mostra o status atual do personagem incluindo HP e Mana.
        Comando gratuito disponível para todos.
        """
        return f"📊 Status | HP: {self.player_health} ❤️ | Mana: {self.player_mana} ⚡"
    
    def on_message(self, username: str, message: str, **kwargs):
        """Hook - Regenera mana a cada mensagem"""
        self.player_mana = min(50, self.player_mana + 1)
    
    def on_points_spent(self, username: str, amount: int, reason: str):
        """Hook - Quando usuário gasta pontos"""
        if amount >= 100:
            self.log_info(f"{username} gastou {amount} pontos em {reason}!")
    
    def on_stream_start(self):
        """Hook - Quando stream começa"""
        self.player_health = 100
        self.player_mana = 50
        self.log_info("Stream iniciada! Stats resetados.")
    
    def on_stream_end(self):
        """Hook - Quando stream termina"""
        self.log_info("Stream encerrada. Salvando stats...")


# Exemplo alternativo usando decorators
class AdvancedGamePlugin(GamePlugin):
    """Exemplo com decorators"""
    
    name = "Advanced Game"
    version = "1.0.0"
    author = "StreamBot"
    description = "Plugin avançado com decorators"
    required_permissions = ("macro:enqueue", "core:log", "points:read", "points:write")
    
    def on_load(self):
        if not self.context:
            raise PluginSecurityError("Contexto não disponível")
        # Auto-registrar comandos decorados
        self.log_info("Iniciando registro de comandos...")
        for name in dir(self):
            attr = getattr(self, name)
            if hasattr(attr, '_is_command'):
                cmd_name = getattr(attr, '_command_name')
                self.register_command(cmd_name, attr)
                self.log_info(f"  Registrado: !{cmd_name}")
                
                # Registrar aliases
                for alias in getattr(attr, '_command_aliases', []):
                    self.register_command(alias, attr)
                    self.log_info(f"  Alias: !{alias} -> !{cmd_name}")
        
        self.log_info(f"Comandos registrados: {list(self.commands.keys())}")
    
    @command("move", aliases=["go", "walk"])
    def cmd_move(self, username: str, args: list, **kwargs) -> str:
        """
        Move o personagem na direção especificada.
        Uso: !move <direção>
        Direções válidas: frente, tras, esquerda, direita
        """
        if not args:
            return f"{username}, use: !move <direção>"
        
        direction = args[0].lower()
        key_map = {
            "frente": "w",
            "tras": "s",
            "esquerda": "a",
            "direita": "d"
        }
        
        if direction in key_map:
            if self.context:
                self.context.macro_run_keys(username=username, keys=key_map[direction], delay=0.08, command="move")
            return f"{username} moveu para {direction}! ➡️"
        
        return f"Direção inválida! Use: frente, tras, esquerda, direita"
    
    @command("combo")
    def cmd_combo(self, username: str, args: list, **kwargs) -> str:
        """
        Executa um combo especial pressionando Q, W, E, R em sequência.
        Custo: 50 pontos
        Requer pontos suficientes para ser executado.
        """
        # Verificar pontos via contexto seguro
        if self.context:
            points = int(self.context.get_points(username))
            if points < 50:
                return f"{username}, você precisa de 50 pontos! (Você tem: {points})"
            self.context.remove_points(username, 50, "combo especial")
        
        # Executar combo com sequência segura
        if self.context:
            self.context.macro_run_keys(username=username, keys="QWER", delay=0.1, command="combo")
        
        return f"{username} executou combo especial! 💥 (-50 pts)"


if __name__ == "__main__":
    # Teste standalone
    plugin = ExampleGamePlugin()
    plugin.on_load()
    
    print("\n🧪 Testando plugin...")
    print(plugin.cmd_jump("TestUser", []))
    print(plugin.cmd_attack("TestUser", []))
    print(plugin.cmd_status("TestUser", []))
    print(plugin.cmd_heal("TestUser", [], is_mod=True))
