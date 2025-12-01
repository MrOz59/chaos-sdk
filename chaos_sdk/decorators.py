"""
Decoradores avançados para desenvolvimento de plugins.

Exemplo de uso:

    from chaos_sdk import Plugin
    from chaos_sdk.decorators import command, cooldown, require_mod, require_sub, on_event

    class MeuPlugin(Plugin):
        @command("!dice", description="Rola um dado")
        @cooldown(seconds=5)
        async def dice(self, ctx):
            import random
            result = random.randint(1, 6)
            await ctx.reply(f"🎲 {ctx.username} rolou {result}!")

        @command("!ban")
        @require_mod
        async def ban(self, ctx):
            await ctx.reply("Comando apenas para mods!")

        @on_event("follow")
        async def on_follow(self, event):
            await event.reply(f"Obrigado pelo follow, {event.user}! 💜")
"""
from functools import wraps
from typing import Callable, Optional, List, Union
import time
import asyncio

# Armazenamento de cooldowns por comando/usuário
_cooldowns: dict = {}


def command(
    name: str,
    aliases: Optional[List[str]] = None,
    description: str = "",
    usage: str = "",
    examples: Optional[List[str]] = None,
    hidden: bool = False,
):
    """
    Decorador principal para registrar comandos.
    
    Args:
        name: Nome do comando (ex: "!dice" ou "dice")
        aliases: Lista de aliases (ex: ["d", "dado"])
        description: Descrição do comando para help
        usage: Formato de uso (ex: "!dice [lados]")
        examples: Exemplos de uso
        hidden: Se True, não aparece no !help
    
    Exemplo:
        @command("!dice", aliases=["d"], description="Rola um dado")
        async def dice(self, ctx):
            ...
    """
    # Normalizar nome (adicionar ! se não tiver)
    cmd_name = name if name.startswith("!") else f"!{name}"
    
    def decorator(func: Callable):
        func._command_info = {
            "name": cmd_name,
            "aliases": [f"!{a}" if not a.startswith("!") else a for a in (aliases or [])],
            "description": description,
            "usage": usage or cmd_name,
            "examples": examples or [],
            "hidden": hidden,
            "cooldown": 0,
            "mod_only": False,
            "sub_only": False,
            "vip_only": False,
            "min_points": 0,
        }
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        wrapper._command_info = func._command_info
        return wrapper
    
    return decorator


def cooldown(seconds: int = 5, per_user: bool = True, message: str = ""):
    """
    Adiciona cooldown a um comando.
    
    Args:
        seconds: Tempo de cooldown em segundos
        per_user: Se True, cooldown é por usuário. Se False, é global.
        message: Mensagem customizada quando em cooldown
    
    Exemplo:
        @command("!dice")
        @cooldown(seconds=10, per_user=True)
        async def dice(self, ctx):
            ...
    """
    def decorator(func: Callable):
        # Atualizar info do comando se existir
        if hasattr(func, '_command_info'):
            func._command_info['cooldown'] = seconds
            func._command_info['cooldown_per_user'] = per_user
            func._command_info['cooldown_message'] = message
        
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            cmd_name = getattr(func, '_command_info', {}).get('name', func.__name__)
            
            # Gerar chave de cooldown
            if per_user:
                key = f"{cmd_name}:{ctx.username}"
            else:
                key = cmd_name
            
            # Verificar cooldown
            now = time.time()
            if key in _cooldowns:
                elapsed = now - _cooldowns[key]
                remaining = seconds - elapsed
                if remaining > 0:
                    if message:
                        await ctx.reply(message.format(remaining=int(remaining)))
                    else:
                        await ctx.reply(f"⏳ Aguarde {int(remaining)}s para usar este comando novamente.")
                    return None
            
            # Registrar uso
            _cooldowns[key] = now
            
            return await func(self, ctx, *args, **kwargs)
        
        wrapper._command_info = getattr(func, '_command_info', {})
        return wrapper
    
    return decorator


