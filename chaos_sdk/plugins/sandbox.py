"""
Sandbox infrastructure for plugins.
Executa cada plugin em um subprocesso com limites de CPU/RAM e comunica via sockets.
"""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import itertools
import os
import queue
import resource
import threading
from dataclasses import dataclass
from multiprocessing import Process
import socket
import json
import select
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys
import pwd
import grp
import ctypes
import errno

from chaos_sdk.plugins.permissions import (
    ALLOWED_PERMISSIONS,
    DEFAULT_PERMISSIONS,
    PluginSecurityError,
)
from chaos_sdk.plugins.context import PluginContext

DEFAULT_SANDBOX_CPU = int(os.getenv("PLUGIN_SANDBOX_CPU_LIMIT", "5"))
DEFAULT_SANDBOX_MEMORY_MB = int(os.getenv("PLUGIN_SANDBOX_MEMORY_MB", "128"))
DISABLE_NETWORK = os.getenv("PLUGIN_DISABLE_NETWORK", "1") == "1"
ISOLATION_MODE = os.getenv("PLUGIN_ISOLATION", "auto")  # auto|none


# Linux prctl constants
PR_SET_NO_NEW_PRIVS = 38

def _prctl(option: int, arg2: int = 0, arg3: int = 0, arg4: int = 0, arg5: int = 0) -> None:
    try:
        libc = ctypes.CDLL(None)
        res = libc.prctl(ctypes.c_int(option), ctypes.c_ulong(arg2), ctypes.c_ulong(arg3), ctypes.c_ulong(arg4), ctypes.c_ulong(arg5))
        if res != 0:
            # ignore errors, best-effort
            pass
    except Exception:
        # Not Linux or prctl unavailable
        pass


@dataclass
class SandboxLimits:
    cpu_seconds: int = DEFAULT_SANDBOX_CPU
    memory_mb: int = DEFAULT_SANDBOX_MEMORY_MB

    @property
    def memory_bytes(self) -> int:
        return self.memory_mb * 1024 * 1024


