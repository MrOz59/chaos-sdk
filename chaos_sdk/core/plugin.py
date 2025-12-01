"""
Classes base para plugins Chaos Factory.

Compatível com o sistema de plugins do chaos-server.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Iterable, Set
import logging

logger = logging.getLogger(__name__)


# Permissões disponíveis (espelha chaos-server/app/plugins/permissions.py)
ALLOWED_PERMISSIONS: Dict[str, str] = {
    "core:log": "Permite registrar mensagens nos logs do servidor.",
    "chat:send": "Autoriza envio de mensagens no chat via contexto seguro.",
    "points:read": "Autoriza consulta ao saldo de pontos dos usuários.",
    "points:write": "Autoriza adicionar/remover pontos.",
    "voting:read": "Permite ler votações ativas e resultados.",
    "voting:vote": "Permite votar em votações ativas.",
    "voting:manage": "Permite criar/encerrar votações.",
    "audio:play": "Permite tocar sons predefinidos.",
    "audio:tts": "Permite enfileirar TTS.",
    "audio:control": "Permite parar/limpar fila de áudio e consultar status.",
    "minigames:play": "Permite invocar minigames via roteador seguro.",
    "leaderboard:read": "Permite ler leaderboard de pontos.",
    "macro:enqueue": "Permite enfileirar execução de teclas via MacroQueue.",
}

DEFAULT_PERMISSIONS: Set[str] = {"core:log"}


class PluginSecurityError(RuntimeError):
    """Disparado quando um plugin tenta executar operação sem permissão."""
    pass


class BasePlugin(ABC):
    """
    Classe base para todos os plugins do StreamBot.
    
    Compatível com o sistema de plugins do chaos-server.
    Plugins podem estender funcionalidades do bot sem modificar o core.
    
    Atributos de classe obrigatórios:
        name: Nome do plugin
        version: Versão (semver)
        author: Autor do plugin
        description: Descrição do plugin
        required_permissions: Permissões necessárias
    
    Exemplo:
        class MeuPlugin(BasePlugin):
            name = "MeuPlugin"
            version = "1.0.0"
            author = "SeuNome"
            description = "Descrição do plugin"
            required_permissions = ["chat:send", "points:read"]
            
            def on_load(self):
                self.register_command("hello", self.cmd_hello)
            
            def cmd_hello(self, username, args, **kwargs):
                return f"Olá, {username}!"
    """
    
    # Metadados do plugin (definir nas subclasses)
    name: str = "Unnamed Plugin"
    version: str = "1.0.0"
    author: str = "Unknown"
    description: str = "No description"
    required_permissions: Iterable[str] = ()
    
    def __init__(self, bot_instance=None):
        """
        Inicializa o plugin.
        
        Args:
            bot_instance: Referência ao bot principal para acesso às APIs
        """
        self._bot = bot_instance
        self.enabled = True
        self.commands: Dict[str, Callable] = {}
        self.hooks: Dict[str, Callable] = {}
        self.config: Dict[str, Any] = {}
        
        # Sistema de permissões
        requested = set(self.required_permissions or [])
        if not requested:
            requested = set(DEFAULT_PERMISSIONS)
        self._requested_permissions: Set[str] = requested
        self._granted_permissions: Set[str] = set(DEFAULT_PERMISSIONS)
        
        # Contexto será injetado pelo loader
        self.context: Optional[Any] = None
        
        # Registrar comandos decorados
        self._register_commands()
        
        logger.info(f"🔌 Plugin carregado: {self.name} v{self.version}")
    
    @property
    def bot(self):
        """Acesso ao bot (depreciado - use self.context)."""
        logger.warning("[%s] Acesso direto ao bot está depreciado. Use self.context.", self.name)
        return self._bot
    
    def _bind_context(self, context):
        """Vincula o contexto de execução (chamado pelo loader)."""
        self.context = context
    
    def _set_granted_permissions(self, permissions: Set[str]):
        """Define permissões concedidas (chamado pelo loader)."""
        self._granted_permissions = permissions
    
    def _ensure_permission(self, permission: str):
        """Verifica se o plugin tem permissão para uma operação."""
        if permission not in self._granted_permissions:
            raise PluginSecurityError(
                f"Plugin '{self.name}' tentou usar '{permission}' sem permissão."
            )
    
    def _register_commands(self):
        """Registra comandos decorados com @command."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name, None)
            if attr is None:
                continue
            
            # Suportar ambos os formatos de decorador
            if hasattr(attr, "_command_info"):
                info = attr._command_info
                cmd_name = info.get("name", attr_name).lstrip("!")
                self.commands[cmd_name] = attr
            elif hasattr(attr, "_is_command") and attr._is_command:
                cmd_name = getattr(attr, "_command_name", attr_name.replace("cmd_", ""))
                self.commands[cmd_name] = attr
                # Registrar aliases
                for alias in getattr(attr, "_command_aliases", []):
                    self.commands[alias] = attr
            
            # Registrar hooks de eventos
            if hasattr(attr, "_is_hook") and attr._is_hook:
                event = getattr(attr, "_hook_event", None)
                if event:
                    self.hooks[event] = attr
            elif hasattr(attr, "_event_info"):
                event = attr._event_info.get("event")
                if event:
                    self.hooks[event] = attr
    
    # ==================== LIFECYCLE ====================
    
    @abstractmethod
    def on_load(self):
        """
        Chamado quando o plugin é carregado.
        Use para inicialização, registrar comandos, etc.
        """
        pass
    
    def on_unload(self):
        """
        Chamado quando o plugin é descarregado.
        Use para cleanup de recursos.
        """
        pass
    
    def on_enable(self):
        """Chamado quando plugin é habilitado."""
        self.enabled = True
        logger.info(f"✅ Plugin habilitado: {self.name}")
    
    def on_disable(self):
        """Chamado quando plugin é desabilitado."""
        self.enabled = False
        logger.info(f"❌ Plugin desabilitado: {self.name}")
    
    # ==================== HOOKS ====================
    
    def on_command(self, command: str, username: str, args: List[str], **kwargs) -> Optional[str]:
        """
        Hook chamado quando um comando é executado.
        
        Args:
            command: Nome do comando (sem !)
            username: Usuário que executou
            args: Argumentos do comando
            **kwargs: is_mod, is_sub, is_vip, etc.
        
        Returns:
            String de resposta ou None
        """
        if command in self.commands:
            return self.commands[command](username, args, **kwargs)
        return None
    
    def on_message(self, username: str, message: str, **kwargs) -> Optional[str]:
        """
        Hook chamado para cada mensagem do chat.
        
        Args:
            username: Usuário que enviou
            message: Conteúdo da mensagem
            **kwargs: is_mod, is_sub, etc.
        
        Returns:
            Resposta opcional
        """
        pass
    
    def on_points_earned(self, username: str, amount: int, reason: str):
        """Hook chamado quando usuário ganha pontos."""
        pass
    
    def on_points_spent(self, username: str, amount: int, reason: str):
        """Hook chamado quando usuário gasta pontos."""
        pass
    
    def on_stream_start(self):
        """Hook chamado quando live inicia."""
        pass
    
    def on_stream_end(self):
        """Hook chamado quando live termina."""
        pass
    
    def on_viewer_join(self, username: str):
        """Hook chamado quando viewer entra no chat."""
        pass
    
    def on_viewer_leave(self, username: str):
        """Hook chamado quando viewer sai do chat."""
        pass
    
    # ==================== UTILITIES ====================
    
    def register_command(self, command: str, handler: Callable):
        """
        Registra um novo comando.
        
        Args:
            command: Nome do comando (sem !)
            handler: Função que processa o comando
        """
        self.commands[command] = handler
        logger.debug(f"📝 Comando registrado: !{command} por {self.name}")
    
    def register_commands(self, commands: Dict[str, Callable]):
        """Registra múltiplos comandos de uma vez."""
        for cmd, handler in commands.items():
            self.register_command(cmd, handler)
    
    def get_config(self, key: str, default=None):
        """Obtém configuração do bot."""
        self._ensure_permission("config:read")
        if self._bot and hasattr(self._bot, 'config'):
            return getattr(self._bot.config, key, default)
        return default
    
    def log_info(self, message: str):
        """Log info com prefixo do plugin."""
        self._ensure_permission("core:log")
        logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str):
        """Log error com prefixo do plugin."""
        self._ensure_permission("core:log")
        logger.error(f"[{self.name}] {message}")
    
    # ==================== CONTEXT API (via self.context) ====================
    
    async def send_chat(self, message: str, platform: str = "twitch") -> bool:
        """Envia mensagem no chat (requer permission chat:send)."""
        if self.context:
            return await self.context.send_chat(message, platform)
        return False
    
    def get_points(self, username: str) -> int:
        """Obtém pontos de um usuário (requer permission points:read)."""
        if self.context:
            return self.context.get_points(username)
        return 0
    
    def add_points(self, username: str, amount: int, reason: str = '') -> bool:
        """Adiciona pontos a um usuário (requer permission points:write)."""
        if self.context:
            return self.context.add_points(username, amount, reason)
        return False
    
    def remove_points(self, username: str, amount: int, reason: str = '') -> bool:
        """Remove pontos de um usuário (requer permission points:write)."""
        if self.context:
            return self.context.remove_points(username, amount, reason)
        return False


