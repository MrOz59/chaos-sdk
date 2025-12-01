"""
Hello Plugin (SDK template)

Commands:
- !points          -> prints current points for the caller
- !macro [keys]    -> enqueues a safe macro with given key sequence (default: wasd)

This template uses the secure PluginContext APIs and avoids deprecated direct bot access.
"""
from __future__ import annotations

from chaos_sdk.plugins.base_plugin import BasePlugin


class HelloPlugin(BasePlugin):
    name = "Hello Plugin"
    version = "1.0.0"
    author = "BotLive"
    description = "Template plugin demonstrating safe context APIs"
    required_permissions = ("core:log", "points:read", "points:write", "macro:enqueue")

    def on_load(self):
        self.register_command("points", self.cmd_points)
        self.register_command("macro", self.cmd_macro)
        self.log_info("HelloPlugin loaded (commands: points, macro)")

    def cmd_points(self, username: str, args: list, **kwargs) -> str:
        if not self.context:
            return "context unavailable"
        current = int(self.context.get_points(username))
        return f"{username} has {current} points"

    def cmd_macro(self, username: str, args: list, **kwargs) -> str:
        if not self.context:
            return "context unavailable"
        keys = "".join(args) if args else "wasd"
        if len(keys) > 32:
            keys = keys[:32]
        self.context.macro_run_keys(username=username, keys=keys, delay=0.08, command="demo")
        return f"macro enqueued: {keys}"
