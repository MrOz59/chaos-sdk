"""
Declaração de permissões para plugins e utilitários de segurança.
"""

from __future__ import annotations

from typing import Dict, Set


ALLOWED_PERMISSIONS: Dict[str, str] = {
    "core:log": "Permite registrar mensagens nos logs do servidor.",
    "chat:send": "Autoriza envio de mensagens no chat via contexto seguro.",
    "points:read": "Autoriza consulta ao saldo de pontos dos usuários.",
    "points:write": "Autoriza adicionar/remover pontos.",
    "voting:read": "Permite ler votações ativas e resultados.",
    "voting:vote": "Permite votar em votações ativas.",
    "voting:manage": "Permite criar/encerrar votações.",
    "audio:play": "Permite tocar sons predefinidos.",
    "audio:tts": "Permite enfileirar TTS.",
    "audio:control": "Permite parar/limpar fila de áudio e consultar status.",
    "minigames:play": "Permite invocar minigames via roteador seguro.",
    "leaderboard:read": "Permite ler leaderboard de pontos.",
    "macro:enqueue": "Permite enfileirar execução de teclas via MacroQueue (sem acesso a filas alheias).",
}

DEFAULT_PERMISSIONS: Set[str] = {"core:log"}


class PluginSecurityError(RuntimeError):
    """Disparado quando um plugin tenta executar operação sem permissão."""

    pass
