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
- 🎨 **Visual Blueprints** - Editor visual estilo Unreal Engine
- 🧪 **Testing Tools** - Teste localmente antes de publicar
- 📦 **Easy Publishing** - Publique no Marketplace

## 🎨 Blueprint Editor - Crie Plugins Sem Código!

O SDK inclui um **editor visual de blueprints** inspirado no Unreal Engine.
Crie plugins arrastando e conectando blocos, sem escrever uma linha de código!

### Features do Blueprint Editor

- 🔗 **Node Graph** - Conecte blocos visualmente
- ⚡ **Compilação Inteligente** - Gera código Python otimizado
- ✅ **Validação em Tempo Real** - Detecta erros enquanto cria
- 🎯 **Ações Prontas** - Chat, TTS, Pontos, Macros e mais
- 📤 **Exportar** - Baixe o plugin pronto para usar

### Usar o Blueprint Editor

```bash
# Iniciar o editor visual
python -m chaos_sdk.blueprints.api

# Acesse no navegador
# http://localhost:8080
```

### Exemplo de Blueprint (JSON)

```json
{
  "name": "MeuPlugin",
  "version": "1.0.0",
  "author": "SeuNome",
  "description": "Plugin criado com blueprints",
  "permissions": ["chat:send", "audio:tts"],
  "commands": {
    "ola": [
      {"type": "respond", "message": "Olá, {username}!"},
      {"type": "audio_tts", "text": "Bem-vindo!"}
    ]
  }
}
```

### Compilar Blueprint para Python

```python
from chaos_sdk.blueprints import compile_blueprint_secure

# Carregar blueprint JSON
with open("meu_plugin.json") as f:
    blueprint = json.load(f)

# Compilar com validação de segurança
result = compile_blueprint_secure(blueprint)

if result.success:
    print(f"✅ Compilado! Hash: {result.security_hash}")
    print(result.code)  # Código Python gerado
    
    # Salvar plugin
    with open("meu_plugin.py", "w") as f:
        f.write(result.code)
else:
    print("❌ Falha na compilação:")
    for msg in result.messages:
        print(f"  [{msg.severity.value}] {msg.message}")
```

> ⚠️ **Sempre use `compile_blueprint_secure`** em produção!
> Ele valida inputs e previne code injection.

## 🚀 Quick Start - Código Python

### Instalação

```bash
pip install chaos-sdk
# ou
pip install -e .
```

### Criar Plugin com Código

```python
from chaos_sdk import Plugin, command

class MeuPlugin(Plugin):
    name = "Meu Plugin"
    version = "1.0.0"
    author = "SeuNome"
    description = "Meu primeiro plugin"
    required_permissions = ["chat:send"]
    
    def on_load(self):
        self.register_command("ola", self.cmd_ola)
    
    def cmd_ola(self, username, args, **kwargs):
        return f"Olá, {username}!"
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
- [Referência de Blocos](blueprints/BLOCKS_REFERENCE.md)
- [Exemplos](examples/)

## 📁 Estrutura

```text
chaos-sdk/
├── chaos_sdk/           # SDK principal
│   ├── core/           # Classes base (Plugin, Command, etc)
│   ├── blueprints/     # Compiladores de blueprints
│   │   ├── compiler.py     # v1 - Legacy
│   │   ├── compiler_v2.py  # v2 - Graph-based
│   │   ├── compiler_v3.py  # v3 - Secure (RECOMENDADO)
│   │   └── SECURITY.md     # Guia de segurança
│   ├── decorators/     # @command, @cooldown, etc
│   ├── models/         # Contexto, User, etc
│   └── testing/        # Ferramentas de teste
├── blueprints/         # Editor visual HTML
│   ├── actions_meta.json
│   └── ...
├── web/                # Blueprint Editor UI
├── examples/           # Exemplos de plugins
└── templates/          # Templates para novos projetos
```

## 🎮 Tipos de Plugin

### BasePlugin
Plugin básico com comandos e hooks.

### GamePlugin
Para jogos que precisam de controle de teclado/mouse.

```python
class MeuJogo(GamePlugin):
    def cmd_pular(self, username, args, **kwargs):
        self.press_key("SPACE")
        return f"{username} pulou!"
```

### IntegrationPlugin
Para integrações externas (OBS, Discord, etc).

### CommandPlugin
Plugin simples focado em comandos com cooldown.

## 🔐 Permissões Disponíveis

| Permissão | Descrição |
|-----------|-----------|
| `core:log` | Registrar logs (padrão) |
| `chat:send` | Enviar mensagens no chat |
| `points:read` | Consultar pontos |
| `points:write` | Adicionar/remover pontos |
| `audio:tts` | Usar texto-para-fala |
| `audio:play` | Tocar sons |
| `macro:enqueue` | Executar teclas/macros |
| `voting:manage` | Criar/encerrar votações |

## 📄 Licença

MIT License - veja [LICENSE](LICENSE)

---

<p align="center">
  Feito com ❤️ para criadores de conteúdo
</p>
