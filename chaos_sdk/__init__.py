"""
Chaos SDK - Kit de Desenvolvimento para Plugins Chaos Factory
=============================================================

SDK compatível com o sistema de plugins do chaos-server.

Exemplo de uso:

    from chaos_sdk import Plugin, command

    class MeuPlugin(Plugin):
        name = "MeuPlugin"
        version = "1.0.0"
        author = "SeuNome"
        description = "Meu primeiro plugin"
        required_permissions = ["chat:send"]
        
        def on_load(self):
            self.register_command("ola", self.cmd_ola)
        
        def cmd_ola(self, username, args, **kwargs):
            return f"Olá, {username}!"

Para integração com mods de jogos:

    from chaos_sdk.mods import ModBridgePlugin, mod_event

    class MeuJogoPlugin(ModBridgePlugin):
        game_id = "meu_jogo"
        
        @mod_event("player_died")
        def on_player_died(self, mod, event):
            return f"{event.player} morreu!"

Documentação: https://chaos.mroz.dev.br/docs/sdk
"""
__version__ = "1.3.0"

# Core - Classes base
from chaos_sdk.core.plugin import (
    Plugin,
    BasePlugin,
    GamePlugin,
    IntegrationPlugin,
    CommandPlugin,
    command,
    hook,
    ALLOWED_PERMISSIONS,
    DEFAULT_PERMISSIONS,
    PluginSecurityError,
)

# Alias para retrocompatibilidade
ChaosPlugin = Plugin

# Core - Comandos e Eventos
from chaos_sdk.core.command import Command, command as cmd_decorator
from chaos_sdk.core.events import Event, Events, on_event, hook as event_hook

# Models - Contextos
from chaos_sdk.models.context import CommandContext, EventContext
from chaos_sdk.models.user import User, Viewer

# Importar decoradores avançados
from chaos_sdk.decorators import (
    cooldown,
    require_mod,
    require_sub,
    require_vip,
    require_points,
    cost_points,
    periodic,
    rate_limit,
)

# Importar utilitários
from chaos_sdk.utils import (
    TextUtils,
    RandomUtils,
    TimeUtils,
    CommandParser,
    Emoji,
    RateLimiter,
    Cooldown,
)

# Importar sistema de config
from chaos_sdk.config import (
    PluginConfig,
    ConfigField,
    string_field,
    int_field,
    float_field,
    bool_field,
    list_field,
    choice_field,
    secret_field,
)

# Blueprint System (visual editor)
from chaos_sdk.blueprints import (
    compile_blueprint,
    compile_blueprint_v2,
    compile_blueprint_secure,
    validate_blueprint,
    CompilationResult,
    CompilerMessage,
    Severity,
)

# Mod Integration System
from chaos_sdk.mods import (
    ModBridgePlugin,
    ModConnection,
    ModMessage,
    ModEvent,
    ModCommand,
    ModResponse,
    mod_event,
    mod_command,
    on_mod_connect,
    on_mod_disconnect,
    ModRegistry,
)

__all__ = [
    # Version
    "__version__",
    
    # Core - Plugin Classes
    "Plugin",
    "ChaosPlugin",  # Alias
    "BasePlugin",
    "GamePlugin",
    "IntegrationPlugin",
    "CommandPlugin",
    
    # Core - Decorators (formato servidor)
    "command",
    "hook",
    
    # Core - Permissions
    "ALLOWED_PERMISSIONS",
    "DEFAULT_PERMISSIONS",
    "PluginSecurityError",
    
    # Core - Commands
    "Command",
    "cmd_decorator",
    
    # Core - Events
    "Event",
    "Events",
    "on_event",
    "event_hook",
    
    # Models
    "CommandContext",
    "EventContext",
    "User",
    "Viewer",
    
    # Decoradores avançados
    "cooldown",
    "require_mod",
    "require_sub",
    "require_vip",
    "require_points",
    "cost_points",
    "periodic",
    "rate_limit",
    
    # Utils
    "TextUtils",
    "RandomUtils",
    "TimeUtils",
    "CommandParser",
    "Emoji",
    "RateLimiter",
    "Cooldown",
    
    # Config
    "PluginConfig",
    "ConfigField",
    "string_field",
    "int_field",
    "float_field",
    "bool_field",
    "list_field",
    "choice_field",
    "secret_field",
    
    # Blueprints
    "compile_blueprint",
    "compile_blueprint_v2",
    "compile_blueprint_secure",
    "validate_blueprint",
    "CompilationResult",
    "CompilerMessage",
    "Severity",
    
    # Mod Integration
    "ModBridgePlugin",
    "ModConnection",
    "ModMessage",
    "ModEvent",
    "ModCommand",
    "ModResponse",
    "mod_event",
    "mod_command",
    "on_mod_connect",
    "on_mod_disconnect",
    "ModRegistry",
]
