# Blueprint System Independence

This directory contains the standalone blueprint authoring pipeline. Goals:

1. Zero coupling with the main web/server/plugin runtime, except for the optional import path used when generating deployable plugin code.
2. Ability to evolve the blueprint schema, compiler, and editor UI without risking regressions in the core bot systems.
3. Provide a "standalone" compilation mode that replaces the real `BasePlugin` with a lightweight stub for preview, linting, and quick local testing.

## Components

- `actions_meta.json`: Declarative metadata for the editor (labels, field specs, defaults). No runtime code dependencies.
- `compiler.py`: Translates JSON blueprints → Python plugin source. Accepts `standalone=True` to switch import to the stub.
- `base_stub.py`: Minimal class exposing `register_command` and `run_command` so generated code is executable in isolation.
- `api.py`: FastAPI router with endpoints (`/api/blueprints/*`) kept separate from the monolithic `web_interface.py`.
- `blueprints.html` + `components/blueprints.js`: Pure static editor assets served by the main app but without referencing internal server objects.

## Standalone Mode

Use when you want preview-only code that does not require the full plugin framework:

```bash
python -m sdk.blueprints.compiler blueprint.json out.py --standalone
```

This injects:

```python
from sdk.blueprints.base_stub import BasePluginStub as BasePlugin
```

You can then execute commands locally:

```python
from out import BlueprintPlugin
p = BlueprintPlugin()
p.on_load()
print(p.run_command('hello', 'alice'))
```

## Independence Practices

- Avoid importing `src.*` modules in editor or API code (except optional fallback via compiler default mode).
- Keep metadata pure JSON; no dynamic evaluation.
- Validate blueprint structure via small helper (`validate_blueprint`) that only depends on Python stdlib.
- Fallback gracefully if metadata file is missing—return the allowed action list from compiler.

## Future Enhancements

- Version negotiation (`schema_version` field) to support migrations.
- Sandbox preview executor for limited action simulation (points/audio/voting mocks) without full context.
- Offline packaging: produce a bundle containing JSON + generated Python + manifest.

## Safety

Generated code uses only whitelisted action emitters. The compiler does not interpret arbitrary Python—fields are treated as data.

## Updating Without Coupling

When adding a new action:
1. Extend `ALLOWED_ACTIONS` and emitter logic in `compiler.py`.
2. Add metadata entry to `actions_meta.json`.
3. (Optional) Add mock behavior to a preview runner script—keep it inside this directory.
4. No changes needed in core server routes.

This keeps blueprint evolution isolated and low-risk.
