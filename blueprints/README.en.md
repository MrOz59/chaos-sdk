# Plugin Blueprints (No-Code, Experimental)

This is an early, optional path to create plugins without writing Python code.
You describe your plugin in a simple JSON "blueprint", and the compiler generates
a secure Python plugin that uses the safe PluginContext APIs.

Status: experimental (secondary project). Backwards-compatible with the sandbox.

## Quick try

1) Use the provided example:

```
python -m sdk.blueprints.compiler sdk/blueprints/examples/hello.json /tmp/hello_plugin.py --class HelloBlueprint
```

2) Run with the SDK runner (verbose):

```
python -m sdk.runner /tmp/hello_plugin.py --tenant local --verbose
```

In the REPL, try:
- `!hello`
- `!buff`
- `:points add tester 100`
- `!buff`

## Blueprint JSON schema (v0)

Top-level fields:
- name, version, author, description
- permissions: array of permission strings (optional; defaults to ["core:log"]) – same set as the secure API
- commands: object of commandName -> list of steps

Supported actions (steps):
- respond: `{ "type": "respond", "message": "Hello {username}!" }`
- macro_run_keys: `{ "type": "macro_run_keys", "keys": "wasd", "delay": 0.08 }`
- points_get: `{ "type": "points_get", "user": "{username}" }`
- points_add: `{ "type": "points_add", "user": "{username}", "amount": 10, "reason": "bonus" }`
- points_remove: `{ "type": "points_remove", "user": "{username}", "amount": 10, "reason": "spend" }`
- audio_tts: `{ "type": "audio_tts", "text": "Hello", "lang": "en-us" }`
- if_points_at_least:
```
{
  "type": "if_points_at_least", "user": "{username}", "min": 50,
  "then": [ { "type": "respond", "message": "ok" } ],
  "else": [ { "type": "respond", "message": "not enough" } ]
}
```

Notes:
- Use `{username}` in strings to reference the calling user at runtime.
- The generated plugin returns the concatenated "respond" messages as the command response.
- All actions map to safe PluginContext calls (no direct bot access, no tenant IDs).

## Permissions

Use the same secure permission names:
- core:log, chat:send, points:read/write, voting:read/vote/manage,
  audio:play/tts/control, minigames:play, leaderboard:read, macro:enqueue

## Limitations and next steps
- This v0 is sequence-based (not a full node graph). It’s intentionally simple.
- Planned: visual editor (drag-nodes), variables/state, timers/loops, error handling, more conditions, and publish to marketplace.

## Safety
- The compiler only emits code that uses the allowed PluginContext methods.
- The sandbox still enforces isolation, timeouts, and allowlists at runtime.
