"""
SDK Mocks for local plugin development.
Provides a lightweight host with chat + points + voting + audio + macro shims so
plugins can be built and tested locally without uploading to the server.
"""
from __future__ import annotations

import asyncio
from typing import Optional, Dict, List, Tuple
import time
import random
import uuid
import logging

logger = logging.getLogger("sdk")


class MockTwitchBot:
    def __init__(self, channel: str = "local"):
        self.channel = channel
        self.writer = object()  # sentinel non-None

    async def send_message(self, message: str):
        logger.info(f"[TWITCH@#{self.channel}] {message}")


class InMemoryMacroQueue:
    def __init__(self):
        self.items: List[Dict] = []

    def add_macro(self, command: str, keys: str, delay: float, user: str, platform: str, tenant_id: str = "local"):
        m = {
            "id": f"{platform}_{user}_{int(time.time()*1000)}",
            "command": command,
            "keys": keys,
            "delay": delay,
            "user": user,
            "platform": platform,
            "tenant_id": tenant_id,
            "timestamp": time.time(),
        }
        self.items.append(m)
        logger.info(f"[SDK/MACRO] enqueue: {m}")
        return m

class InMemoryPointsSystem:
    def __init__(self):
        self._points: Dict[str, int] = {}

    def get_points(self, username: str) -> int:
        return int(self._points.get(username.lower(), 0))

    def add_points(self, username: str, amount: int, reason: str = "") -> bool:
        u = username.lower()
        self._points[u] = self.get_points(u) + int(amount)
        logger.info(f"[SDK/POINTS] +{amount} -> {u} ({reason}) = {self._points[u]}")
        return True

    def remove_points(self, username: str, amount: int, reason: str = "") -> bool:
        u = username.lower()
        self._points[u] = max(0, self.get_points(u) - int(amount))
        logger.info(f"[SDK/POINTS] -{amount} -> {u} ({reason}) = {self._points[u]}")
        return True

    def get_leaderboard(self, limit: int = 10, category: str = "points") -> List[Tuple[str, int]]:
        if category != "points":
            return []
        return sorted(self._points.items(), key=lambda kv: kv[1], reverse=True)[:limit]

class SdkPoll:
    def __init__(self, title: str, options: List[str], creator: str, duration_minutes: int, allow_change: bool, require_points: int):
        self.id = uuid.uuid4().hex[:12]
        self.title = title
        self.options = options
        self.creator = creator
        self.allow_change = allow_change
        self.require_points = require_points
        self.ends_at = time.time() + (duration_minutes * 60)
        self.votes: Dict[str, int] = {}  # user -> index

    def to_dict(self):
        counts = [0] * len(self.options)
        for _, idx in self.votes.items():
            if 0 <= idx < len(counts):
                counts[idx] += 1
        return {
            "id": self.id,
            "title": self.title,
            "options": self.options,
            "ends_at": self.ends_at,
            "counts": counts,
        }

class InMemoryVotingSystem:
    def __init__(self):
        self._active: Optional[SdkPoll] = None

    def create_poll(self, title: str, options: List[str], creator: str, duration_minutes: int, allow_change: bool, require_points: int, **_):
        if self._active and time.time() < self._active.ends_at:
            return {"success": False, "message": "Poll already active"}
        self._active = SdkPoll(title, options, creator, duration_minutes, allow_change, require_points)
        logger.info(f"[SDK/VOTE] new poll: {self._active.to_dict()}")
        return {"success": True, "poll": self._active.to_dict()}

    def vote(self, username: str, poll_id: str, option_index: int, **_):
        if not self._active or self._active.id != poll_id or time.time() >= self._active.ends_at:
            return {"success": False, "message": "No active poll"}
        u = username.lower()
        if not self._active.allow_change and u in self._active.votes:
            return {"success": False, "message": "Vote already cast"}
        if not (0 <= option_index < len(self._active.options)):
            return {"success": False, "message": "Invalid option"}
        self._active.votes[u] = option_index
        logger.info(f"[SDK/VOTE] {u} -> {option_index}")
        return {"success": True, "poll": self._active.to_dict()}

    def get_active_poll(self, **_):
        if self._active and time.time() < self._active.ends_at:
            return self._active
        return None

    def end_poll(self, poll_id: str, reason: str = "manual", **_):
        if not self._active or self._active.id != poll_id:
            return {"success": False, "message": "No active poll"}
        result = self._active.to_dict()
        logger.info(f"[SDK/VOTE] end: reason={reason} result={result}")
        self._active = None
        return {"success": True, "result": result}

    def get_poll_results(self, poll_id: str, **_):
        if self._active and self._active.id == poll_id:
            return self._active.to_dict()
        return None

class InMemoryAudioSystem:
    def __init__(self):
        self.queue: List[Dict] = []

    def play_sound(self, name: str):
        self.queue.append({"type": "sound", "name": name})
        logger.info(f"[SDK/AUDIO] play: {name}")
        return True

    def text_to_speech(self, text: str, lang: str = "pt-br"):
        self.queue.append({"type": "tts", "text": text, "lang": lang})
        logger.info(f"[SDK/TTS] {lang}: {text}")
        return True

    def stop(self):
        logger.info("[SDK/AUDIO] stop")

    def clear_queue(self):
        logger.info(f"[SDK/AUDIO] clear {len(self.queue)} items")
        self.queue.clear()

    def get_queue_size(self) -> int:
        return len(self.queue)


class LocalHost:
    """Minimal host object to pass into PluginLoader for SDK runs."""
    def __init__(self, tenant_id: str = "local", channel: str = "local"):
        self.tenant_id = tenant_id
        self.twitch_bot = MockTwitchBot(channel)
        self.kick_bot = None
        # In-memory systems for SDK fallbacks used by PluginContext
        self.sdk_points = InMemoryPointsSystem()
        self.sdk_voting = InMemoryVotingSystem()
        self.sdk_audio = InMemoryAudioSystem()
        self.sdk_macro_queue = InMemoryMacroQueue()

    # Optional: simulate a points system in-memory if needed later
    # For now, PluginContext routes points/votes via BotManager when available.
    # In SDK mode, prefer passing tenant_id in API calls from the plugin.
