"""
Plugin Compatível com o Servidor - Exemplo Completo
====================================================

Este plugin demonstra o formato EXATO que o chaos-server espera.

O servidor chama os métodos de comando no formato:
    handler(username: str, args: List[str], **kwargs) -> Optional[str]

Onde kwargs contém:
    - is_mod: bool
    - is_sub: bool  
    - is_vip: bool
    - display_name: str
    - user_id: str

O retorno deve ser uma string (resposta) ou None.

Autor: Chaos Factory Team
"""
from chaos_sdk import Plugin, command, hook


class ServerCompatiblePlugin(Plugin):
    """
    Plugin no formato exato do chaos-server.
    
    Use este exemplo como base para plugins que precisam
    funcionar diretamente no servidor.
    """
    
    # Metadados obrigatórios (o servidor lê esses atributos)
    name = "Server Compatible"
    version = "1.0.0"
    author = "Chaos Factory"
    description = "Plugin compatível com chaos-server"
    
    # Permissões que o plugin solicita
    # O servidor filtra e concede apenas as permitidas
    required_permissions = (
        "core:log",         # Permite logging
        "chat:send",        # Permite enviar mensagens
        "points:read",      # Permite ler pontos
        "points:write",     # Permite modificar pontos
    )
    
    def on_load(self):
        """
        Chamado quando o plugin é carregado pelo servidor.
        
        Use para:
        - Registrar comandos
        - Inicializar estado
        - Configurar recursos
        """
        # Registrar comandos no formato do servidor
        self.register_command("ping", self.cmd_ping)
        self.register_command("points", self.cmd_points)
        self.register_command("give", self.cmd_give)
        self.register_command("mod", self.cmd_mod_only)
        
        self.log_info("Plugin carregado com sucesso!")
    
    def on_unload(self):
        """Chamado quando o plugin é descarregado."""
        self.log_info("Plugin descarregado")
    
    def on_enable(self):
        """Chamado quando o plugin é habilitado."""
        self.enabled = True
        self.log_info("Plugin habilitado")
    
    def on_disable(self):
        """Chamado quando o plugin é desabilitado."""
        self.enabled = False
        self.log_info("Plugin desabilitado")
    
    # ==================== COMANDOS ====================
    # Formato: def cmd_X(self, username, args, **kwargs) -> Optional[str]
    
    def cmd_ping(self, username: str, args: list, **kwargs) -> str:
        """
        Comando simples de ping.
        
        Uso: !ping
        """
        display = kwargs.get('display_name', username)
        return f"🏓 Pong, {display}!"
    
    def cmd_points(self, username: str, args: list, **kwargs) -> str:
        """
        Mostra pontos do usuário ou de outro usuário.
        
        Uso: !points [usuario]
        """
        # Se passou um target, consultar esse usuário
        target = args[0] if args else username
        
        # Usar o contexto para obter pontos (requer points:read)
        if self.context:
            points = self.context.get_points(target)
            return f"💰 {target} tem {points:,} pontos"
        
        return "❌ Sistema de pontos indisponível"
    
    def cmd_give(self, username: str, args: list, **kwargs) -> str:
        """
        Dá pontos para outro usuário (requer mod).
        
        Uso: !give <usuario> <quantidade>
        """
        # Verificar se é mod
        is_mod = kwargs.get('is_mod', False)
        if not is_mod:
            return "❌ Apenas moderadores podem usar este comando"
        
        # Validar argumentos
        if len(args) < 2:
            return "❌ Uso: !give <usuario> <quantidade>"
        
        target = args[0]
        try:
            amount = int(args[1])
        except ValueError:
            return "❌ Quantidade inválida"
        
        if amount <= 0:
            return "❌ Quantidade deve ser positiva"
        
        # Usar contexto para dar pontos (requer points:write)
        if self.context:
            success = self.context.add_points(target, amount, f"Dado por {username}")
            if success:
                return f"✅ {username} deu {amount:,} pontos para {target}!"
            return "❌ Não foi possível dar pontos"
        
        return "❌ Sistema de pontos indisponível"
    
    def cmd_mod_only(self, username: str, args: list, **kwargs) -> str:
        """
        Comando exclusivo para moderadores.
        
        Uso: !mod
        """
        # O servidor passa is_mod, is_sub, is_vip nos kwargs
        is_mod = kwargs.get('is_mod', False)
        is_sub = kwargs.get('is_sub', False)
        is_vip = kwargs.get('is_vip', False)
        
        if not is_mod:
            return "❌ Este comando é apenas para moderadores"
        
        # Exibir informações
        roles = []
        if is_mod:
            roles.append("Mod")
        if is_sub:
            roles.append("Sub")
        if is_vip:
            roles.append("VIP")
        
        return f"✅ {username} ({', '.join(roles)}) - Acesso autorizado!"
    
    # ==================== HOOKS DE EVENTOS ====================
    
    def on_message(self, username: str, message: str, **kwargs) -> None:
        """
        Chamado para CADA mensagem do chat.
        
        Use para:
        - Filtros de spam
        - Auto-resposta
        - Tracking
        
        IMPORTANTE: Este método pode ser chamado MUITAS vezes.
        Mantenha-o rápido e eficiente.
        """
        # Exemplo: contar mensagens
        if not hasattr(self, '_msg_count'):
            self._msg_count = 0
        self._msg_count += 1
    
    def on_points_earned(self, username: str, amount: int, reason: str):
        """Chamado quando usuário ganha pontos."""
        pass
    
    def on_points_spent(self, username: str, amount: int, reason: str):
        """Chamado quando usuário gasta pontos."""
        pass
    
    def on_stream_start(self):
        """Chamado quando a live inicia."""
        self.log_info("Live iniciada!")
    
    def on_stream_end(self):
        """Chamado quando a live termina."""
        self.log_info("Live encerrada!")
    
    def on_viewer_join(self, username: str):
        """Chamado quando viewer entra no chat."""
        pass
    
    def on_viewer_leave(self, username: str):
        """Chamado quando viewer sai do chat."""
        pass