def _load_plugin_class(module_path: str):
    spec = importlib.util.spec_from_file_location(
        Path(module_path).stem, module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    from chaos_sdk.plugins.base_plugin import BasePlugin

    for _, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
            return obj
    raise RuntimeError("Nenhuma classe BasePlugin encontrada em %s" % module_path)


class SandboxContextBridge:
    """Contexto usado dentro do subprocesso para enviar chamadas ao host."""

    def __init__(self, sock):
        self._sock = sock
        self._sock_file = self._sock.makefile('rwb', buffering=0)
        self._seq = itertools.count(1)

    def _call_host(self, method: str, *args, **kwargs):
        request_id = next(self._seq)
        payload = {
            "type": "context_request",
            "id": request_id,
            "method": method,
            "args": args,
            "kwargs": kwargs,
        }
        self._send_json(payload)
        while True:
            msg = self._recv_json()
            if msg.get("type") == "context_response" and msg.get("id") == request_id:
                if msg.get("error"):
                    raise PluginSecurityError(msg["error"])
                return msg.get("result")

    def _send_json(self, data: dict):
        raw = (json.dumps(data, separators=(',', ':'), ensure_ascii=True) + "\n").encode('utf-8')
        if len(raw) > 64 * 1024:
            raise PluginSecurityError("Payload muito grande")
        self._sock_file.write(raw)
        self._sock_file.flush()

    def _recv_json(self) -> dict:
        line = self._sock_file.readline()
        if not line:
            raise PluginSecurityError("Conexão com host encerrada")
        if len(line) > 64 * 1024:
            raise PluginSecurityError("Resposta muito grande")
        try:
            return json.loads(line.decode('utf-8'))
        except Exception:
            raise PluginSecurityError("Resposta inválida do host")

    async def send_chat(self, message: str, platform: str = "twitch") -> bool:
        return self._call_host("send_chat", message, platform)

    def press_key(self, key: str, duration: float = 0.1):
        return self._call_host("press_key", key, duration)

    def press_keys(self, keys: str, delay: float = 0.08):
        return self._call_host("press_keys", keys, delay)

    def click_mouse(self, button: str = "left"):
        return self._call_host("click_mouse", button)

    def move_mouse(self, x: int, y: int):
        return self._call_host("move_mouse", x, y)

    # Points API
    def get_points(self, username: str) -> int:
        return self._call_host("get_points", username)

    def add_points(self, username: str, amount: int, reason: str = '') -> bool:
        return self._call_host("add_points", username, amount, reason)

    def remove_points(self, username: str, amount: int, reason: str = '') -> bool:
        return self._call_host("remove_points", username, amount, reason)

    # Voting API
    def start_poll(self, title: str, options: list, creator: str, duration_minutes: int = 5, allow_change: bool = True, require_points: int = 0):
        return self._call_host("start_poll", title, options, creator, duration_minutes, allow_change, require_points)

    def vote(self, username: str, poll_id: str, option_index: int):
        return self._call_host("vote", username, poll_id, option_index)

    def get_active_poll(self):
        return self._call_host("get_active_poll")

    def end_poll(self, poll_id: str, reason: str = "manual"):
        return self._call_host("end_poll", poll_id, reason)

    def get_poll_results(self, poll_id: str):
        return self._call_host("get_poll_results", poll_id)


def _sandbox_entry(
    module_path: str,
    cmd_fd: int,
    ctx_fd: int,
    limits: SandboxLimits,
) -> None:
    """Função executada no subprocesso."""
    try:
        if ISOLATION_MODE != "none":
            # Prevent gaining new privileges
            _prctl(PR_SET_NO_NEW_PRIVS, 1)

            # Try to block networking using namespaces (Linux only)
            if DISABLE_NETWORK:
                try:
                    if hasattr(os, "unshare"):
                        # 0x40000000 is CLONE_NEWNET; avoid importing linux-specific flags
                        CLONE_NEWNET = 0x40000000
                        os.unshare(CLONE_NEWNET)
                except Exception:
                    # Fallback: monkeypatch socket to block AF_INET/AF_INET6
                    try:
                        _orig_socket = socket.socket
                        def _blocked_socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, fileno=None):
                            if family in (socket.AF_INET, socket.AF_INET6):
                                raise PluginSecurityError("Networking desabilitado no sandbox")
                            return _orig_socket(family, type, proto, fileno) if fileno is not None else _orig_socket(family, type, proto)
                        socket.socket = _blocked_socket  # type: ignore
                    except Exception:
                        pass

        if ISOLATION_MODE != "none":
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (limits.cpu_seconds, limits.cpu_seconds),
            )
            resource.setrlimit(
                resource.RLIMIT_AS,
                (limits.memory_bytes, limits.memory_bytes),
            )
            # Restrict number of open files and processes
            try:
                resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            except Exception:
                pass
            try:
                if hasattr(resource, "RLIMIT_NPROC"):
                    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
            except Exception:
                pass
            try:
                if hasattr(resource, "RLIMIT_FSIZE"):
                    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))  # 10MB
            except Exception:
                pass
    except Exception:
        # Em sistemas sem suporte, continua sem crash
        pass

    # Sanitize environment
    try:
        import builtins as _builtins
        import sys as _sys
        import importlib as _importlib
        # Clear env and set minimal PATH
        os.environ.clear()
        os.environ["PATH"] = "/usr/bin:/bin"
        try:
            os.chdir("/tmp")
        except Exception:
            pass

        if ISOLATION_MODE != "none":
            # Close all unexpected file descriptors except the IPC ones and stdio
            try:
                preserve = {0, 1, 2, int(cmd_fd), int(ctx_fd)}
                fd_dir = "/proc/self/fd"
                for name in os.listdir(fd_dir):
                    try:
                        fd = int(name)
                    except ValueError:
                        continue
                    if fd in preserve:
                        continue
                    try:
                        os.close(fd)
                    except Exception:
                        pass
            except Exception:
                # Best effort only
                pass

        # Disable dangerous builtins
        for dangerous in ("eval", "exec", "compile"):
            def _blocked(*a, **k):
                raise PluginSecurityError("Operação não permitida")
            setattr(_builtins, dangerous, _blocked)

        # Import allowlist (modules que plugins podem carregar)
        _ALLOWED_IMPORTS = {
            "math", "random", "time", "json", "re", "typing", "dataclasses", "collections", "itertools",
            "logging", "functools", "statistics", "datetime", "string",
            "src.shared.plugins.base_plugin", "src.shared.plugins.permissions",
        }
        real_import_module = _importlib.import_module
        real_builtin_import = _builtins.__import__

        def _is_allowed(module: str) -> bool:
            return module in _ALLOWED_IMPORTS or any(module.startswith(p + ".") for p in _ALLOWED_IMPORTS)

        def safe_import_module(name, package=None):
            if not _is_allowed(name):
                raise ImportError(f"Import não permitido: {name}")
            return real_import_module(name, package=package)

        def safe_builtin_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Resolver nome absoluto simples; relativa não é suportada no sandbox
            if not _is_allowed(name):
                raise ImportError(f"Import não permitido: {name}")
            return real_builtin_import(name, globals, locals, fromlist, level)

        _importlib.import_module = safe_import_module
        _builtins.__import__ = safe_builtin_import
    except Exception:
        pass

    if ISOLATION_MODE != "none":
        # Drop privileges if possible (Linux)
        try:
            # If running as root, drop to nobody/nogroup
            if os.geteuid() == 0:
                try:
                    gid = grp.getgrnam("nogroup").gr_gid
                except KeyError:
                    gid = 65534
                try:
                    uid = pwd.getpwnam("nobody").pw_uid
                except KeyError:
                    uid = 65534
                try:
                    os.setgid(gid)
                    os.setgroups([])
                except Exception:
                    pass
                try:
                    os.setuid(uid)
                except Exception:
                    pass
        except Exception:
            pass

    plugin_cls = _load_plugin_class(module_path)
    plugin = plugin_cls(bot_instance=None)

    requested = set(getattr(plugin, "required_permissions", set())) or set(
        DEFAULT_PERMISSIONS
    )
    invalid = requested.difference(ALLOWED_PERMISSIONS)
    if invalid:
        raise PluginSecurityError(
            f"Permissões inválidas declaradas: {', '.join(sorted(invalid))}"
        )
    plugin._set_granted_permissions(requested)
    # Recreate sockets
    cmd_sock = socket.socket(fileno=cmd_fd)
    ctx_sock = socket.socket(fileno=ctx_fd)
    context_bridge = SandboxContextBridge(ctx_sock)
    plugin._bind_context(context_bridge)
    plugin.on_load()

    metadata = {
        "name": plugin.name,
        "version": plugin.version,
        "author": plugin.author,
        "description": plugin.description,
        "commands": list(plugin.commands.keys()),
        "granted_permissions": sorted(requested),
    }
    _send_json(cmd_sock, {"type": "loaded", "metadata": metadata})

    while True:
        msg = _recv_json(cmd_sock)
        if msg is None:
            break
        mtype = msg.get("type")
        if mtype == "execute_command":
            command = msg.get("command")
            username = msg.get("username")
            args = msg.get("args", [])
            kwargs = msg.get("kwargs", {})
            response = None
            error = None
            try:
                handler = plugin.commands.get(command)
                if handler:
                    response = handler(username, args, **kwargs)
                else:
                    response = None
            except Exception as exc:
                error = str(exc)
            _send_json(cmd_sock, {"type": "response", "id": msg.get("id"), "result": response, "error": error})
        elif mtype == "set_enabled":
            enabled = bool(msg.get("enabled", True))
            try:
                if enabled:
                    plugin.on_enable()
                else:
                    plugin.on_disable()
            except Exception:
                pass
            _send_json(cmd_sock, {"type": "response", "id": msg.get("id"), "result": True, "error": None})
        elif mtype == "event":
            event = msg.get("event")
            payload = msg.get("payload", {})
            error = None
            try:
                # Map event names to plugin methods
                method_name = None
                if event in {"on_message", "on_points_earned", "on_points_spent", "on_stream_start", "on_stream_end", "on_viewer_join", "on_viewer_leave"}:
                    method_name = event
                if method_name and hasattr(plugin, method_name):
                    getattr(plugin, method_name)(**payload)
            except Exception as exc:
                error = str(exc)
            _send_json(cmd_sock, {"type": "response", "id": msg.get("id"), "result": True, "error": error})
        elif mtype == "shutdown":
            try:
                plugin.on_unload()
            except Exception:
                pass
            _send_json(cmd_sock, {"type": "response", "id": msg.get("id"), "result": True, "error": None})
            break
        else:
            _send_json(cmd_sock, {"type": "response", "id": msg.get("id"), "error": f"Mensagem desconhecida: {mtype}"})


