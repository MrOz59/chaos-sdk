# 🔧 Chaos Factory - SDK

<p align="center">
  <strong>SDK para Desenvolvimento de Plugins</strong><br>
  Crie plugins e jogos para a plataforma Chaos Factory
</p>

<p align="center">
  <a href="README.en.md">English</a> •
  <a href="README.pt-BR.md">Português</a>
</p>

---

## ✨ Features

- 🎮 **Game Development** - Crie jogos interativos para lives
- 🔌 **Plugin System** - Estenda funcionalidades do servidor
- 🎨 **Blueprints** - Editor visual de lógica
- 🧪 **Testing Tools** - Teste localmente antes de publicar
- 📦 **Easy Publishing** - Publique no Marketplace

## 🚀 Quick Start

### Instalação

```bash
pip install chaos-sdk
# ou
pip install -e .
```

### Criar Plugin

```python
from chaos_sdk import Plugin, command, event

class MeuPlugin(Plugin):
    name = "Meu Plugin"
    version = "1.0.0"
    
    @command("!ola")
    async def hello(self, ctx):
        await ctx.reply(f"Olá {ctx.user}!")
    
    @event("on_subscribe")
    async def on_sub(self, event):
        await event.send_tts(f"Obrigado pelo sub {event.user}!")
```

### Testar Localmente

```bash
python -m chaos_sdk.cli run meu_plugin.py
```

### Publicar

```bash
python -m chaos_sdk.cli publish meu_plugin.py
```

## 📖 Documentação

- [Guia Completo (PT-BR)](README.pt-BR.md)
- [Full Guide (English)](README.en.md)
- [API Reference](docs/)
- [Exemplos](examples/)

## 📁 Estrutura

```
chaos-sdk/
├── chaos_sdk/           # SDK principal
│   ├── core/           # Classes base
│   ├── decorators/     # @command, @event, etc
│   ├── models/         # Modelos de dados
│   └── testing/        # Ferramentas de teste
├── blueprints/         # Sistema de blueprints visual
├── examples/           # Exemplos de plugins
├── templates/          # Templates para novos projetos
└── docs/               # Documentação
```

## 🎮 Exemplos

### Comando Simples

```python
@command("!pontos")
async def pontos(self, ctx):
    user_points = await self.db.get_points(ctx.user_id)
    await ctx.reply(f"Você tem {user_points} pontos!")
```

### Evento de Chat

```python
@event("on_message")
async def on_msg(self, event):
    if "gg" in event.message.lower():
        await event.react("🎉")
```

### Jogo Interativo

```python
@command("!rolar")
async def rolar_dado(self, ctx):
    numero = random.randint(1, 6)
    await ctx.reply(f"🎲 {ctx.user} rolou {numero}!")
    
    if numero == 6:
        await self.db.add_points(ctx.user_id, 100)
        await ctx.reply("Crítico! +100 pontos!")
```

## 📄 Licença

MIT License - veja [LICENSE](LICENSE)

---

<p align="center">
  Feito com ❤️ para criadores de conteúdo
</p>
