# 🔒 Chaos Blueprint Compiler - Security Guide

## Overview

O Chaos Blueprint Compiler v3 é um compilador seguro que transforma blueprints visuais (estilo Unreal Engine) em código Python executável. Esta versão inclui múltiplas camadas de segurança para prevenir exploits.

## Versões do Compilador

| Versão | Status | Uso |
|--------|--------|-----|
| v1 (`compiler.py`) | Legacy | Apenas para compatibilidade |
| v2 (`compiler_v2.py`) | Estável | Recursos avançados, menos segurança |
| v3 (`compiler_v3.py`) | **Recomendado** | Segurança total + AST validation |

## Segurança

### Camadas de Proteção

```
┌─────────────────────────────────────────────────────┐
│                Blueprint JSON Input                  │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  1. Input Sanitization (SecurityValidator)          │
│     - String length limits                          │
│     - Dangerous pattern detection (40+ patterns)    │
│     - Null byte detection                           │
│     - Identifier validation                         │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  2. Safe Code Generation (SecureCodeEmitter)        │
│     - Whitelist of allowed actions                  │
│     - String escaping                               │
│     - Number sanitization                           │
│     - Identifier normalization                      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  3. AST Validation (ASTValidator)                   │
│     - Parse tree analysis                           │
│     - Forbidden node detection                      │
│     - Import whitelist check                        │
│     - Dangerous call detection                      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  4. Output with Security Hash                       │
│     - SHA-256 code fingerprint                      │
│     - Permission manifest                           │
│     - Compilation metadata                          │
└─────────────────────────────────────────────────────┘
```

### Padrões Bloqueados

O compilador detecta e bloqueia automaticamente:

```python
# Code Injection
eval("...")          # ❌ Blocked
exec("...")          # ❌ Blocked
compile("...")       # ❌ Blocked
__import__("...")    # ❌ Blocked

# File System
open("/etc/passwd")  # ❌ Blocked
os.system("...")     # ❌ Blocked
subprocess.call(...) # ❌ Blocked

# Reflection
getattr(obj, "...")  # ❌ Blocked
setattr(obj, ...)    # ❌ Blocked
globals()            # ❌ Blocked
locals()             # ❌ Blocked

# Dunder Access
obj.__class__        # ❌ Blocked
obj.__bases__        # ❌ Blocked
__init__             # ❌ Blocked as variable name
```

### Limites de Segurança

| Limite | Valor | Razão |
|--------|-------|-------|
| Max Commands | 50 | Prevenir complexidade excessiva |
| Max Steps/Command | 100 | Prevenir loops infinitos |
| Max Nodes/Command | 200 | Limitar consumo de memória |
| Max Connections | 500 | Limitar complexidade do grafo |
| Max String Length | 1000 | Prevenir memory exhaustion |
| Max Delay | 30s | Prevenir abuse de recursos |
| Max Identifier | 50 chars | Sanidade |
| Max Nesting | 10 levels | Prevenir stack overflow |

## Uso

### Importação Recomendada

```python
from chaos_sdk.blueprints import compile_blueprint_secure

# ou
from chaos_sdk.blueprints.compiler_v3 import (
    compile_blueprint_secure,
    CompilationResult,
    Severity
)
```

### Compilação Básica

```python
blueprint = {
    "name": "My Plugin",
    "version": "1.0.0",
    "author": "Developer",
    "description": "Plugin description",
    "commands": {
        "hello": [
            {"type": "respond", "message": "Hello {username}!"}
        ]
    }
}

result = compile_blueprint_secure(blueprint)

if result.success:
    print(f"✅ Compiled successfully")
    print(f"   Hash: {result.security_hash}")
    print(f"   Lines: {result.stats['code_lines']}")
    print(f"   Permissions: {result.stats['permissions']}")
    
    # Save to file
    with open("my_plugin.py", "w") as f:
        f.write(result.code)
else:
    print("❌ Compilation failed:")
    for msg in result.messages:
        if msg.severity in (Severity.ERROR, Severity.SECURITY):
            print(f"   [{msg.severity.value}] {msg.message}")
```

### Verificar Segurança de Input

```python
from chaos_sdk.blueprints import SecurityValidator, Severity

# Validate a string
messages = SecurityValidator.validate_string(user_input, "user message")

# Check for security issues
has_security_issues = any(
    m.severity == Severity.SECURITY 
    for m in messages
)

if has_security_issues:
    print("⚠️ Input contains dangerous patterns!")
```

### Validar Código Gerado

```python
from chaos_sdk.blueprints import ASTValidator

code = """
def hello():
    print("Hello world")
"""

messages = ASTValidator.validate_code(code)

for msg in messages:
    print(f"[{msg.severity.value}] {msg.message}")
```

## Tipos de Ação Suportados

### Chat & Response
- `respond` - Resposta direta ao comando
- `chat_send` - Enviar mensagem no chat

### Audio
- `audio_tts` - Text-to-speech
- `audio_play` - Tocar áudio
- `audio_stop` - Parar áudio
- `audio_clear` - Limpar fila

### Points
- `points_add` - Adicionar pontos
- `points_remove` - Remover pontos
- `leaderboard` - Mostrar ranking

### Variables
- `variable_set` - Definir variável
- `variable_increment` - Incrementar contador

### Control Flow
- `delay` - Aguardar (max 30s)
- `if_points_at_least` - Condição de pontos

### Macros
- `macro_run_keys` - Executar teclas

## Resultado da Compilação

```python
@dataclass
class CompilationResult:
    success: bool           # Se compilou com sucesso
    code: str              # Código Python gerado
    messages: List[...]    # Mensagens (erros, warnings)
    stats: Dict[...]       # Estatísticas
    security_hash: str     # Hash SHA-256 do código
```

### Severidades

| Severity | Código | Descrição |
|----------|--------|-----------|
| `ERROR` | AST001+ | Erros que impedem compilação |
| `SECURITY` | SEC001+ | Problemas de segurança |
| `WARNING` | - | Avisos que não bloqueiam |
| `INFO` | - | Informações úteis |

## CLI

```bash
# Compilar blueprint
python -m chaos_sdk.blueprints.compiler_v3 input.json output.py

# Com nome de classe customizado
python -m chaos_sdk.blueprints.compiler_v3 input.json output.py --class MyPlugin
```

## Best Practices

### DO ✅

```python
# Usar compile_blueprint_secure em produção
result = compile_blueprint_secure(bp)

# Sempre verificar success
if not result.success:
    handle_error(result.messages)

# Armazenar security_hash para auditoria
log_compilation(bp_id, result.security_hash)
```

### DON'T ❌

```python
# Não confiar em inputs não validados
user_input = request.json  # ❌ Pode conter exploits

# Não ignorar mensagens de segurança
for msg in result.messages:
    if msg.severity == Severity.SECURITY:
        # ❌ Não ignore isso!
        pass

# Não usar exec() no código gerado
exec(result.code)  # ❌ O código já é seguro,
                   # mas exec() sempre é arriscado
```

## Roadmap de Segurança

- [ ] Sandboxed execution environment
- [ ] Rate limiting na compilação
- [ ] Plugin signature verification
- [ ] Audit logging completo
- [ ] Static analysis integration (bandit, semgrep)

## Contribuindo

Para reportar vulnerabilidades de segurança, entre em contato privado:
- **Email**: security@chaoslive.dev
- **Não abra issues públicas** para vulnerabilidades!

---

*Blueprint Compiler v3.0 - Secure by Design*
