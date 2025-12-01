# Blueprints de Plugins (No-Code, Experimental)

Caminho opcional para criar plugins sem escrever Python.
Você descreve seu plugin em um JSON simples ("blueprint"), e o compilador gera
um plugin Python seguro que usa as APIs do PluginContext.

Status: experimental (projeto secundário). Compatível com o sandbox.

## Teste rápido

1) Use o exemplo incluso:

```
python -m sdk.blueprints.compiler sdk/blueprints/examples/hello.json /tmp/hello_plugin.py --class HelloBlueprint
```

2) Rode com o runner do SDK (verbose):

```
python -m sdk.runner /tmp/hello_plugin.py --tenant local --verbose
```

No REPL, tente:
- `!hello`
- `!buff`
- `:points add tester 100`
- `!buff`

## Esquema do Blueprint (v0)

Campos principais:
- name, version, author, description
- permissions: array de permissões (opcional; padrão ["core:log"]) – mesmo conjunto da API segura
- commands: objeto de nomeDoComando -> lista de passos

Ações suportadas (passos):
- respond: `{ "type": "respond", "message": "Olá {username}!" }`
- macro_run_keys: `{ "type": "macro_run_keys", "keys": "wasd", "delay": 0.08 }`
- points_get: `{ "type": "points_get", "user": "{username}" }`
- points_add: `{ "type": "points_add", "user": "{username}", "amount": 10, "reason": "bonus" }`
- points_remove: `{ "type": "points_remove", "user": "{username}", "amount": 10, "reason": "spend" }`
- audio_tts: `{ "type": "audio_tts", "text": "Olá", "lang": "pt-br" }`
- if_points_at_least:
```
{
  "type": "if_points_at_least", "user": "{username}", "min": 50,
  "then": [ { "type": "respond", "message": "ok" } ],
  "else": [ { "type": "respond", "message": "faltam pontos" } ]
}
```

Notas:
- Use `{username}` em strings para referenciar o usuário chamador em tempo de execução.
- O plugin gerado retorna as mensagens de "respond" concatenadas como resposta do comando.
- Todas as ações mapeiam para métodos seguros de `PluginContext` (sem acesso direto ao bot, sem tenant_id).

## Permissões

Use os mesmos nomes de permissões da API segura:
- core:log, chat:send, points:read/write, voting:read/vote/manage,
  audio:play/tts/control, minigames:play, leaderboard:read, macro:enqueue

## Limitações e próximos passos
- Esta v0 é baseada em sequência (não é um grafo completo). É propositalmente simples.
- Planejado: editor visual (drag-nodes), variáveis/estado, timers/loops, tratamento de erros, mais condições e publicação direta no marketplace.

## Segurança
- O compilador só gera código que usa métodos permitidos do PluginContext.
- O sandbox continua aplicando isolamento, timeouts e allowlists em tempo de execução.
