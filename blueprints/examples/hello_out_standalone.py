# Standalone mode: using stub base plugin
from blueprints.base_stub import BasePluginStub as BasePlugin


class BlueprintPlugin(BasePlugin):

    name = "Hello Blueprint"
    version = "1.0.0"
    author = "BotLive"
    description = "Greets the user and enqueues a demo macro"
    required_permissions = ('core:log', 'chat:send', 'macro:enqueue', 'points:read', 'points:write')

    def on_load(self):
        self.register_command("hello", self.cmd_hello)
        self.register_command("buff", self.cmd_buff)

    def cmd_hello(self, username: str, args: list, **kwargs) -> str:
        responses = []
        ctx = self.context
        if not ctx:
            return 'context unavailable'
        vars = {}
        
        def _rv(s):
            """resolve value: {username} or {var:name} or literal"""
            try:
                if isinstance(s, str):
                    if s == '{username}':
                        return username
                    if s.startswith('{var:') and s.endswith('}'):
                        return vars.get(s[5:-1], '')
                return s
            except Exception:
                return s
        
        def _rint(x):
            try:
                return int(x)
            except Exception:
                return 0
        
        # Execute blueprint steps
        responses.append(f"Hello {username}!")
        ctx.macro_run_keys(username=username, keys="wasd", delay=0.08, command="hello")
        return ' '.join([str(x) for x in responses if x])

    def cmd_buff(self, username: str, args: list, **kwargs) -> str:
        responses = []
        ctx = self.context
        if not ctx:
            return 'context unavailable'
        # Placeholder implementation
        return f"Buff activated!"
