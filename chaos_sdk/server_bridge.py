"""
Server Bridge - Conexão entre SDK e o servidor Chaos.

Este módulo fornece uma camada de abstração entre o SDK e o servidor.
Quando o SDK é usado junto com o servidor, o servidor registra suas
implementações reais. Quando usado standalone, usa stubs/mocks.

Uso pelo servidor:
    from chaos_sdk.server_bridge import register_bot_manager
    register_bot_manager(my_bot_manager_instance)

Uso pelo SDK:
    from chaos_sdk.server_bridge import get_bot_manager
    manager = get_bot_manager()  # Retorna instância real ou stub
"""

from typing import Optional, Any, Callable
import logging

logger = logging.getLogger(__name__)

# === Registros globais ===
_bot_manager = None
_macro_queue = None
_minigames_commands = None


# === Bot Manager ===
class BotManagerStub:
    """Stub do BotManager para uso standalone"""
    
    def get_tenant_bot(self, tenant_id: str, platform: str):
        logger.warning(f"BotManagerStub: get_tenant_bot({tenant_id}, {platform}) - servidor não conectado")
        return None
    
    def list_tenants(self):
        return []


def register_bot_manager(manager):
    """Registra o BotManager real do servidor"""
    global _bot_manager
    _bot_manager = manager
    logger.info("BotManager registrado no server_bridge")


def get_bot_manager():
    """Retorna o BotManager (real ou stub)"""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = BotManagerStub()
    return _bot_manager


# === Macro Queue ===
class MacroQueueStub:
    """Stub do MacroQueue para uso standalone"""
    
    def enqueue(self, macro: Any, priority: int = 0):
        logger.warning(f"MacroQueueStub: enqueue() - servidor não conectado")
        return False
    
    def get_queue_size(self):
        return 0


def register_macro_queue(queue):
    """Registra o MacroQueue real do servidor"""
    global _macro_queue
    _macro_queue = queue
    logger.info("MacroQueue registrado no server_bridge")


def get_macro_queue():
    """Retorna o MacroQueue (real ou stub)"""
    global _macro_queue
    if _macro_queue is None:
        _macro_queue = MacroQueueStub()
    return _macro_queue


# === Minigames Commands ===
class MinigamesCommandsStub:
    """Stub para MinigamesCommands"""
    
    def get_active_minigame(self):
        return None
    
    def list_minigames(self):
        return []


def register_minigames_commands(commands):
    """Registra MinigamesCommands real do servidor"""
    global _minigames_commands
    _minigames_commands = commands
    logger.info("MinigamesCommands registrado no server_bridge")


# Alias para compatibilidade
MinigamesCommands = MinigamesCommandsStub


def get_minigames_commands():
    """Retorna MinigamesCommands (real ou stub)"""
    global _minigames_commands
    if _minigames_commands is None:
        _minigames_commands = MinigamesCommandsStub()
    return _minigames_commands


# === Utilitário para verificar conexão ===
def is_server_connected() -> bool:
    """Verifica se o SDK está conectado ao servidor"""
    return not isinstance(_bot_manager, BotManagerStub)


def reset_all():
    """Reset todos os registros (útil para testes)"""
    global _bot_manager, _macro_queue, _minigames_commands
    _bot_manager = None
    _macro_queue = None
    _minigames_commands = None
