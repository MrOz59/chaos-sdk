"""
Plugin de exemplo - Hello World

Este plugin demonstra o formato compatível com o chaos-server.
"""
from chaos_sdk import Plugin, command


class HelloWorldPlugin(Plugin):
    """
    Plugin de exemplo básico.
    
    Demonstra:
    - Estrutura básica de plugin
    - Decorador @command com formato do servidor
    - Método register_command() do servidor
    """
    
    name = "Hello World"
    version = "1.0.0"
    author = "Chaos Factory"
    description = "Plugin de exemplo básico"
    required_permissions = ["chat:send"]  # Permissões necessárias
    
    def on_load(self):
        """Chamado quando o plugin é carregado."""
        # Método 1: Registrar comando manualmente (formato servidor)
        self.register_command("hello", self.cmd_hello)
        self.register_command("dice", self.cmd_dice)
        
        # Os aliases também podem ser registrados
        self.register_command("hi", self.cmd_hello)
        self.register_command("ola", self.cmd_hello)
        
        self.log_info("Plugin carregado com sucesso!")
    
    def cmd_hello(self, username: str, args: list, **kwargs) -> str:
        """
        Diz olá para o usuário.
        
        Formato compatível com o servidor:
        - username: Nome do usuário que executou
        - args: Lista de argumentos do comando
        - **kwargs: is_mod, is_sub, is_vip, etc.
        
        Returns:
            String de resposta (enviada automaticamente ao chat)
        """
        display = kwargs.get('display_name', username)
        return f"Olá, {display}! 👋"
    
    def cmd_dice(self, username: str, args: list, **kwargs) -> str:
        """Rola um dado de 6 lados."""
        import random
        
        # Pode usar args para customizar
        sides = 6
        if args:
            try:
                sides = int(args[0])
                sides = max(2, min(100, sides))  # Limitar entre 2-100
            except ValueError:
                pass
        
        result = random.randint(1, sides)
        display = kwargs.get('display_name', username)
        return f"🎲 {display} rolou {result}! (d{sides})"


# Plugin alternativo usando decoradores (também compatível)
class HelloWorldPluginDecorator(Plugin):
    """
    Mesmo plugin usando decoradores.
    
    Ambos os formatos funcionam com o servidor.
    """
    
    name = "Hello World Decorator"
    version = "1.0.0"
    author = "Chaos Factory"
    description = "Plugin de exemplo com decoradores"
    required_permissions = ["chat:send"]
    
    @command("hello2", aliases=["hi2"])
    def cmd_hello2(self, username: str, args: list, **kwargs) -> str:
        """Diz olá usando decorador."""
        return f"Olá via decorador, {username}! 👋"
    
    def on_load(self):
        """Os comandos decorados são registrados automaticamente."""
        self.log_info("Plugin com decoradores carregado!")
