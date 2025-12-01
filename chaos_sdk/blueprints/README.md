# Blueprint Visual Editor System

Sistema de editor visual de plugins estilo Unreal Engine Blueprints.

## Estrutura

```
chaos_sdk/blueprints/
├── __init__.py          # Exports do módulo
├── compiler.py          # Compilador original (step-based)
├── compiler_v2.py       # Compilador v2 com resolução de grafos
├── api.py              # Rotas FastAPI para o editor
├── base_stub.py        # Plugin stub para modo standalone
├── actions_meta.json   # Metadados das ações disponíveis
├── node_templates.json # Templates visuais de nós
└── user/               # Blueprints salvos pelo usuário

web/
├── blueprints_visual.html  # Interface do editor
└── blueprint_visual.js     # Lógica JavaScript do editor
```

## Recursos

### Editor Visual
- **Drag & Drop**: Arraste nós da paleta para o canvas
- **Conexões**: Arraste entre pinos para conectar nós
- **Pan/Zoom**: Middle mouse ou Shift+drag para mover, scroll para zoom
- **Multi-seleção**: Ctrl+A seleciona todos
- **Undo/Redo**: Ctrl+Z / Ctrl+Y
- **Copy/Paste**: Ctrl+C / Ctrl+V
- **Duplicate**: Ctrl+D
- **Delete**: Delete ou Backspace
- **Frame**: F para centralizar na seleção

### Compilador v2
- Resolução inteligente de nós puros (data nodes)
- Suporte a 60+ tipos de ações
- Geração de código otimizado
- Validação de permissões
- Modo standalone para testes

## Uso

### Python

```python
from chaos_sdk.blueprints import compile_blueprint_v2

blueprint = {
    "name": "MeuPlugin",
    "version": "1.0.0",
    "author": "Eu",
    "description": "Meu plugin visual",
    "commands": {
        "hello": {
            "nodes": [...],
            "connections": [...]
        }
    }
}

result = compile_blueprint_v2(blueprint, standalone=True)
if result.success:
    print(result.code)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from chaos_sdk.blueprints.api import router as blueprint_router

app = FastAPI()
app.include_router(blueprint_router)
```

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/blueprints/actions` | Lista todas as ações disponíveis |
| GET | `/api/blueprints/actions/categories` | Ações agrupadas por categoria |
| POST | `/api/blueprints/validate` | Valida estrutura do blueprint |
| POST | `/api/blueprints/validate/visual` | Validação detalhada com warnings |
| POST | `/api/blueprints/compile` | Compila para Python |
| POST | `/api/blueprints/save` | Salva blueprint |
| GET | `/api/blueprints/load` | Carrega blueprint |
| GET | `/api/blueprints/list` | Lista blueprints salvos |
| DELETE | `/api/blueprints/delete` | Remove blueprint |
| POST | `/api/blueprints/duplicate` | Duplica blueprint |
| POST | `/api/blueprints/export/plugin` | Exporta como arquivo .py |

## Categorias de Nós

- **Events**: Pontos de entrada (On Command, On Chat, etc)
- **Actions**: Ações de execução (Send Message, Press Key, etc)
- **Flow Control**: Controle de fluxo (Branch, Loop, Delay)
- **Data**: Manipulação de dados (Variables, Constants)
- **Math**: Operações matemáticas
- **String**: Manipulação de texto
- **Array**: Operações com listas
- **User**: Operações com usuários (Points, etc)
- **Audio**: Controle de áudio (TTS, Sound)
- **Voting**: Sistema de votação

## Permissões

O compilador detecta automaticamente as permissões necessárias com base nos nós usados:

- `chat:send` - Envio de mensagens
- `points:read` - Leitura de pontos
- `points:write` - Modificação de pontos
- `audio:tts` - Text-to-speech
- `audio:play` - Reprodução de áudio
- `voting:manage` - Gerenciamento de votações
- `input:keyboard` - Controle de teclado
- E mais...
