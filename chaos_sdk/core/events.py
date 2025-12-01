"""
Sistema de eventos para plugins.

Compatível com o sistema de plugins do chaos-server.
"""
from functools import wraps
from typing import Callable, Any, Dict, Optional
from dataclasses import dataclass, field


def on_event(event_name: str):
    """
    Decorador para registrar handler de evento.
    
    Compatível com ambos os formatos:
    - Formato do servidor: _is_hook, _hook_event
    - Formato novo do SDK: _event_info
    
    Eventos disponíveis:
        - "message" / "on_message": Mensagem no chat
        - "follow": Novo seguidor
        - "subscribe": Nova inscrição
        - "bits": Doação de bits
        - "raid": Raid recebido
        - "stream_start" / "on_stream_start": Live iniciada
        - "stream_end" / "on_stream_end": Live encerrada
        - "viewer_join" / "on_viewer_join": Viewer entrou no chat
        - "viewer_leave" / "on_viewer_leave": Viewer saiu do chat
        - "points_earned" / "on_points_earned": Usuário ganhou pontos
        - "points_spent" / "on_points_spent": Usuário gastou pontos
    
    Exemplo:
        @on_event("follow")
        async def on_follow(self, event):
            await event.reply(f"Obrigado pelo follow, {event.user}!")
        
        @on_event("stream_start")
        async def on_live(self):
            self.log_info("Live começou!")
    """
    # Normalizar nome do evento (remover prefixo on_ se existir)
    normalized_event = event_name
    if event_name.startswith("on_"):
        normalized_event = event_name[3:]  # Remove "on_"
    
    def decorator(func: Callable):
        # Formato do servidor
        func._is_hook = True
        func._hook_event = normalized_event
        
        # Formato novo do SDK
        func._event_info = {
            "event": normalized_event,
            "original_name": event_name,
        }
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Copiar atributos
        wrapper._is_hook = True
        wrapper._hook_event = normalized_event
        wrapper._event_info = func._event_info
        
        return wrapper
    
    return decorator


# Alias para compatibilidade
hook = on_event


@dataclass
class Event:
    """
    Representa um evento recebido.
    
    Contém informações sobre o tipo de evento e dados associados.
    """
    
    type: str = ""
    user: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    platform: str = "twitch"
    
    # Referência ao runtime (injetada pelo loader)
    _runtime: Any = None
    
    async def reply(self, message: str) -> bool:
        """
        Envia resposta no chat.
        
        Args:
            message: Mensagem a enviar
            
        Returns:
            True se enviou com sucesso
        """
        if self._runtime:
            return await self._runtime.send_chat(message, self.platform)
        return False
    
    @property
    def username(self) -> str:
        """Alias para user."""
        return self.user
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        """
        Cria Event a partir de dicionário.
        
        Args:
            data: Dicionário com dados do evento
            
        Returns:
            Instância de Event
        """
        return cls(
            type=data.get("type", ""),
            user=data.get("user", data.get("username", "")),
            message=data.get("message", ""),
            data=data,
            platform=data.get("platform", "twitch"),
        )


# Eventos pré-definidos para conveniência
class Events:
    """Constantes de nomes de eventos."""
    
    MESSAGE = "message"
    FOLLOW = "follow"
    SUBSCRIBE = "subscribe"
    BITS = "bits"
    RAID = "raid"
    STREAM_START = "stream_start"
    STREAM_END = "stream_end"
    VIEWER_JOIN = "viewer_join"
    VIEWER_LEAVE = "viewer_leave"
    POINTS_EARNED = "points_earned"
    POINTS_SPENT = "points_spent"