class Plugin(BasePlugin):
    """
    Classe principal para plugins simples.
    Estenda esta classe para criar plugins.
    """
    
    def on_load(self):
        """Override este método para inicialização."""
        logger.info(f"Plugin {self.name} v{self.version} carregado")
    
    def on_unload(self):
        """Override este método para cleanup."""
        logger.info(f"Plugin {self.name} descarregado")


class GamePlugin(BasePlugin):
    """
    Plugin especializado para integração com jogos.
    Adiciona métodos para controle de teclado/mouse.
    """
    
    def __init__(self, bot_instance=None):
        super().__init__(bot_instance)
        self.key_bindings: Dict[str, str] = {}
    
    def on_load(self):
        """Override para inicialização."""
        logger.info(f"GamePlugin {self.name} v{self.version} carregado")
    
    def press_key(self, key: str, duration: float = 0.1):
        """
        Simula pressionar uma tecla.
        
        Args:
            key: Tecla a pressionar
            duration: Duração do press em segundos
        """
        if self.context:
            return self.context.press_key(key, duration=duration)
        raise PluginSecurityError("Contexto não disponível para press_key.")
    
    def press_keys(self, keys: str, delay: float = 0.08):
        """
        Simula sequência de teclas (ex: stratagems).
        
        Args:
            keys: String com teclas (ex: "WASD")
            delay: Delay entre teclas
        """
        if self.context:
            return self.context.press_keys(keys, delay=delay)
        raise PluginSecurityError("Contexto não disponível para press_keys.")
    
    def click_mouse(self, button: str = "left"):
        """Simula clique do mouse."""
        if self.context:
            return self.context.click_mouse(button)
        raise PluginSecurityError("Contexto não disponível para click_mouse.")
    
    def move_mouse(self, x: int, y: int):
        """Move o mouse para posição."""
        if self.context:
            return self.context.move_mouse(x, y)
        raise PluginSecurityError("Contexto não disponível para move_mouse.")