def _send_json(sock: socket.socket, data: dict):
    raw = (json.dumps(data, separators=(',', ':'), ensure_ascii=True) + "\n").encode('utf-8')
    if len(raw) > 64 * 1024:
        raise PluginSecurityError("Payload muito grande")
    sock.sendall(raw)


def _recv_json(sock: socket.socket) -> dict:
    # Read until newline (simple framing)
    chunks = []
    total = 0
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return None
        chunks.append(chunk)
        total += len(chunk)
        if total > 64 * 1024:
            raise PluginSecurityError("Payload muito grande")
        if b"\n" in chunk:
            break
    data = b"".join(chunks)
    line = data.split(b"\n", 1)[0]
    try:
        return json.loads(line.decode('utf-8'))
    except Exception:
        raise PluginSecurityError("Mensagem inválida")


class PluginSandboxController:
    """Controla o subprocesso e expõe métodos para o host."""

    def __init__(
        self,
        module_path: str,
        limits: SandboxLimits,
        host_context_factory,
    ):
        self.module_path = module_path
        self.limits = limits
        self.host_context_factory = host_context_factory
        self.cmd_parent, cmd_child = socket.socketpair()
        self.ctx_parent, ctx_child = socket.socketpair()
        self.process = Process(
            target=_sandbox_entry,
            args=(module_path, cmd_child.fileno(), ctx_child.fileno(), limits),
            daemon=True,
        )
        self._response_futures: Dict[int, queue.Queue] = {}
        self._seq = itertools.count(1)
        self._ctx_thread: Optional[threading.Thread] = None
        self._context = None
        self._loop = None
        self._running = False
        self._current_tenant = None

    def start(self):
        self.process.start()
        loaded_msg = self._recv_with_timeout()
        if loaded_msg.get("type") != "loaded":
            raise RuntimeError("Falha ao iniciar sandbox do plugin.")
        metadata = loaded_msg.get("metadata", {})
        self._context = self.host_context_factory(metadata.get("name"), metadata)
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = None
        self._running = True
        self._ctx_thread = threading.Thread(
            target=self._context_loop, name=f"plugin-ctx-{metadata.get('name')}"
        )
        self._ctx_thread.daemon = True
        self._ctx_thread.start()
        return metadata

    def _context_loop(self):
        while self._running:
            try:
                msg = self._recv_json_safe(self.ctx_parent)
            except Exception:
                break
            if not msg:
                continue
            if msg.get("type") != "context_request":
                continue
            req_id = msg.get("id")
            method = msg.get("method")
            args = msg.get("args", [])
            kwargs = msg.get("kwargs", {})
            try:
                result = self._call_context(method, *args, **kwargs)
                error = None
            except Exception as exc:
                result = None
                error = str(exc)
            _send_json(self.ctx_parent, {"type": "context_response", "id": req_id, "result": result, "error": error})

    def _call_context(self, method: str, *args, **kwargs):
        if not self._context:
            raise RuntimeError("Contexto indisponível")
        # Allowlist estrita de métodos de contexto expostos ao plugin
        allowed = {
            "send_chat",
            "get_points", "add_points", "remove_points",
            "start_poll", "vote", "get_active_poll", "end_poll", "get_poll_results",
            "audio_play", "audio_tts", "audio_stop", "audio_clear_queue", "audio_queue_size",
            "get_leaderboard",
            "minigames_command",
            "macro_run_keys",
        }
        if method not in allowed:
            raise PluginSecurityError(f"Método de contexto não permitido: {method}")
        attr = getattr(self._context, method, None)
        if not attr:
            raise AttributeError(f"Método de contexto inexistente: {method}")
        # Propagar tenant atual de forma interna e opaca ao plugin
        try:
            setattr(self._context, "_current_tenant_id", self._current_tenant)
            result = attr(*args, **kwargs)
        finally:
            try:
                delattr(self._context, "_current_tenant_id")
            except Exception:
                pass
        if inspect.iscoroutine(result):
            if self._loop and self._loop.is_running():
                fut = asyncio.run_coroutine_threadsafe(result, self._loop)
                return fut.result()
            return asyncio.run(result)
        return result

    def _request(self, payload: Dict[str, Any]) -> Any:
        req_id = next(self._seq)
        payload["id"] = req_id
        _send_json(self.cmd_parent, payload)
        # Wait with timeout
        msg = self._recv_with_timeout()
        if not msg or msg.get("id") != req_id:
            raise PluginSecurityError("Timeout ou resposta inválida do plugin")
        if msg.get("error"):
            raise PluginSecurityError(msg["error"])
        return msg.get("result")

    def _recv_with_timeout(self, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        r, _, _ = select.select([self.cmd_parent], [], [], timeout)
        if not r:
            return None
        return self._recv_json_safe(self.cmd_parent)

    def _recv_json_safe(self, sock: socket.socket) -> Optional[Dict[str, Any]]:
        try:
            return _recv_json(sock)
        except Exception:
            return None

    def execute_command(self, command: str, username: str, args: List[str], kwargs: Dict[str, Any]) -> Any:
        return self._request(
            {
                "type": "execute_command",
                "command": command,
                "username": username,
                "args": args,
                "kwargs": kwargs,
            }
        )

    def set_enabled(self, enabled: bool) -> None:
        self._request({"type": "set_enabled", "enabled": bool(enabled)})

    def shutdown(self):
        if not self._running:
            return
        try:
            self._request({"type": "shutdown"})
        except Exception:
            pass
        self._running = False
        if self._ctx_thread and self._ctx_thread.is_alive():
            self._ctx_thread.join(timeout=1)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=1)

    def deliver_event(self, event: str, payload: Dict[str, Any]) -> bool:
        """Envia um evento (on_message, etc.) para o plugin no sandbox."""
        try:
            return bool(self._request({"type": "event", "event": event, "payload": payload}))
        except Exception:
            return False

    def set_current_tenant(self, tenant_id: Optional[str]):
        """Define tenant atual (interno) usado por chamadas de contexto subsequentes."""
        self._current_tenant = tenant_id
