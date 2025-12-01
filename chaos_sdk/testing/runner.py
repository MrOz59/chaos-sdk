"""
Local Plugin SDK Runner

Usage:
        python -m sdk.runner /absolute/path/to/your_plugin.py [--tenant local] [--verbose]

This will:
    - start the sandbox for the provided plugin file
    - provide a tiny REPL to invoke registered commands
    - simulate chat messages broadcast to the plugin's on_message
    - enable detailed logs in --verbose mode to help plugin debugging

Notes:
    - The SDK supplies in-memory systems for points, voting, audio and macro queue.
        Your plugin can test most features locally without the full server.
"""
from __future__ import annotations

import asyncio
import os
import sys
import logging
from typing import List

from sdk.mocks import LocalHost


def usage_and_exit():
    print("Usage: python -m sdk.runner /abs/path/to/plugin.py [--tenant local] [--verbose]")
    sys.exit(2)


async def main(argv: List[str]):
    if len(argv) < 2:
        usage_and_exit()
    # Parse args (very light custom parsing to avoid adding deps)
    args = [a for a in argv[1:] if a]
    if not args:
        usage_and_exit()

    plugin_path = None
    tenant_id = "local"
    verbose = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--tenant" and i + 1 < len(args):
            tenant_id = args[i + 1]
            i += 2
            continue
        if a == "--verbose":
            verbose = True
            i += 1
            continue
        if not plugin_path:
            plugin_path = a
            i += 1
            continue
        i += 1

    if not plugin_path:
        usage_and_exit()
    if not os.path.isabs(plugin_path):
        plugin_path = os.path.abspath(plugin_path)
    if not os.path.exists(plugin_path):
        print(f"Plugin not found: {plugin_path}")
        sys.exit(1)

    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(name)s: %(message)s")

    # Late import to avoid heavy deps at tool startup
    from chaos_sdk.plugins.plugin_loader import get_plugin_loader

    host = LocalHost(tenant_id=tenant_id, channel="local")
    loader = get_plugin_loader(host)
    loader.set_host(host)

    proxy = loader.load_plugin_file(plugin_path)
    if not proxy:
        print("Failed to load plugin.")
        sys.exit(1)

    print(f"Loaded plugin: {proxy.name} v{proxy.version} (commands: {list(proxy.commands.keys())})")
    if verbose:
        print("Verbose logging enabled. Context calls and SDK systems will log details.")

    # Simple REPL
    print("\nType '!<command> [args...]' to run a plugin command.")
    print("Type '> msg your message' to simulate a chat message.")
    print("Type ':help' for helper actions (points, polls).")
    print("Type 'exit' to quit.\n")

    loop = asyncio.get_event_loop()

    while True:
        try:
            raw = await loop.run_in_executor(None, sys.stdin.readline)
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            break
        line = raw.strip()
        if not line:
            continue
        if line.lower() in {"exit", "quit"}:
            break
        if line.lower() in {":help", ":h"}:
            print("\nHelper commands:\n"
                  "  :points add <user> <amount> [reason]\n"
                  "  :points get <user>\n"
                  "  :poll start <title>|<opt1>|<opt2>[|opt3...] [minutes=1]\n"
                  "  :poll vote <user> <poll_id> <index>\n"
                  "  :poll active\n"
                  "  :poll end <poll_id> [reason]\n")
            continue
        if line.startswith("!"):
            parts = line[1:].split()
            cmd = parts[0]
            args = parts[1:]
            resp = loader.handle_command(cmd, username="tester", args=args, user_info={}, tenant_id=tenant_id)
            if resp:
                print(f"< {resp}")
            continue
        if line.startswith("> ") or line.startswith(">"):
            msg = line[2:].strip() if line.startswith("> ") else line[1:].strip()
            loader.broadcast_message("tester", msg, {"platform": "twitch"}, tenant_id=tenant_id)
            continue
        if line.startswith(":points "):
            parts = line.split()
            if len(parts) >= 3 and parts[1] == "get":
                user = parts[2]
                print(f"points[{user}] = {host.sdk_points.get_points(user)}")
                continue
            if len(parts) >= 4 and parts[1] == "add":
                user = parts[2]
                try:
                    amt = int(parts[3])
                except Exception:
                    print("amount must be int")
                    continue
                reason = " ".join(parts[4:]) if len(parts) > 4 else "manual"
                host.sdk_points.add_points(user, amt, reason)
                print(f"points[{user}] = {host.sdk_points.get_points(user)}")
                continue
            print(":points usage: :points get <user> | :points add <user> <amount> [reason]")
            continue
        if line.startswith(":poll "):
            parts = line.split(maxsplit=2)
            if len(parts) >= 2 and parts[1] == "active":
                ap = host.sdk_voting.get_active_poll()
                print(ap.to_dict() if ap else None)
                continue
            if len(parts) >= 3 and parts[1] == "start":
                payload = parts[2]
                # format: title|opt1|opt2|opt3 ... [minutes=N]
                minutes = 1
                if " minutes=" in payload:
                    try:
                        before, after = payload.split(" minutes=", 1)
                        payload = before
                        minutes = int(after.strip())
                    except Exception:
                        pass
                fields = [p.strip() for p in payload.split("|") if p.strip()]
                if len(fields) < 3:
                    print("format: :poll start <title>|<opt1>|<opt2>[|opt3...] [minutes=N]")
                else:
                    title, options = fields[0], fields[1:]
                    res = host.sdk_voting.create_poll(title, options, creator="tester", duration_minutes=minutes, allow_change=True, require_points=0)
                    print(res)
                continue
            if len(parts) >= 3 and parts[1] == "vote":
                rest = parts[2].split()
                if len(rest) < 3:
                    print(":poll vote <user> <poll_id> <index>")
                else:
                    user, pid, idxs = rest[0], rest[1], rest[2]
                    try:
                        idx = int(idxs)
                    except Exception:
                        print("index must be int")
                        continue
                    print(host.sdk_voting.vote(user, pid, idx))
                continue
            if len(parts) >= 3 and parts[1] == "end":
                rest = parts[2].split(maxsplit=1)
                pid = rest[0]
                reason = rest[1] if len(rest) > 1 else "manual"
                print(host.sdk_voting.end_poll(pid, reason=reason))
                continue
            print(":poll usage: start|active|vote|end (see :help)")
            continue
        print("Unknown input. Use '!cmd', '> message', or 'exit'.")

    # Cleanup
    loader.shutdown()


if __name__ == "__main__":
    asyncio.run(main(sys.argv))
