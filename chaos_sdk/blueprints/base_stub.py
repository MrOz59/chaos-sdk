"""
Base Plugin Stub for Standalone Blueprint Plugins

This stub provides a minimal BasePlugin class that can be used when
compiling blueprints in standalone mode (without the full server).

For full functionality, use with the chaos-server package.
"""
from typing import Any, Dict, List, Optional, Callable


class BasePluginStub:
    """
    Minimal BasePlugin stub for standalone blueprint plugins.
    
    Provides command registration and basic lifecycle methods.
    For full functionality, use with chaos-server.
    """
    
    name: str = "StubPlugin"
    version: str = "1.0.0"
    author: str = "Unknown"
    description: str = ""
    required_permissions: tuple = ()
    
    def __init__(self):
        self._commands: Dict[str, Callable] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self.context = StubContext()
        self.logger = StubLogger(self.name)
    
    def register_command(self, name: str, handler: Callable) -> None:
        """Register a command handler."""
        self._commands[name] = handler
    
    def register_hook(self, event: str, handler: Callable) -> None:
        """Register an event hook."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)
    
    def on_load(self) -> None:
        """Called when plugin is loaded. Override to register commands."""
        pass
    
    def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        pass
    
    def execute_command(self, cmd: str, username: str, args: List[str], **kwargs) -> str:
        """Execute a registered command."""
        handler = self._commands.get(cmd)
        if handler:
            return handler(username, args, **kwargs)
        return f"Unknown command: {cmd}"
    
    def emit_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Emit an event to all registered hooks."""
        results = []
        for handler in self._hooks.get(event, []):
            try:
                result = handler(*args, **kwargs)
                if result:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Hook error: {e}")
        return results


class StubContext:
    """
    Stub context providing no-op implementations of all context methods.
    
    For testing/standalone use only.
    """
    
    def get_points(self, username: str) -> int:
        """Get user points (stub: returns 0)."""
        return 0
    
    def add_points(self, username: str, amount: int, reason: str = "") -> int:
        """Add points to user (stub: no-op)."""
        print(f"[STUB] add_points({username}, {amount}, {reason})")
        return amount
    
    def remove_points(self, username: str, amount: int, reason: str = "") -> int:
        """Remove points from user (stub: no-op)."""
        print(f"[STUB] remove_points({username}, {amount}, {reason})")
        return 0
    
    async def send_chat(self, message: str, platform: str = "twitch") -> None:
        """Send chat message (stub: prints to console)."""
        print(f"[CHAT:{platform}] {message}")
    
    def macro_run_keys(self, username: str, keys: str, delay: float = 0.08, command: str = "") -> bool:
        """Run keyboard macro (stub: no-op)."""
        print(f"[STUB] macro_run_keys({keys}, delay={delay})")
        return True
    
    def audio_tts(self, text: str, lang: str = "pt-br") -> bool:
        """Play TTS (stub: no-op)."""
        print(f"[STUB] audio_tts({text}, lang={lang})")
        return True
    
    def audio_play(self, name: str) -> bool:
        """Play sound (stub: no-op)."""
        print(f"[STUB] audio_play({name})")
        return True
    
    def audio_stop(self) -> bool:
        """Stop audio (stub: no-op)."""
        print("[STUB] audio_stop()")
        return True
    
    def audio_clear_queue(self) -> bool:
        """Clear audio queue (stub: no-op)."""
        print("[STUB] audio_clear_queue()")
        return True
    
    def start_poll(self, title: str, options: List[str], creator: str, 
                   duration: int = 5, allow_change: bool = True, 
                   require_points: int = 0) -> Dict[str, Any]:
        """Start a poll (stub: returns mock data)."""
        print(f"[STUB] start_poll({title}, {options})")
        return {"poll": {"id": "stub_poll_1"}}
    
    def get_leaderboard(self, limit: int = 10, category: str = "points") -> List[tuple]:
        """Get leaderboard (stub: returns empty)."""
        return []
    
    def minigames_command(self, command: str, username: str, args: List[str]) -> str:
        """Run minigame command (stub: no-op)."""
        print(f"[STUB] minigames_command({command}, {username}, {args})")
        return ""


class StubLogger:
    """Simple logger for standalone plugins."""
    
    def __init__(self, name: str):
        self.name = name
    
    def _log(self, level: str, msg: str) -> None:
        print(f"[{level}] [{self.name}] {msg}")
    
    def debug(self, msg: str) -> None:
        self._log("DEBUG", msg)
    
    def info(self, msg: str) -> None:
        self._log("INFO", msg)
    
    def warning(self, msg: str) -> None:
        self._log("WARN", msg)
    
    def error(self, msg: str) -> None:
        self._log("ERROR", msg)


# For backwards compatibility
BasePlugin = BasePluginStub
