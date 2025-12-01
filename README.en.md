# BotLive Plugin SDK

Develop, run, and test plugins locally with a lightweight workflow that mirrors the production sandbox and API.

This SDK pairs with the hardened Plugin Sandbox: JSON IPC, strict method allowlist, hidden tenancy, dangerous builtins disabled, import allowlist, resource limits, and network disabled by default.

## What you can do here

Blueprints (no-code, experimental):
- English: `sdk/blueprints/README.en.md`
- Português (Brasil): `sdk/blueprints/README.pt-BR.md`
- Keep your code compatible with production: same BasePlugin, permissions, and PluginContext methods

## Requirements
- Python 3.10+
- A clone of this repository (SDK runs in-repo)

## Quick start

1) Create a plugin file (subclass BasePlugin) or use the template in `sdk/examples/hello_plugin.py`.

2) Run the SDK runner (verbose recommended the first time):

```
python -m sdk.runner /absolute/path/to/your_plugin.py --tenant local --verbose
```

3) Use the REPL:
- `!<command> [args...]` executes your plugin command
- `> your message` broadcasts a chat-like message to `on_message`
- `:help` lists helper commands for points and polls
- `exit` quits

## Plugin skeleton (compatible with secure API)

```python
from src.shared.plugins.base_plugin import BasePlugin

class MyFirstPlugin(BasePlugin):
    name = "My First Plugin"
    version = "1.0.0"
    author = "You"
    description = "Example plugin using the safe API"
    required_permissions = ("core:log", "points:read", "points:write", "macro:enqueue")

    def on_load(self):
        self.register_command("points", self.cmd_points)
        self.register_command("macro", self.cmd_macro)

    def cmd_points(self, username: str, args: list, **kwargs) -> str:
        # Read/update points via secure context
        if self.context:
            current = int(self.context.get_points(username))
            return f"{username} has {current} points"
        return "context unavailable"

    def cmd_macro(self, username: str, args: list, **kwargs) -> str:
        # Enqueue a safe macro (keys only, no mouse)
        if self.context:
            self.context.macro_run_keys(username=username, keys="wasd", delay=0.08, command="demo")
        return "macro enqueued"
```

Tip: Avoid direct access to the bot instance. Use `self.context` methods instead.

## Permissions model

Declare only what you need in `required_permissions`:
- core:log
- chat:send
- points:read, points:write
- voting:read, voting:vote, voting:manage
- audio:play, audio:tts, audio:control
- minigames:play
- leaderboard:read
- macro:enqueue

Requests for unknown permissions are rejected at load time.

## Safe PluginContext methods (host-side allowlist)

- Chat: `send_chat(message, platform="twitch")` (note: see limitations in SDK below)
- Points: `get_points`, `add_points`, `remove_points`
- Voting: `start_poll`, `vote`, `get_active_poll`, `end_poll`, `get_poll_results`
- Audio: `audio_play`, `audio_tts`, `audio_stop`, `audio_clear_queue`, `audio_queue_size`
- Leaderboard: `get_leaderboard`
- Minigames: `minigames_command`
- Macros: `macro_run_keys(username, keys, delay=0.08, command=None, platform='twitch')`

What you cannot do:
- No access to tenant_id or sensitive config
- No low-level keyboard/mouse APIs exposed to plugins
- No read/modify of macros.json or external macro queues

## Sandbox & security (mirrors production)

- IPC: JSON line protocol, size limits (~64KB) and 2s timeouts
- No new privileges (Linux), process resource limits (CPU, memory, files, pids), and file-size caps
- Network disabled by default (network namespace when available, otherwise socket block for AF_INET/AF_INET6)
- Dangerous builtins disabled; import allowlist enforced
- File descriptors closed except IPC/stdio

Environment toggles:
- `PLUGIN_DISABLE_NETWORK=1` (default)
- `PLUGIN_ISOLATION=auto|none` (default: auto)

## SDK vs Server behavior

- The SDK runner does not boot a full server. Some features (macro queue clients, real chat delivery) are mimicked by mocks.
- For end-to-end tests:
  - Run the server with `PLUGIN_ISOLATION=auto` and place your plugin under `config/plugins/...`
  - Use chat/commands from your channel to exercise the full path.

## Migration guide (older plugins)

- Replace `macro:execute` permission and any `press_key(s)/click_mouse` calls with the safe `macro:enqueue` + `macro_run_keys()`.
- Replace direct bot access (`self.bot.points_system`) with `self.context.get_points/add_points/remove_points`.
- Remove any logic that expects tenant_id.

## Troubleshooting

- "Plugin failed to load" — check for invalid permissions or import of non-allowlisted modules.
- "Network disabled" — expected; use context APIs instead of network calls.
- "No output for send_chat in SDK" — chat messages print via the mock logger; ensure your code path is executed. In production, bots deliver to the platform.
- "Macro enqueue does nothing in SDK" — use the server runtime to see real macro queue behavior. The SDK is primarily for command/event logic.

## FAQ

- Can I import third-party libraries? Not in the sandbox by default (allowlist). Keep plugins small and pure-Python stdlib where possible.
- How do I share state? Maintain internal state on your plugin instance; avoid global mutable state.
- How do I store data? Use host-provided systems via context when available; avoid filesystem/network access in plugins.
