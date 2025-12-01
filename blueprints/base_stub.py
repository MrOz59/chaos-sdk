"""Minimal stub to allow standalone blueprint compilation without depending on full plugin system.
This keeps the editor independent; generated code can later be swapped to real BasePlugin by changing import.
"""
from typing import Any, Callable

class BasePluginStub:
    name = "BlueprintStandalone"
    version = "0.0.0"
    author = "stub"
    description = "Standalone blueprint stub"
    required_permissions = tuple()

    def __init__(self):
        self.context = None
        self._commands = {}

    def register_command(self, name: str, fn: Callable):
        self._commands[name] = fn

    # Execution helper for local testing
    def run_command(self, name: str, username: str = "tester", args=None):
        args = args or []
        fn = self._commands.get(name)
        if not fn:
            return f"command {name} not found"
        return fn(username, args)
