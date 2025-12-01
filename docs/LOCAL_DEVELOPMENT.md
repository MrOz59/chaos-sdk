# 🛠️ Desenvolvimento Local - Chaos SDK

> Guia completo para desenvolver e testar plugins e mods localmente, sem depender do servidor de produção.

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Instalação](#instalação)
3. [Comandos CLI](#comandos-cli)
4. [Modo Interativo](#modo-interativo)
5. [Testes Automatizados](#testes-automatizados)
6. [Testando Mods](#testando-mods)
7. [Mock de Eventos](#mock-de-eventos)
8. [API de Desenvolvimento](#api-de-desenvolvimento)
9. [Debugging](#debugging)
10. [Boas Práticas](#boas-práticas)

---

## 🎯 Visão Geral

O ambiente de desenvolvimento local permite:

- ✅ **Testar plugins** sem cadastrar no marketplace
- ✅ **Simular chat** do Twitch/Kick
- ✅ **Simular eventos** (subs, bits, raids)
- ✅ **Testar mods** de jogos localmente
- ✅ **Debugging** completo com breakpoints
- ✅ **Testes automatizados** unitários e de integração

### Fluxo de Desenvolvimento

```
┌──────────────────────────────────────────────────────────────┐
│                    DESENVOLVIMENTO LOCAL                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  [Seu IDE]                     [Terminal]                     │
│      │                             │                          │
│      ▼                             ▼                          │
│  plugin.py  ───────────────►  chaos-dev run                   │
│      │                             │                          │
│      │                             ▼                          │
│      │                    [Modo Interativo]                   │
│      │                        !hello                          │
│      │                        !gamble 100                     │
│      │                             │                          │
│      ▼                             ▼                          │
│  test_plugin.py ──────────►  chaos-dev test                   │
│                                    │                          │
│                                    ▼                          │
│                            [Testes Passando]                  │
│                                    │                          │
└────────────────────────────────────┼──────────────────────────┘
                                     │
                                     ▼
                          [Publicar no Marketplace]
```

---

## 📦 Instalação

### Instalar o SDK

```bash
pip install chaos-sdk

# Ou com extras de desenvolvimento
pip install chaos-sdk[dev]
```

### Verificar instalação

```bash
chaos-dev --help
```

---

## 💻 Comandos CLI

### `chaos-dev run` - Modo Interativo

Roda seu plugin em um ambiente simulado interativo.

```bash
chaos-dev run meu_plugin.py
```

**Opções:**
- `--port PORT` - Porta do WebSocket (default: 8765)

**Exemplo:**
```
$ chaos-dev run hello_plugin.py

🎮 Chaos Dev Server - Modo Interativo
==================================================
✅ Plugin carregado: HelloPlugin
✅ Plugin ativo: Hello World v1.0.0
📋 Comandos: hello, points, give
🔌 Mod WebSocket: ws://localhost:8765/mod
--------------------------------------------------
Digite comandos como: !comando arg1 arg2
Comandos especiais:
  /user <nome>     - Mudar usuário atual
  /mod             - Ativar modo mod
  /sub             - Ativar modo sub
  /points <n>      - Definir pontos
  /event <tipo>    - Simular evento do mod
  /help            - Ajuda
  /quit            - Sair
--------------------------------------------------

[viewer1] > !hello
💬 Olá, viewer1! 👋

[viewer1] > /user streamer
👤 Usuário: streamer

[streamer] > !hello viewer1
💬 Olá, viewer1! 👋
```

### `chaos-dev test` - Testes Automatizados

Roda testes automáticos no plugin.

```bash
chaos-dev test meu_plugin.py
```

**Opções:**
- `-v, --verbose` - Saída detalhada

### `chaos-dev server` - Servidor Completo

Inicia servidor de desenvolvimento com múltiplos plugins.

```bash
chaos-dev server --plugin plugin1.py --plugin plugin2.py
```

### `chaos-dev chat` - Simulador de Chat

Simula chat interativo para testes.

```bash
chaos-dev chat
```

---

## 🎮 Modo Interativo

### Comandos Especiais

| Comando | Descrição |
|---------|-----------|
| `/user <nome>` | Mudar usuário atual |
| `/mod` | Tornar usuário atual mod |
| `/sub` | Tornar usuário atual subscriber |
| `/vip` | Tornar usuário atual VIP |
| `/points <n>` | Definir pontos do usuário |
| `/event <tipo> [json]` | Simular evento de mod |
| `/help` | Mostrar ajuda |
| `/quit` | Sair |

### Exemplo de Sessão

```
[viewer1] > !points
💬 viewer1, você tem 1000 pontos!

[viewer1] > /points 5000
💰 Pontos: 5000

[viewer1] > !gamble 1000
💬 🎉 viewer1 ganhou! +1000 pontos (total: 6000)!

[viewer1] > /user mod_user
👤 Usuário: mod_user

[mod_user] > /mod
🛡️ mod_user agora é mod

[mod_user] > !setgreeting Eae
✅ Saudação alterada para: Eae
```

---

## 🧪 Testes Automatizados

### Estrutura de Testes

```python
from chaos_sdk.testing import PluginTestCase

class TestMyPlugin(PluginTestCase):
    plugin_class = MyPlugin
    
    def test_hello_command(self):
        result = self.execute_command("hello", "viewer1", [])
        self.assertContains(result, "Olá")
    
    def test_points_transfer(self):
        self.set_points("viewer1", 100)
        self.set_points("viewer2", 0)
        
        self.execute_command("give", "viewer1", ["viewer2", "50"])
        
        self.assertEqual(self.get_points("viewer1"), 50)
        self.assertEqual(self.get_points("viewer2"), 50)
```

### Helpers Disponíveis

```python
# Executar comandos
result = self.execute_command("cmd", "user", ["arg1", "arg2"])

# Gerenciar usuários
user = self.create_user("viewer1", is_mod=True, points=1000)
self.set_points("viewer1", 500)
points = self.get_points("viewer1")

# Gerenciar variáveis
self.set_variable("counter", 42)
value = self.get_variable("counter")

# Verificar chat
log = self.get_chat_log()
self.clear_chat_log()
```

### Assertions Especiais

```python
# Texto contém substring
self.assertContains(result, "sucesso")
self.assertNotContains(result, "erro")

# Chat contém mensagem
self.assertChatContains("Olá")

# Comando existe
self.assertCommandExists("hello")
self.assertCommandNotExists("admin_secret")
```

### Rodar Testes

```bash
# Via CLI
chaos-dev test meu_plugin.py

# Via pytest
pytest tests/test_meu_plugin.py -v

# Via Python
python -m pytest tests/
```

---

## 🎮 Testando Mods

### ModTestCase

Para plugins que usam integração com mods de jogos:

```python
from chaos_sdk.testing import ModTestCase

class TestMinecraftPlugin(ModTestCase):
    plugin_class = MinecraftChaosPlugin
    game_id = "minecraft"
    
    def test_spawn_command(self):
        result = self.execute_command("spawn", "viewer1", ["zombie", "5"])
        
        # Verificar que comando foi enviado ao mod
        self.assertModReceivedCommand("spawn_entity", {
            "type": "zombie",
            "count": 5
        })
    
    def test_player_death_event(self):
        # Simular evento vindo do mod
        result = self.simulate_event("player_died", {
            "player": "Steve",
            "cause": "zombie"
        })
        
        self.assertContains(result, "Steve")
```

### Conectar Mod de Teste

Durante desenvolvimento, você pode conectar um mod real ou simulado:

```python
import websockets
import json
import asyncio

async def test_mod():
    async with websockets.connect("ws://localhost:8765/mod") as ws:
        # Registrar
        await ws.send(json.dumps({
            "type": "register",
            "mod_id": "minecraft_mod_1",
            "game_id": "minecraft",
            "mod_name": "Test Mod",
            "version": "1.0.0"
        }))
        
        # Enviar evento
        await ws.send(json.dumps({
            "type": "event",
            "event_type": "player_died",
            "data": {"player": "Steve", "cause": "creeper"}
        }))
        
        # Receber comandos
        async for msg in ws:
            data = json.loads(msg)
            print(f"Comando recebido: {data}")

asyncio.run(test_mod())
```

---

## 📨 Mock de Eventos

### Eventos de Chat

```python
# No modo interativo
[viewer1] > /event follow {"username": "novo_follower"}
📨 Simulando evento: follow

# Programaticamente
server.simulate_event("follow", {"username": "novo_follower"})
server.simulate_event("subscription", {"username": "novo_sub", "tier": 1})
server.simulate_event("bits", {"username": "donor", "amount": 100})
server.simulate_event("raid", {"from": "outro_streamer", "viewers": 50})
```

### Eventos de Mod

```python
# Simular evento do jogo
server.simulate_mod_event("minecraft", "player_died", {
    "player": "Steve",
    "cause": "zombie",
    "location": {"x": 100, "y": 64, "z": -200}
})

# Simular achievement
server.simulate_mod_event("minecraft", "achievement", {
    "player": "Steve",
    "achievement": "diamonds"
})
```

---

## 🔧 API de Desenvolvimento

### LocalDevServer

```python
from chaos_sdk.testing import LocalDevServer

# Criar servidor
server = LocalDevServer(port=8765)

# Carregar plugin
plugin = server.load_plugin(MyPlugin)

# Simular comando
result = server.simulate_command("hello", "viewer1", ["arg"])

# Simular evento
server.simulate_event("subscription", {"username": "sub1"})

# Conectar mod simulado
mod = server.create_mod("minecraft", "Test Mod")
mod.send_event("player_died", {"player": "Steve"})

# Rodar servidor async
await server.start_async()
```

### MockContext

```python
from chaos_sdk.testing import MockContext

ctx = MockContext()

# Pontos
ctx.set_points("user1", 1000)
points = ctx.get_points("user1")
ctx.add_points("user1", 100)
ctx.remove_points("user1", 50)

# Variáveis
ctx.set_variable("counter", 0)
value = ctx.get_variable("counter")

# Chat
ctx.send_chat("Mensagem!")
log = ctx.get_chat_log()

# Cooldowns
ctx.set_cooldown("cmd", "user", 10)
if ctx.is_on_cooldown("cmd", "user"):
    print("Em cooldown!")
```

---

## 🐛 Debugging

### Com VS Code

1. Crie um arquivo `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Plugin",
            "type": "python",
            "request": "launch",
            "module": "chaos_sdk.testing.dev_cli",
            "args": ["run", "${file}"],
            "console": "integratedTerminal"
        }
    ]
}
```

2. Abra seu plugin e pressione F5

### Com breakpoints

```python
def cmd_debug(self, username: str, args: list):
    # Adicione breakpoint aqui
    import pdb; pdb.set_trace()
    
    # Ou use o VS Code debugger
    resultado = self.processar(args)
    return resultado
```

### Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MyPlugin(ChaosPlugin):
    def cmd_test(self, username, args):
        logger.debug(f"Comando test de {username} com args: {args}")
        # ...
```

---

## ✅ Boas Práticas

### 1. Estrutura de Projeto

```
meu_plugin/
├── meu_plugin.py          # Plugin principal
├── tests/
│   ├── test_comandos.py   # Testes de comandos
│   └── test_integracao.py # Testes de integração
├── README.md              # Documentação
└── requirements.txt       # Dependências
```

### 2. Teste Antes de Publicar

```bash
# Rodar testes
chaos-dev test meu_plugin.py -v

# Testar interativamente
chaos-dev run meu_plugin.py

# Verificar com múltiplos usuários
/user viewer1
!comando
/user viewer2
!comando
```

### 3. Cobrir Casos de Erro

```python
def test_give_insufficient_points(self):
    self.set_points("viewer1", 10)
    result = self.execute_command("give", "viewer1", ["viewer2", "100"])
    self.assertContains(result, "❌")

def test_give_negative_amount(self):
    result = self.execute_command("give", "viewer1", ["viewer2", "-50"])
    self.assertContains(result, "❌")

def test_give_invalid_amount(self):
    result = self.execute_command("give", "viewer1", ["viewer2", "abc"])
    self.assertContains(result, "❌")
```

### 4. Testar Permissões

```python
def test_mod_only_command(self):
    # Sem ser mod
    result = self.execute_command("ban", "viewer1", ["bad_user"])
    self.assertContains(result, "permissão")
    
    # Como mod
    self.create_user("mod_user", is_mod=True)
    result = self.execute_command("ban", "mod_user", ["bad_user"])
    self.assertContains(result, "banido")
```

### 5. Workflow Completo

```bash
# 1. Desenvolver
vim meu_plugin.py

# 2. Testar interativamente
chaos-dev run meu_plugin.py

# 3. Criar testes
vim tests/test_meu_plugin.py

# 4. Rodar testes
chaos-dev test meu_plugin.py -v

# 5. Testar com mod (se aplicável)
chaos-dev server --plugin meu_plugin.py
# Em outro terminal: conectar mod de teste

# 6. Publicar no marketplace
chaos-sdk publish meu_plugin.py
```

---

## 🆘 Problemas Comuns

### "Plugin não encontrado"

Verifique se seu plugin herda de `ChaosPlugin`:

```python
from chaos_sdk import ChaosPlugin

class MyPlugin(ChaosPlugin):  # ✅ Correto
    ...
```

### "Comando não existe"

Comandos devem começar com `cmd_`:

```python
def cmd_hello(self, username, args):  # ✅ Correto
    ...

def hello(self, username, args):  # ❌ Não será reconhecido
    ...
```

### "Pontos não persistem"

O MockContext não persiste entre sessões. Para testes, use `setUp`:

```python
def setUp(self):
    super().setUp()
    self.set_points("viewer1", 1000)
    self.set_points("viewer2", 500)
```

### "Mod não conecta"

Verifique se o servidor está rodando e a porta está correta:

```bash
chaos-dev server --port 8765
# WebSocket: ws://localhost:8765/mod
```

---

## 📚 Próximos Passos

1. 📖 Leia a [documentação de plugins](/docs/PLUGINS.md)
2. 🎮 Explore [integração com mods](/docs/MOD_INTEGRATION.md)
3. 📦 Publique no [marketplace](/docs/MARKETPLACE.md)
4. 💬 Entre na [comunidade Discord](https://discord.gg/chaos)

---

*Chaos SDK - Desenvolvido com ❤️ pela comunidade*