def require_mod(func: Callable = None, *, message: str = ""):
    """
    Restringe comando apenas para moderadores.
    
    Exemplo:
        @command("!timeout")
        @require_mod
        async def timeout(self, ctx):
            ...
    """
    def decorator(f: Callable):
        if hasattr(f, '_command_info'):
            f._command_info['mod_only'] = True
        
        @wraps(f)
        async def wrapper(self, ctx, *args, **kwargs):
            if not ctx.is_mod:
                msg = message or "❌ Este comando é apenas para moderadores."
                await ctx.reply(msg)
                return None
            return await f(self, ctx, *args, **kwargs)
        
        wrapper._command_info = getattr(f, '_command_info', {})
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def require_sub(func: Callable = None, *, message: str = ""):
    """
    Restringe comando apenas para subscribers.
    
    Exemplo:
        @command("!vip")
        @require_sub
        async def vip_command(self, ctx):
            ...
    """
    def decorator(f: Callable):
        if hasattr(f, '_command_info'):
            f._command_info['sub_only'] = True
        
        @wraps(f)
        async def wrapper(self, ctx, *args, **kwargs):
            if not ctx.is_subscriber:
                msg = message or "❌ Este comando é apenas para subscribers."
                await ctx.reply(msg)
                return None
            return await f(self, ctx, *args, **kwargs)
        
        wrapper._command_info = getattr(f, '_command_info', {})
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def require_vip(func: Callable = None, *, message: str = ""):
    """
    Restringe comando apenas para VIPs.
    """
    def decorator(f: Callable):
        if hasattr(f, '_command_info'):
            f._command_info['vip_only'] = True
        
        @wraps(f)
        async def wrapper(self, ctx, *args, **kwargs):
            if not ctx.is_vip:
                msg = message or "❌ Este comando é apenas para VIPs."
                await ctx.reply(msg)
                return None
            return await f(self, ctx, *args, **kwargs)
        
        wrapper._command_info = getattr(f, '_command_info', {})
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def require_points(amount: int, message: str = ""):
    """
    Requer que o usuário tenha X pontos para usar o comando.
    NÃO deduz os pontos automaticamente.
    
    Args:
        amount: Quantidade mínima de pontos
        message: Mensagem customizada
    
    Exemplo:
        @command("!jackpot")
        @require_points(1000)
        async def jackpot(self, ctx):
            ...
    """
    def decorator(func: Callable):
        if hasattr(func, '_command_info'):
            func._command_info['min_points'] = amount
        
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            if hasattr(self, 'context') and self.context:
                user_points = self.context.get_points(ctx.username)
                if user_points < amount:
                    msg = message or f"❌ Você precisa de {amount} pontos. Você tem {user_points}."
                    await ctx.reply(msg)
                    return None
            return await func(self, ctx, *args, **kwargs)
        
        wrapper._command_info = getattr(func, '_command_info', {})
        return wrapper
    
    return decorator


def cost_points(amount: int, message: str = ""):
    """
    Deduz pontos automaticamente ao usar o comando.
    Se não tiver pontos suficientes, bloqueia.
    
    Args:
        amount: Quantidade de pontos a deduzir
        message: Mensagem customizada quando não tem pontos
    
    Exemplo:
        @command("!spin")
        @cost_points(100)
        async def spin(self, ctx):
            # 100 pontos já foram deduzidos automaticamente
            ...
    """
    def decorator(func: Callable):
        if hasattr(func, '_command_info'):
            func._command_info['cost'] = amount
        
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            if hasattr(self, 'context') and self.context:
                user_points = self.context.get_points(ctx.username)
                if user_points < amount:
                    msg = message or f"❌ Você precisa de {amount} pontos. Você tem {user_points}."
                    await ctx.reply(msg)
                    return None
                
                # Deduzir pontos
                self.context.remove_points(ctx.username, amount, f"Comando {func.__name__}")
            
            return await func(self, ctx, *args, **kwargs)
        
        wrapper._command_info = getattr(func, '_command_info', {})
        return wrapper
    
    return decorator


def on_event(event_name: str):
    """
    Registra handler para um evento.
    
    Eventos disponíveis:
        - "message": Toda mensagem do chat
        - "follow": Novo seguidor
        - "subscribe": Nova inscrição
        - "bits": Doação de bits
        - "raid": Raid recebido
        - "stream_start": Live iniciada
        - "stream_end": Live encerrada
        - "viewer_join": Viewer entrou no chat
        - "viewer_leave": Viewer saiu do chat
    
    Exemplo:
        @on_event("follow")
        async def on_follow(self, event):
            await event.reply(f"Bem-vindo {event.user}!")
    """
    def decorator(func: Callable):
        func._event_info = {
            "event": event_name,
        }
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        wrapper._event_info = func._event_info
        return wrapper
    
    return decorator


def periodic(interval_seconds: int):
    """
    Executa uma função periodicamente.
    
    Args:
        interval_seconds: Intervalo em segundos
    
    Exemplo:
        @periodic(60)
        async def check_live_status(self):
            # Executado a cada 60 segundos
            ...
    """
    def decorator(func: Callable):
        func._periodic_info = {
            "interval": interval_seconds,
        }
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        wrapper._periodic_info = func._periodic_info
        return wrapper
    
    return decorator


def rate_limit(calls: int = 5, period: int = 60):
    """
    Limita número de chamadas por período.
    
    Args:
        calls: Número máximo de chamadas
        period: Período em segundos
    
    Exemplo:
        @command("!api")
        @rate_limit(calls=10, period=60)  # 10 chamadas por minuto
        async def api_command(self, ctx):
            ...
    """
    _call_times: dict = {}
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            cmd_name = getattr(func, '_command_info', {}).get('name', func.__name__)
            key = f"{cmd_name}:{ctx.username}"
            now = time.time()
            
            # Limpar chamadas antigas
            if key not in _call_times:
                _call_times[key] = []
            _call_times[key] = [t for t in _call_times[key] if now - t < period]
            
            # Verificar limite
            if len(_call_times[key]) >= calls:
                await ctx.reply(f"⚠️ Limite de uso atingido. Aguarde um momento.")
                return None
            
            _call_times[key].append(now)
            return await func(self, ctx, *args, **kwargs)
        
        wrapper._command_info = getattr(func, '_command_info', {})
        return wrapper
    
    return decorator
