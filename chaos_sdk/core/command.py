"""
Decoradores e classes para comandos.

Compatível com o sistema de plugins do chaos-server.
"""
from functools import wraps
from typing import Callable, Optional, List


def command(
    name: str,
    aliases: Optional[List[str]] = None,
    cooldown: int = 0,
    mod_only: bool = False,
    subscriber_only: bool = False,
    vip_only: bool = False,
    description: str = "",
    usage: str = "",
    hidden: bool = False,
):
    """
    Decorador para registrar um método como comando.
    
    Compatível com ambos os formatos:
    - Formato do servidor: _is_command, _command_name, _command_aliases
    - Formato novo do SDK: _command_info
    
    Args:
        name: Nome do comando (ex: "dice" ou "!dice")
        aliases: Aliases alternativos
        cooldown: Cooldown em segundos
        mod_only: Requer moderador
        subscriber_only: Requer subscriber
        vip_only: Requer VIP
        description: Descrição do comando
        usage: Formato de uso (ex: "!dice [lados]")
        hidden: Se True, não aparece no !help
    
    Exemplo:
        @command("dice", cooldown=5, description="Rola um dado")
        async def cmd_dice(self, ctx):
            import random
            await ctx.reply(f"🎲 Você rolou {random.randint(1, 6)}!")
    """
    # Normalizar nome (remover ! se tiver para armazenamento interno)
    cmd_name = name.lstrip("!")
    
    def decorator(func: Callable):
        # Formato do servidor (usado pelo plugin_loader.py do servidor)
        func._is_command = True
        func._command_name = cmd_name
        func._command_aliases = [a.lstrip("!") for a in (aliases or [])]
        
        # Formato novo do SDK (mais detalhado)
        func._command_info = {
            "name": cmd_name,
            "aliases": func._command_aliases,
            "cooldown": cooldown,
            "mod_only": mod_only,
            "subscriber_only": subscriber_only,
            "vip_only": vip_only,
            "description": description,
            "usage": usage or f"!{cmd_name}",
            "hidden": hidden,
        }
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Copiar atributos para o wrapper
        wrapper._is_command = True
        wrapper._command_name = cmd_name
        wrapper._command_aliases = func._command_aliases
        wrapper._command_info = func._command_info
        
        return wrapper
    
    return decorator


class Command:
    """
    Representação de um comando registrado.
    
    Usado internamente pelo sistema de plugins.
    """
    
    def __init__(
        self,
        name: str,
        handler: Callable,
        aliases: Optional[List[str]] = None,
        cooldown: int = 0,
        mod_only: bool = False,
        subscriber_only: bool = False,
        vip_only: bool = False,
        description: str = "",
        usage: str = "",
        hidden: bool = False,
    ):
        self.name = name.lstrip("!")
        self.handler = handler
        self.aliases = [a.lstrip("!") for a in (aliases or [])]
        self.cooldown = cooldown
        self.mod_only = mod_only
        self.subscriber_only = subscriber_only
        self.vip_only = vip_only
        self.description = description
        self.usage = usage or f"!{self.name}"
        self.hidden = hidden
        
        # Para tracking de cooldowns por usuário
        self._cooldown_tracker: dict = {}
    
    def check_cooldown(self, username: str) -> bool:
        """
        Verifica se o usuário pode usar o comando (cooldown).
        
        Returns:
            True se pode usar, False se em cooldown
        """
        if self.cooldown <= 0:
            return True
        
        import time
        now = time.time()
        last_use = self._cooldown_tracker.get(username, 0)
        
        if now - last_use < self.cooldown:
            return False
        
        self._cooldown_tracker[username] = now
        return True
    
    def get_remaining_cooldown(self, username: str) -> int:
        """
        Retorna segundos restantes de cooldown.
        
        Returns:
            Segundos restantes ou 0 se não está em cooldown
        """
        if self.cooldown <= 0:
            return 0
        
        import time
        now = time.time()
        last_use = self._cooldown_tracker.get(username, 0)
        remaining = self.cooldown - (now - last_use)
        
        return max(0, int(remaining))
    
    def can_execute(self, is_mod: bool = False, is_sub: bool = False, is_vip: bool = False) -> bool:
        """
        Verifica se o usuário tem permissão para executar o comando.
        
        Args:
            is_mod: Se é moderador
            is_sub: Se é subscriber
            is_vip: Se é VIP
            
        Returns:
            True se pode executar
        """
        if self.mod_only and not is_mod:
            return False
        if self.subscriber_only and not is_sub:
            return False
        if self.vip_only and not is_vip:
            return False
        return True
    
    def to_dict(self) -> dict:
        """Retorna representação em dicionário."""
        return {
            "name": self.name,
            "aliases": self.aliases,
            "cooldown": self.cooldown,
            "mod_only": self.mod_only,
            "subscriber_only": self.subscriber_only,
            "vip_only": self.vip_only,
            "description": self.description,
            "usage": self.usage,
            "hidden": self.hidden,
        }
