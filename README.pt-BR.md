# BotLive Plugin SDK

Desenvolva, rode e teste plugins localmente com um fluxo leve que espelha o sandbox e a API de produção.

Este SDK funciona com o Sandbox de Plugins reforçado: IPC em JSON, lista de métodos permitidos, tenant oculto, builtins perigosos desabilitados, allowlist de imports, limites de recursos e rede desabilitada por padrão.

## O que dá pra fazer
- Carregar um arquivo de plugin e interagir via um REPL simples
- Chamar comandos com `!comando [args...]`
- Simular mensagens de chat entregues ao `on_message` com `> mensagem`
- Manter compatibilidade com produção: mesma BasePlugin, permissões e métodos do PluginContext

Blueprints (no-code, experimental):
- English: `sdk/blueprints/README.en.md`
- Português (Brasil): `sdk/blueprints/README.pt-BR.md`

Obs.: O SDK agora inclui mocks em memória para pontos, votação, áudio e fila de macros para você testar a maioria das features localmente. Para comportamento fim a fim (bots reais, clientes reais de fila), use o servidor completo.

## Requisitos
- Python 3.10+
- Repositório clonado (o SDK roda dentro do repo)

## Comece rápido

1) Crie um arquivo de plugin (subclasse BasePlugin) ou use o template em `sdk/examples/hello_plugin.py`.

2) Rode o runner do SDK (recomendado com verbose na primeira vez):

```
python -m sdk.runner /caminho/absoluto/do/seu_plugin.py --tenant local --verbose
```

3) Use o REPL:
- `!<comando> [args...]` executa um comando do seu plugin
- `> sua mensagem` envia uma mensagem ao `on_message`
- `:help` mostra comandos auxiliares para pontos e enquetes
- `exit` sai

## Esqueleto de plugin (compatível com a API segura)

```python
from src.shared.plugins.base_plugin import BasePlugin

class MeuPrimeiroPlugin(BasePlugin):
    name = "Meu Primeiro Plugin"
    version = "1.0.0"
    author = "Você"
    description = "Plugin exemplo usando a API segura"
    required_permissions = ("core:log", "points:read", "points:write", "macro:enqueue")

    def on_load(self):
        self.register_command("points", self.cmd_points)
        self.register_command("macro", self.cmd_macro)

    def cmd_points(self, username: str, args: list, **kwargs) -> str:
        # Ler/atualizar pontos via contexto seguro
        if self.context:
            atual = int(self.context.get_points(username))
            return f"{username} tem {atual} pontos"
        return "contexto indisponível"

    def cmd_macro(self, username: str, args: list, **kwargs) -> str:
        # Enfileira uma macro segura (apenas teclas, sem mouse)
        if self.context:
            self.context.macro_run_keys(username=username, keys="wasd", delay=0.08, command="demo")
        return "macro enfileirada"
```

Dica: Evite acessar o bot diretamente. Prefira os métodos de `self.context`.

## Modelo de permissões

Declare apenas o necessário em `required_permissions`:
- core:log
- chat:send
- points:read, points:write
- voting:read, voting:vote, voting:manage
- audio:play, audio:tts, audio:control
- minigames:play
- leaderboard:read
- macro:enqueue

Permissões desconhecidas são rejeitadas no carregamento.

## Métodos seguros do PluginContext (allowlist no host)

- Chat: `send_chat(message, platform="twitch")` (veja limitações no SDK abaixo)
- Pontos: `get_points`, `add_points`, `remove_points`
- Votação: `start_poll`, `vote`, `get_active_poll`, `end_poll`, `get_poll_results`
- Áudio: `audio_play`, `audio_tts`, `audio_stop`, `audio_clear_queue`, `audio_queue_size`
- Leaderboard: `get_leaderboard`
- Minigames: `minigames_command`
- Macros: `macro_run_keys(username, keys, delay=0.08, command=None, platform='twitch')`

O que não pode:
- Sem acesso a tenant_id nem dados sensíveis
- Sem APIs de teclado/mouse de baixo nível expostas a plugins
- Sem ler/modificar macros.json ou outras filas

## Sandbox e segurança (alinhado com produção)

- IPC: protocolo JSON por linha, limites de tamanho (~64KB) e timeouts de 2s
- Sem novos privilégios (Linux), limites de recursos (CPU, memória, arquivos, processos) e limite de tamanho de arquivo
- Rede desabilitada por padrão (namespace quando disponível; caso contrário bloqueio de sockets AF_INET/AF_INET6)
- Builtins perigosos desabilitados; allowlist de imports aplicada
- Descritores de arquivo fechados exceto IPC/stdio

Variáveis de ambiente:
- `PLUGIN_DISABLE_NETWORK=1` (padrão)
- `PLUGIN_ISOLATION=auto|none` (padrão: auto)

## Diferenças SDK x Servidor

- O runner do SDK não inicia um servidor completo. Algumas features (clientes reais de fila, entrega real de chat) são mimetizadas por mocks.
- Para testes fim a fim:
  - Rode o servidor com `PLUGIN_ISOLATION=auto` e coloque seu plugin em `config/plugins/...`
  - Use chat/comandos do seu canal para exercitar o fluxo completo.

## Guia de migração (plugins antigos)

- Troque a permissão `macro:execute` e quaisquer chamadas `press_key(s)/click_mouse` por `macro:enqueue` + `macro_run_keys()`.
- Troque acessos diretos ao bot (`self.bot.points_system`) por `self.context.get_points/add_points/remove_points`.
- Remova qualquer lógica que dependa de tenant_id.

## Solução de problemas

- "Falha ao carregar plugin" — verifique permissões inválidas ou import de módulos fora da allowlist.
- "Rede desabilitada" — esperado; use as APIs do contexto em vez de chamadas de rede.
- "Nada acontece com send_chat no SDK" — as mensagens são registradas no logger do mock; em produção, os bots enviam para a plataforma.
- "macro_run_keys não faz nada no SDK" — use o servidor para ver a fila de macros real. O SDK serve principalmente para lógica de comandos/eventos.

## Perguntas frequentes

- Posso importar libs de terceiros? Não no sandbox por padrão (allowlist). Mantenha plugins pequenos e com stdlib quando possível.
- Como compartilho estado? Mantenha estado interno na instância do plugin; evite estado global mutável.
- Como armazeno dados? Use sistemas do host via contexto quando disponíveis; evite acesso a filesystem/rede nos plugins.
