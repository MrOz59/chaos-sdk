"""
Plugin Loader - carrega plugins em sandbox com limites de recursos.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
import atexit

from chaos_sdk.plugins.permissions import (
    ALLOWED_PERMISSIONS,
    DEFAULT_PERMISSIONS,
    PluginSecurityError,
)
from chaos_sdk.plugins.context import PluginContext
from chaos_sdk.plugins.sandbox import PluginSandboxController, SandboxLimits

logger = logging.getLogger(__name__)

DANGEROUS_PLUGIN_PATTERNS = [
    "os.system(",
    "os.popen(",
    "subprocess.run",
    "subprocess.popen",
    "eval(",
    "exec(",
    "__import__(",
    "compile(",
]


class SandboxedPluginProxy:
    """Representa um plugin sendo executado em sandbox."""

    def __init__(self, metadata: Dict, controller: PluginSandboxController):
        self.controller = controller
        self.name = metadata.get("name", "unknown")
        self.version = metadata.get("version", "1.0")
        self.author = metadata.get("author")
        self.description = metadata.get("description")
        self.enabled = True
        self.granted_permissions = set(metadata.get("granted_permissions", DEFAULT_PERMISSIONS))
        self.commands: Dict[str, callable] = {}
        for command in metadata.get("commands", []):
            self.commands[command] = self._wrap_command(command)

    def _wrap_command(self, command_name: str):
        def handler(username: str, args: List[str], **kwargs):
            if not self.enabled:
                return None
            return self.controller.execute_command(command_name, username, args, kwargs)

        return handler

    def on_enable(self):
        if not self.enabled:
            self.enabled = True
            try:
                self.controller.set_enabled(True)
            except Exception as exc:
                logger.warning("Não foi possível habilitar plugin %s: %s", self.name, exc)

    def on_disable(self):
        if self.enabled:
            self.enabled = False
            try:
                self.controller.set_enabled(False)
            except Exception as exc:
                logger.warning("Não foi possível desabilitar plugin %s: %s", self.name, exc)

    def shutdown(self):
        self.controller.shutdown()


class PluginLoader:
    """Carrega e gerencia plugins dinamicamente (multi-tenant)."""

    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.plugins: Dict[str, SandboxedPluginProxy] = {}
        self.plugin_dirs = [
            "config/plugins/game_plugins",
            "config/plugins/integration_plugins",
            "config/plugins/custom_commands",
        ]
        self.state_file = "config/plugins/plugin_state.json"
        self.plugin_states = self._load_plugin_states()
        self.sandbox_limits = SandboxLimits()
        self._controllers: List[PluginSandboxController] = []
        self.allowed_permissions = self._load_allowed_permissions()
        atexit.register(self.shutdown)

    # ------------------------------------------------------------------ #
    # Estados
    # ------------------------------------------------------------------ #
    def _load_plugin_states(self) -> Dict[str, bool]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning("⚠️  Erro ao carregar estado dos plugins: %s", exc)
        return {}

    def _save_plugin_states(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump({name: plugin.enabled for name, plugin in self.plugins.items()}, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("❌ Erro ao salvar estado dos plugins: %s", exc)

    def _load_allowed_permissions(self) -> set:
        env_value = os.getenv("PLUGIN_ALLOWED_PERMISSIONS", "")
        if env_value:
            raw = {p.strip() for p in env_value.split(",") if p.strip()}
            filtered = {p for p in raw if p in ALLOWED_PERMISSIONS}
            if filtered:
                return filtered
            logger.warning("PLUGIN_ALLOWED_PERMISSIONS vazio ou inválido; usando permissões padrão.")
        return set(DEFAULT_PERMISSIONS)

    def _filter_permissions(self, requested: set, plugin_name: str) -> set:
        valid = {p for p in requested if p in ALLOWED_PERMISSIONS}
        dropped_invalid = requested.difference(valid)
        if dropped_invalid:
            logger.warning("Plugin %s solicitou permissões inválidas: %s", plugin_name, ", ".join(sorted(dropped_invalid)))
        granted = valid.intersection(self.allowed_permissions)
        dropped_host = valid.difference(granted)
        if dropped_host:
            logger.warning("Plugin %s teve permissões recusadas pelo host: %s", plugin_name, ", ".join(sorted(dropped_host)))
        if not granted:
            # Nunca conceder nada fora do allowlist; retorna apenas permissões padrão permitidas
            granted = set(DEFAULT_PERMISSIONS).intersection(self.allowed_permissions)
        return granted

    # ------------------------------------------------------------------ #
    # Carregamento
    # ------------------------------------------------------------------ #
    def load_all_plugins(self) -> List[SandboxedPluginProxy]:
        logger.info("🔌 Iniciando carregamento de plugins em sandbox...")
        loaded_count = 0
        for plugin_dir in self.plugin_dirs:
            os.makedirs(plugin_dir, exist_ok=True)
            loaded_count += len(self._load_plugins_from_directory(plugin_dir))

        # Restaurar estados
        for name, plugin in self.plugins.items():
            desired_state = self.plugin_states.get(name, True)
            if desired_state:
                plugin.on_enable()
            else:
                plugin.on_disable()

        logger.info("✅ %s plugin(s) carregado(s)", loaded_count)
        return list(self.plugins.values())

    def _load_plugins_from_directory(self, directory: str) -> List[SandboxedPluginProxy]:
        loaded: List[SandboxedPluginProxy] = []
        for filename in os.listdir(directory):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            file_path = os.path.join(directory, filename)
            if not self._scan_plugin_source(file_path):
                continue
            try:
                proxy = self._start_sandbox(file_path)
                if proxy:
                    self.plugins[proxy.name] = proxy
                    loaded.append(proxy)
            except Exception as exc:
                logger.error("❌ Erro ao carregar plugin %s: %s", filename, exc)
        return loaded

    def _scan_plugin_source(self, file_path: str) -> bool:
        """Varredura rápida por padrões perigosos antes de subir sandbox."""
        try:
            source = Path(file_path).read_text(encoding="utf-8").lower()
        except Exception as exc:
            logger.error("❌ Não foi possível ler plugin %s: %s", file_path, exc)
            return False
        for pattern in DANGEROUS_PLUGIN_PATTERNS:
            if pattern in source:
                logger.error("❌ Plugin %s bloqueado por padrão perigoso ('%s').", file_path, pattern.strip("("))
                return False
        return True

    def _start_sandbox(self, module_path: str) -> Optional[SandboxedPluginProxy]:
        module_abs = str(Path(module_path).resolve())
        controller = PluginSandboxController(
            module_path=module_abs,
            limits=self.sandbox_limits,
            host_context_factory=self._create_context_factory,
        )
        metadata = controller.start()
        requested = set(metadata.get("granted_permissions", DEFAULT_PERMISSIONS))
        granted = self._filter_permissions(requested, metadata.get("name", module_abs))
        metadata["granted_permissions"] = sorted(granted)
        proxy = SandboxedPluginProxy(metadata, controller)
        self._controllers.append(controller)
        return proxy

    def _create_context_factory(self, plugin_name: str, metadata: Dict):
        requested = set(metadata.get("granted_permissions", DEFAULT_PERMISSIONS))
        granted_permissions = self._filter_permissions(requested, plugin_name)

        def ensure(permission: str):
            if permission not in granted_permissions:
                raise PluginSecurityError(
                    f"Plugin '{plugin_name}' tentou usar '{permission}' sem permissão."
                )

        return PluginContext(plugin_name, ensure, self.bot)

    # ------------------------------------------------------------------ #
    # Estados em tempo de execução
    # ------------------------------------------------------------------ #
    def reload_plugin_states(self):
        self.plugin_states = self._load_plugin_states()
        for name, plugin in self.plugins.items():
            desired_state = self.plugin_states.get(name, True)
            if desired_state and not plugin.enabled:
                plugin.on_enable()
            elif not desired_state and plugin.enabled:
                plugin.on_disable()

    def save_states(self):
        self._save_plugin_states()

    def shutdown(self):
        for plugin in self.plugins.values():
            plugin.shutdown()
        self.plugins.clear()
        for controller in self._controllers:
            controller.shutdown()
        self._controllers.clear()

    # ------------------------------------------------------------------ #
    # Integração de comandos/eventos
    # ------------------------------------------------------------------ #
    def handle_command(self, command: str, username: str, args: List[str] = None, user_info: Optional[Dict] = None, tenant_id: Optional[str] = None):
        """Despacha um comando para plugins que o registraram."""
        args = args or []
        user_info = user_info or {}
        for plugin in self.plugins.values():
            if not plugin.enabled:
                continue
            handler = plugin.commands.get(command)
            if handler:
                try:
                    # Definir tenant atual apenas internamente antes da execução
                    try:
                        plugin.controller.set_current_tenant(tenant_id)
                    except Exception:
                        pass
                    return handler(username, args, **user_info)
                except Exception as exc:
                    logger.error("Erro executando comando '%s' no plugin %s: %s", command, plugin.name, exc)
                    continue
                finally:
                    try:
                        plugin.controller.set_current_tenant(None)
                    except Exception:
                        pass
        return None

    def broadcast_message(self, username: str, message: str, user_info: Optional[Dict] = None, tenant_id: Optional[str] = None) -> None:
        """Envia evento on_message para todos os plugins (sem expor tenant)."""
        payload = {
            "username": username,
            "message": message,
        }
        if user_info:
            payload.update(user_info)
        # Não expor tenant_id no payload
        payload.pop('tenant_id', None)
        for plugin in self.plugins.values():
            try:
                plugin.controller.set_current_tenant(tenant_id)
                plugin.controller.deliver_event("on_message", payload)
            except Exception as exc:
                logger.debug("Falha ao entregar on_message para %s: %s", plugin.name, exc)
            finally:
                try:
                    plugin.controller.set_current_tenant(None)
                except Exception:
                    pass
    # ------------------------------------------------------------------ #
    # Utilitários
    # ------------------------------------------------------------------ #
    def load_plugin_file(self, module_path: str) -> Optional[SandboxedPluginProxy]:
        """Carrega um único arquivo de plugin (SDK/local)."""
        if not module_path or not os.path.exists(module_path):
            logger.error("Arquivo de plugin não encontrado: %s", module_path)
            return None
        if not self._scan_plugin_source(module_path):
            return None
        try:
            proxy = self._start_sandbox(module_path)
            if proxy:
                self.plugins[proxy.name] = proxy
            return proxy
        except Exception as exc:
            logger.error("Erro ao carregar plugin %s: %s", module_path, exc)
            return None

    def set_host(self, bot_instance=None):
        """Atualiza referência do host/bot para novos contextos (aplica para futuros plugins)."""
        self.bot = bot_instance


_plugin_loader: Optional[PluginLoader] = None


def get_plugin_loader(bot_instance=None) -> PluginLoader:
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader(bot_instance)
    return _plugin_loader
