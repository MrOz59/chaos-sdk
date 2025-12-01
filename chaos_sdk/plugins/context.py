"""
PluginContext fornece APIs limitadas e seguras para uso pelos plugins.
"""

from __future__ import annotations

from typing import Callable, Optional, List, Dict, Any

from chaos_sdk.plugins.permissions import PluginSecurityError


class PluginContext:
    """Encapsula operações expostas ao plugin."""

    def __init__(
        self,
        plugin_name: str,
        ensure_permission: Callable[[str], None],
        bot_instance,
    ):
        self._plugin_name = plugin_name
        self._ensure_permission = ensure_permission
        self._bot = bot_instance

    # ==================== Chat ====================
    async def send_chat(self, message: str, platform: str = "twitch") -> bool:
        """Envia mensagens usando bots habilitados (multi-tenant seguro, sem expor tenant ao plugin)."""
        self._ensure_permission("chat:send")
        if not message:
            return False
        # limitar tamanho para evitar spam/DoS
        if len(message) > 400:
            message = message[:400]
        platform = (platform or "twitch").lower()
        # Preferir encaminhar via BotManager multi-tenant
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            # o tenant é resolvido internamente pelo host/controller via _current_tenant_id
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None)
            if tenant:
                if platform == "twitch":
                    bot = manager.get_tenant_bot(tenant, 'twitch')
                    if bot and hasattr(bot, 'send_message'):
                        await bot.send_message(message)
                        return True
                elif platform == "kick":
                    bot = manager.get_tenant_bot(tenant, 'kick')
                    if bot and hasattr(bot, 'send_message'):
                        await bot.send_message(message)
                        return True
        except Exception:
            # Fallback para modo single-tenant/SDK local
            pass

        # Fallback: tentar usar bot único passado no contexto (SDK/local)
        if platform == "twitch":
            bot = getattr(self._bot, "twitch_bot", None)
            if bot and hasattr(bot, "send_message"):
                await bot.send_message(message)
                return True
        elif platform == "kick":
            bot = getattr(self._bot, "kick_bot", None)
            if bot and hasattr(bot, "send_message"):
                await bot.send_message(message)
                return True
        return False

    # ==================== Macros ====================
    # Desabilitado para plugins de terceiros por política de segurança.
    # Métodos removidos da API pública.

    # ==================== Points (multi-tenant) ====================
    def get_points(self, username: str) -> int:
        self._ensure_permission("points:read")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            ps = manager.get_tenant_points_system(tenant)
            if ps:
                return int(ps.get_points(username, tenant_id=tenant))
        except Exception:
            # SDK fallback
            try:
                ps = getattr(self._bot, 'sdk_points', None)
                if ps:
                    return int(ps.get_points(username))
            except Exception:
                pass
        return 0

    def add_points(self, username: str, amount: int, reason: str = '') -> bool:
        self._ensure_permission("points:write")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            ps = manager.get_tenant_points_system(tenant)
            if ps:
                return bool(ps.add_points(username, amount, reason, tenant_id=tenant))
        except Exception:
            try:
                ps = getattr(self._bot, 'sdk_points', None)
                if ps:
                    return bool(ps.add_points(username, amount, reason))
            except Exception:
                pass
        return False

    def remove_points(self, username: str, amount: int, reason: str = '') -> bool:
        self._ensure_permission("points:write")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            ps = manager.get_tenant_points_system(tenant)
            if ps:
                return bool(ps.remove_points(username, amount, reason, tenant_id=tenant))
        except Exception:
            try:
                ps = getattr(self._bot, 'sdk_points', None)
                if ps:
                    return bool(ps.remove_points(username, amount, reason))
            except Exception:
                pass
        return False

    # ==================== Voting (multi-tenant) ====================
    def start_poll(
        self,
        title: str,
        options: List[str],
        creator: str,
        duration_minutes: int = 5,
        allow_change: bool = True,
        require_points: int = 0,
    ) -> Dict[str, Any]:
        self._ensure_permission("voting:manage")
        # validações básicas
        if not title or not isinstance(options, list) or len(options) < 2 or len(options) > 10:
            return {"success": False, "message": "❌ Opções inválidas"}
        options = [str(o)[:60] for o in options]
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            vs = manager.voting_systems.get(tenant)
            if vs:
                return vs.create_poll(title, options, creator, duration_minutes, allow_change, require_points, tenant_id=tenant)
        except Exception:
            try:
                vs = getattr(self._bot, 'sdk_voting', None)
                if vs:
                    return vs.create_poll(title, options, creator, duration_minutes, allow_change, require_points)
            except Exception:
                pass
        return {"success": False, "message": "Voting system unavailable"}

    def vote(self, username: str, poll_id: str, option_index: int) -> Dict[str, Any]:
        self._ensure_permission("voting:vote")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            vs = manager.voting_systems.get(tenant)
            if vs:
                return vs.vote(username, poll_id, option_index, tenant_id=tenant)
        except Exception:
            try:
                vs = getattr(self._bot, 'sdk_voting', None)
                if vs:
                    return vs.vote(username, poll_id, option_index)
            except Exception:
                pass
        return {"success": False, "message": "Voting system unavailable"}

    def get_active_poll(self) -> Optional[Dict[str, Any]]:
        self._ensure_permission("voting:read")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            vs = manager.voting_systems.get(tenant)
            if vs:
                poll = vs.get_active_poll(tenant_id=tenant)
                return poll.__dict__ if poll else None
        except Exception:
            try:
                vs = getattr(self._bot, 'sdk_voting', None)
                if vs:
                    poll = vs.get_active_poll()
                    return poll.to_dict() if poll else None
            except Exception:
                pass
        return None

    # ==================== Audio (multi-tenant, seguro) ====================
    def audio_play(self, sound_name: str) -> bool:
        self._ensure_permission("audio:play")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            audio = manager.get_tenant_audio_system(tenant)
            if audio:
                return bool(audio.play_sound(sound_name))
        except Exception:
            try:
                audio = getattr(self._bot, 'sdk_audio', None)
                if audio:
                    return bool(audio.play_sound(sound_name))
            except Exception:
                pass
        return False

    def audio_tts(self, text: str, lang: str = 'pt-br') -> bool:
        self._ensure_permission("audio:tts")
        if not text:
            return False
        if len(text) > 200:
            text = text[:200]
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            audio = manager.get_tenant_audio_system(tenant)
            if audio:
                return bool(audio.text_to_speech(text, lang=lang))
        except Exception:
            try:
                audio = getattr(self._bot, 'sdk_audio', None)
                if audio:
                    return bool(audio.text_to_speech(text, lang=lang))
            except Exception:
                pass
        return False

    def audio_stop(self) -> None:
        self._ensure_permission("audio:control")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            audio = manager.get_tenant_audio_system(tenant)
            if audio:
                audio.stop()
        except Exception:
            try:
                audio = getattr(self._bot, 'sdk_audio', None)
                if audio:
                    audio.stop()
            except Exception:
                pass

    def audio_clear_queue(self) -> None:
        self._ensure_permission("audio:control")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            audio = manager.get_tenant_audio_system(tenant)
            if audio:
                audio.clear_queue()
        except Exception:
            try:
                audio = getattr(self._bot, 'sdk_audio', None)
                if audio:
                    audio.clear_queue()
            except Exception:
                pass

    def audio_queue_size(self) -> int:
        self._ensure_permission("audio:control")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            audio = manager.get_tenant_audio_system(tenant)
            if audio:
                return int(audio.get_queue_size())
        except Exception:
            try:
                audio = getattr(self._bot, 'sdk_audio', None)
                if audio:
                    return int(audio.get_queue_size())
            except Exception:
                pass
        return 0

    # ==================== Leaderboard (read-only) ====================
    def get_leaderboard(self, limit: int = 10, category: str = 'points') -> List[tuple]:
        self._ensure_permission("leaderboard:read")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            ps = manager.get_tenant_points_system(tenant)
            if ps:
                return ps.get_leaderboard(limit=limit, category=category, tenant_id=tenant)
        except Exception:
            try:
                ps = getattr(self._bot, 'sdk_points', None)
                if ps:
                    return ps.get_leaderboard(limit=limit, category=category)
            except Exception:
                pass
        return []

    # ==================== Minigames (roteador seguro) ====================
    def minigames_command(self, command: str, username: str, args: List[str]) -> Optional[str]:
        self._ensure_permission("minigames:play")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            from chaos_sdk.server_bridge import MinigamesCommands
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'global'
            mg = manager.minigames_systems.get(tenant)
            vs = manager.voting_systems.get(tenant)
            if mg:
                router = MinigamesCommands(bot_instance=None, manager=mg, voting_system=vs, tenant_id=tenant)
                return router.handle_command(command, username, args, user_info={}, tenant_id=tenant)
        except Exception:
            pass
        return None

    # ==================== Macros (enfileirar apenas) ====================
    def macro_run_keys(self, username: str, keys: str, delay: float = 0.08, command: str = None, platform: str = 'twitch') -> bool:
        """Enfileira uma sequência de teclas como macro para execução pelo cliente do tenant.
        Não permite listar/alterar/cancelar macros existentes.
        """
        self._ensure_permission("macro:enqueue")
        # validações
        if not keys or len(keys) > 64:
            return False
        if delay < 0.02:
            delay = 0.02
        if delay > 1.0:
            delay = 1.0
        try:
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            from chaos_sdk.server_bridge import get_macro_queue
            mq = get_macro_queue()
            # prefixo obrigatório com plugin
            safe_cmd = f"plugin:{self._plugin_name}:{(command or 'action')[:32]}"
            mq.add_macro(
                command=safe_cmd,
                keys=keys,
                delay=delay,
                user=username,
                platform=platform,
                tenant_id=tenant,
            )
            return True
        except Exception:
            # SDK fallback
            try:
                tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
                mq = getattr(self._bot, 'sdk_macro_queue', None)
                safe_cmd = f"plugin:{self._plugin_name}:{(command or 'action')[:32]}"
                if mq:
                    mq.add_macro(command=safe_cmd, keys=keys, delay=delay, user=username, platform=platform, tenant_id=tenant)
                    return True
            except Exception:
                pass
            return False

    def end_poll(self, poll_id: str, reason: str = "manual") -> Dict[str, Any]:
        self._ensure_permission("voting:manage")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            vs = manager.voting_systems.get(tenant)
            if vs:
                return vs.end_poll(poll_id, reason=reason, tenant_id=tenant)
        except Exception:
            try:
                vs = getattr(self._bot, 'sdk_voting', None)
                if vs:
                    return vs.end_poll(poll_id, reason=reason)
            except Exception:
                pass
        return {"success": False, "message": "Voting system unavailable"}

    def get_poll_results(self, poll_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_permission("voting:read")
        try:
            from chaos_sdk.server_bridge import get_bot_manager
            manager = get_bot_manager()
            tenant = getattr(self, '_current_tenant_id', None) or getattr(self._bot, 'tenant_id', None) or 'default'
            vs = manager.voting_systems.get(tenant)
            if vs:
                return vs.get_poll_results(poll_id, tenant_id=tenant)
        except Exception:
            try:
                vs = getattr(self._bot, 'sdk_voting', None)
                if vs:
                    return vs.get_poll_results(poll_id)
            except Exception:
                pass
        return None
