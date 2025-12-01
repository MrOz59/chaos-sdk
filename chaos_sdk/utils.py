"""
Utilitários para desenvolvimento de plugins.

Fornece helpers para tarefas comuns durante o desenvolvimento.
"""
from typing import List, Optional, Dict, Any, Callable
import random
import re
import asyncio
from datetime import datetime, timedelta


class TextUtils:
    """Utilitários para manipulação de texto."""
    
    @staticmethod
    def truncate(text: str, max_length: int = 400, suffix: str = "...") -> str:
        """Trunca texto para o tamanho máximo."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def sanitize(text: str) -> str:
        """Remove caracteres potencialmente perigosos."""
        # Remove caracteres de controle
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        # Remove múltiplos espaços
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def parse_duration(text: str) -> Optional[int]:
        """
        Converte string de duração para segundos.
        
        Exemplos:
            "30s" -> 30
            "5m" -> 300
            "1h" -> 3600
            "1d" -> 86400
        """
        match = re.match(r'^(\d+)\s*(s|m|h|d)?$', text.lower().strip())
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2) or 's'
        
        multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        return value * multipliers[unit]
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """
        Formata segundos como string legível.
        
        Exemplos:
            30 -> "30s"
            90 -> "1m 30s"
            3661 -> "1h 1m 1s"
        """
        if seconds < 60:
            return f"{seconds}s"
        
        parts = []
        if seconds >= 86400:
            days = seconds // 86400
            seconds %= 86400
            parts.append(f"{days}d")
        if seconds >= 3600:
            hours = seconds // 3600
            seconds %= 3600
            parts.append(f"{hours}h")
        if seconds >= 60:
            minutes = seconds // 60
            seconds %= 60
            parts.append(f"{minutes}m")
        if seconds > 0:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    @staticmethod
    def format_number(n: int) -> str:
        """
        Formata número grande de forma legível.
        
        Exemplos:
            1000 -> "1K"
            1500000 -> "1.5M"
        """
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)


class RandomUtils:
    """Utilitários para aleatoriedade."""
    
    @staticmethod
    def chance(percent: float) -> bool:
        """
        Retorna True com X% de chance.
        
        Exemplo:
            if RandomUtils.chance(25):  # 25% de chance
                print("Sorte!")
        """
        return random.random() * 100 < percent
    
    @staticmethod
    def weighted_choice(options: Dict[str, float]) -> str:
        """
        Escolhe uma opção baseado em pesos.
        
        Exemplo:
            result = RandomUtils.weighted_choice({
                "comum": 70,
                "raro": 25,
                "épico": 5
            })
        """
        total = sum(options.values())
        r = random.uniform(0, total)
        cumulative = 0
        for option, weight in options.items():
            cumulative += weight
            if r <= cumulative:
                return option
        return list(options.keys())[-1]
    
    @staticmethod
    def dice(sides: int = 6, count: int = 1) -> List[int]:
        """Rola dados."""
        return [random.randint(1, sides) for _ in range(count)]
    
    @staticmethod
    def shuffle(items: list) -> list:
        """Embaralha lista (retorna cópia)."""
        result = items.copy()
        random.shuffle(result)
        return result
    
    @staticmethod
    def pick(items: list, count: int = 1) -> list:
        """Escolhe N itens aleatórios sem repetição."""
        if count >= len(items):
            return RandomUtils.shuffle(items)
        return random.sample(items, count)


class TimeUtils:
    """Utilitários para tempo."""
    
    @staticmethod
    def now() -> datetime:
        """Retorna datetime atual."""
        return datetime.now()
    
    @staticmethod
    def timestamp() -> int:
        """Retorna timestamp Unix atual."""
        return int(datetime.now().timestamp())
    
    @staticmethod
    def from_timestamp(ts: int) -> datetime:
        """Converte timestamp para datetime."""
        return datetime.fromtimestamp(ts)
    
    @staticmethod
    def ago(seconds: int) -> datetime:
        """Retorna datetime de X segundos atrás."""
        return datetime.now() - timedelta(seconds=seconds)
    
    @staticmethod
    def time_since(dt: datetime) -> str:
        """
        Retorna string legível do tempo passado.
        
        Exemplo:
            "há 5 minutos"
            "há 2 horas"
        """
        delta = datetime.now() - dt
        seconds = int(delta.total_seconds())
        
        if seconds < 60:
            return "agora mesmo"
        if seconds < 3600:
            minutes = seconds // 60
            return f"há {minutes} minuto{'s' if minutes > 1 else ''}"
        if seconds < 86400:
            hours = seconds // 3600
            return f"há {hours} hora{'s' if hours > 1 else ''}"
        
        days = seconds // 86400
        return f"há {days} dia{'s' if days > 1 else ''}"


class CommandParser:
    """Parser para argumentos de comando."""
    
    @staticmethod
    def parse_args(args: List[str], schema: Dict[str, type]) -> Dict[str, Any]:
        """
        Parse argumentos baseado em schema.
        
        Exemplo:
            args = ["100", "dice", "--silent"]
            result = CommandParser.parse_args(args, {
                "amount": int,
                "type": str,
                "silent": bool
            })
            # result = {"amount": 100, "type": "dice", "silent": True}
        """
        result = {}
        positional = []
        flags = set()
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                flag = arg[2:]
                if "=" in flag:
                    key, value = flag.split("=", 1)
                    result[key] = value
                else:
                    flags.add(flag)
            elif arg.startswith("-"):
                flags.add(arg[1:])
            else:
                positional.append(arg)
            i += 1
        
        # Mapear positional para schema
        schema_keys = [k for k in schema.keys() if k not in result and k not in flags]
        for j, key in enumerate(schema_keys):
            if j < len(positional):
                try:
                    result[key] = schema[key](positional[j])
                except (ValueError, TypeError):
                    result[key] = positional[j]
        
        # Mapear flags como bool
        for flag in flags:
            if flag in schema:
                result[flag] = True
        
        return result
    
    @staticmethod
    def get_mention(text: str) -> Optional[str]:
        """Extrai @menção do texto."""
        match = re.search(r'@(\w+)', text)
        return match.group(1) if match else None
    
    @staticmethod
    def get_all_mentions(text: str) -> List[str]:
        """Extrai todas as @menções do texto."""
        return re.findall(r'@(\w+)', text)


class Emoji:
    """Emojis comuns para respostas."""
    
    # Status
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    
    # Ações
    DICE = "🎲"
    MONEY = "💰"
    POINTS = "⭐"
    GIFT = "🎁"
    TROPHY = "🏆"
    MEDAL = "🏅"
    
    # Social
    HEART = "💜"
    FIRE = "🔥"
    PARTY = "🎉"
    COOL = "😎"
    THINK = "🤔"
    
    # Gaming
    GAME = "🎮"
    KEYBOARD = "⌨️"
    MOUSE = "🖱️"
    STREAM = "📺"
    
    @staticmethod
    def progress_bar(current: int, total: int, length: int = 10) -> str:
        """
        Cria barra de progresso com emojis.
        
        Exemplo:
            progress_bar(7, 10) -> "🟩🟩🟩🟩🟩🟩🟩⬜⬜⬜"
        """
        filled = int(length * current / total)
        empty = length - filled
        return "🟩" * filled + "⬜" * empty


class RateLimiter:
    """Rate limiter simples para uso em plugins."""
    
    def __init__(self, calls: int, period: int):
        """
        Args:
            calls: Número máximo de chamadas
            period: Período em segundos
        """
        self.calls = calls
        self.period = period
        self._timestamps: Dict[str, List[float]] = {}
    
    def can_call(self, key: str = "default") -> bool:
        """Verifica se pode fazer uma chamada."""
        import time
        now = time.time()
        
        if key not in self._timestamps:
            self._timestamps[key] = []
        
        # Limpar timestamps antigos
        self._timestamps[key] = [
            t for t in self._timestamps[key] 
            if now - t < self.period
        ]
        
        return len(self._timestamps[key]) < self.calls
    
    def record_call(self, key: str = "default"):
        """Registra uma chamada."""
        import time
        if key not in self._timestamps:
            self._timestamps[key] = []
        self._timestamps[key].append(time.time())
    
    def try_call(self, key: str = "default") -> bool:
        """Tenta fazer uma chamada. Retorna True se permitido."""
        if self.can_call(key):
            self.record_call(key)
            return True
        return False
    
    def remaining(self, key: str = "default") -> int:
        """Retorna quantas chamadas ainda podem ser feitas."""
        import time
        now = time.time()
        
        if key not in self._timestamps:
            return self.calls
        
        recent = [t for t in self._timestamps[key] if now - t < self.period]
        return max(0, self.calls - len(recent))


class Cooldown:
    """Gerenciador de cooldown para comandos."""
    
    def __init__(self, seconds: int, per_user: bool = True):
        self.seconds = seconds
        self.per_user = per_user
        self._last_use: Dict[str, float] = {}
    
    def check(self, user: str = "global") -> tuple[bool, int]:
        """
        Verifica cooldown.
        
        Returns:
            (pode_usar, segundos_restantes)
        """
        import time
        key = user if self.per_user else "global"
        now = time.time()
        
        if key not in self._last_use:
            return True, 0
        
        elapsed = now - self._last_use[key]
        remaining = self.seconds - elapsed
        
        if remaining <= 0:
            return True, 0
        
        return False, int(remaining)
    
    def use(self, user: str = "global"):
        """Registra uso."""
        import time
        key = user if self.per_user else "global"
        self._last_use[key] = time.time()
    
    def try_use(self, user: str = "global") -> tuple[bool, int]:
        """Tenta usar. Retorna (sucesso, segundos_restantes)."""
        can_use, remaining = self.check(user)
        if can_use:
            self.use(user)
        return can_use, remaining
    
    def reset(self, user: str = None):
        """Reseta cooldown."""
        if user:
            key = user if self.per_user else "global"
            self._last_use.pop(key, None)
        else:
            self._last_use.clear()
