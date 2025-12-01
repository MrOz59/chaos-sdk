"""
Contexto de execução de comandos.

Compatível com o sistema de plugins do chaos-server.
"""
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, field


@dataclass
class CommandContext:
    """
    Contexto passado para handlers de comando.
    
    Contém informações sobre o usuário, mensagem e canal.
    Fornece métodos para responder e interagir com o chat.
    """
    
    # Informações do usuário
    user_id: str = ""
    username: str = ""
    display_name: str = ""
    
    # Mensagem e argumentos
    message: str = ""
    args: List[str] = field(default_factory=list)
    
    # Permissões do usuário
    is_mod: bool = False
    is_subscriber: bool = False
    is_vip: bool = False
    is_broadcaster: bool = False
    
    # Informações do canal
    channel: str = ""
    platform: str = "twitch"  # twitch, kick
    
    # Dados brutos (para integrações avançadas)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # Referência ao runtime (injetada pelo loader)
    _runtime: Any = None
    
    async def reply(self, message: str) -> bool:
        """
        Envia resposta no chat (menciona o usuário).
        
        Args:
            message: Mensagem a enviar
            
        Returns:
            True se enviou com sucesso
        """
        if self._runtime:
            return await self._runtime.send_chat(f"@{self.username} {message}", self.platform)
        return False
    
    async def send(self, message: str) -> bool:
        """
        Envia mensagem no chat (sem mencionar).
        
        Args:
            message: Mensagem a enviar
            
        Returns:
            True se enviou com sucesso
        """
        if self._runtime:
            return await self._runtime.send_chat(message, self.platform)
        return False
    
    async def whisper(self, message: str) -> bool:
        """
        Envia whisper/DM para o usuário.
        
        Args:
            message: Mensagem a enviar
            
        Returns:
            True se enviou com sucesso
        """
        if self._runtime and hasattr(self._runtime, 'send_whisper'):
            return await self._runtime.send_whisper(self.username, message)
        return False
    
    # ==================== Points API ====================
    
    def get_points(self, username: str = None) -> int:
        """
        Obtém pontos de um usuário.
        
        Args:
            username: Nome do usuário (default: próprio usuário)
            
        Returns:
            Quantidade de pontos
        """
        target = username or self.username
        if self._runtime:
            return self._runtime.get_points(target)
        return 0
    
    def add_points(self, amount: int, username: str = None, reason: str = '') -> bool:
        """
        Adiciona pontos a um usuário.
        
        Args:
            amount: Quantidade de pontos
            username: Nome do usuário (default: próprio usuário)
            reason: Motivo da adição
            
        Returns:
            True se adicionou com sucesso
        """
        target = username or self.username
        if self._runtime:
            return self._runtime.add_points(target, amount, reason)
        return False
    
    def remove_points(self, amount: int, username: str = None, reason: str = '') -> bool:
        """
        Remove pontos de um usuário.
        
        Args:
            amount: Quantidade de pontos
            username: Nome do usuário (default: próprio usuário)
            reason: Motivo da remoção
            
        Returns:
            True se removeu com sucesso
        """
        target = username or self.username
        if self._runtime:
            return self._runtime.remove_points(target, amount, reason)
        return False
    
    # ==================== Macro API ====================
    
    async def execute_macro(self, macro_name: str, **kwargs) -> bool:
        """
        Executa uma macro no cliente.
        
        Args:
            macro_name: Nome da macro
            **kwargs: Parâmetros da macro
            
        Returns:
            True se executou com sucesso
        """
        if self._runtime and hasattr(self._runtime, 'execute_macro'):
            return await self._runtime.execute_macro(macro_name, **kwargs)
        return False
    
    async def press_key(self, key: str, duration: float = 0.1) -> bool:
        """
        Simula pressionar uma tecla.
        
        Args:
            key: Tecla a pressionar
            duration: Duração em segundos
            
        Returns:
            True se executou com sucesso
        """
        if self._runtime and hasattr(self._runtime, 'press_key'):
            return self._runtime.press_key(key, duration)
        return False
    
    async def press_keys(self, keys: str, delay: float = 0.08) -> bool:
        """
        Simula sequência de teclas.
        
        Args:
            keys: Teclas a pressionar (ex: "WASD")
            delay: Delay entre teclas
            
        Returns:
            True se executou com sucesso
        """
        if self._runtime and hasattr(self._runtime, 'press_keys'):
            return self._runtime.press_keys(keys, delay)
        return False


@dataclass
class EventContext:
    """
    Contexto passado para handlers de eventos.
    """
    
    event_type: str = ""
    user: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    platform: str = "twitch"
    
    # Referência ao runtime
    _runtime: Any = None
    
    async def reply(self, message: str) -> bool:
        """Envia resposta no chat."""
        if self._runtime:
            return await self._runtime.send_chat(message, self.platform)
        return False
    
    @property
    def username(self) -> str:
        """Alias para user."""
        return self.user
    
    @property
    def message(self) -> str:
        """Obtém mensagem do evento (se houver)."""
        return self.data.get("message", "")