# Alternativa: Usando decoradores (também compatível)
class DecoratorStylePlugin(Plugin):
    """
    Mesmo plugin usando decoradores do SDK.
    
    Os decoradores @command configuram _is_command e _command_name
    que são lidos pelo servidor.
    """
    
    name = "Decorator Style"
    version = "1.0.0"
    author = "Chaos Factory"
    description = "Plugin usando decoradores"
    required_permissions = ("core:log", "chat:send")
    
    @command("hello", aliases=["hi", "ola"])
    def cmd_hello(self, username: str, args: list, **kwargs) -> str:
        """Comando usando decorador."""
        return f"Olá, {username}! 👋"
    
    @command("echo")
    def cmd_echo(self, username: str, args: list, **kwargs) -> str:
        """Repete a mensagem."""
        if not args:
            return "❌ Uso: !echo <mensagem>"
        return " ".join(args)
    
    @hook("stream_start")
    def on_live(self):
        """Hook para início de live."""
        self.log_info("Stream começou!")
    
    def on_load(self):
        """Os comandos decorados são registrados automaticamente."""
        self.log_info("Plugin com decoradores carregado!")


# Para teste local
if __name__ == "__main__":
    # Teste básico sem servidor
    plugin = ServerCompatiblePlugin()
    
    # Simular chamada de comando
    result = plugin.cmd_ping("usuario_teste", [], display_name="Usuario Teste")
    print(f"Resultado: {result}")
    
    result = plugin.cmd_mod_only("mod_teste", [], is_mod=True, is_sub=True)
    print(f"Resultado mod: {result}")
    
    result = plugin.cmd_mod_only("user_normal", [], is_mod=False)
    print(f"Resultado não-mod: {result}")
