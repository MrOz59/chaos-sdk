"""
Chaos SDK Core - Classes base para plugins.

Compatível com o sistema de plugins do chaos-server.
"""
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
from chaos_sdk.core.command import Command, command as cmd_decorator
from chaos_sdk.core.events import Event, Events, on_event, hook as event_hook

__all__ = [
    # Plugin classes
    "Plugin",
    "BasePlugin",
    "GamePlugin",
    "IntegrationPlugin",
    "CommandPlugin",
    
    # Decorators
    "command",
    "hook",
    "cmd_decorator",
    "on_event",
    "event_hook",
    
    # Permissions
    "ALLOWED_PERMISSIONS",
    "DEFAULT_PERMISSIONS",
    "PluginSecurityError",
    
    # Command & Event classes
    "Command",
    "Event",
    "Events",
]