class IntegrationPlugin(BasePlugin):
    """
    Plugin para integrações externas (OBS, Discord, APIs, etc.)
    """
    
    def __init__(self, bot_instance=None):
        super().__init__(bot_instance)
        self.connection = None
    
    def on_load(self):
        """Override para inicialização."""
        logger.info(f"IntegrationPlugin {self.name} v{self.version} carregado")
    
    @abstractmethod
    def connect(self):
        """Conecta ao serviço externo."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Desconecta do serviço."""
        pass
    
    def is_connected(self) -> bool:
        """Verifica se está conectado."""
        return self.connection is not None


class CommandPlugin(BasePlugin):
    """
    Plugin simples para comandos customizados.
    """
    
    def __init__(self, bot_instance=None):
        super().__init__(bot_instance)
        self.cooldowns: Dict[str, float] = {}
    
    def on_load(self):
        """Subclasses devem registrar comandos aqui."""
        pass
    
    def check_cooldown(self, username: str, command: str, seconds: int) -> bool:
        """
        Verifica se usuário pode usar comando (cooldown).
        
        Returns:
            True se pode usar, False se em cooldown
        """
        import time
        key = f"{username}:{command}"
        now = time.time()
        
        if key in self.cooldowns:
            if now - self.cooldowns[key] < seconds:
                return False
        
        self.cooldowns[key] = now
        return True


# ==================== DECORATORS ====================

def command(name: str = None, aliases: List[str] = None):
    """
    Decorator para registrar comandos facilmente.
    
    Compatível com o formato do servidor.
    
    Usage:
        @command("hello", aliases=["hi", "oi"])
        def cmd_hello(self, user, args):
            return f"Olá, {user}!"
    """
    def decorator(func):
        func._is_command = True
        func._command_name = name or func.__name__.replace("cmd_", "")
        func._command_aliases = aliases or []
        return func
    return decorator


def hook(event: str):
    """
    Decorator para registrar hooks de eventos.
    
    Compatível com o formato do servidor.
    
    Usage:
        @hook("stream_start")
        def on_my_stream_start(self):
            self.log_info("Live começou!")
    """
    def decorator(func):
        func._is_hook = True
        func._hook_event = event
        return func
    return decorator
