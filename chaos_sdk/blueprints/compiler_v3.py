"""
Blueprint Compiler v3.0 - Secure & Robust Code Generator
=========================================================

Compilador seguro com:
- Sanitização rigorosa de inputs
- Validação AST do código gerado
- Prevenção de code injection
- Whitelist de operações permitidas
- Detecção de padrões perigosos
- Limite de complexidade

Usage:
  from chaos_sdk.blueprints.compiler_v3 import compile_blueprint_secure
  result = compile_blueprint_secure(blueprint_json)
"""
from __future__ import annotations

import ast
import json
import re
import sys
from typing import Dict, Any, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib

# ============================================================================
# Constants & Configuration
# ============================================================================

MAX_COMMANDS = 50
MAX_STEPS_PER_COMMAND = 100
MAX_NODES_PER_COMMAND = 200
MAX_CONNECTIONS = 500
MAX_STRING_LENGTH = 1000
MAX_NESTING_DEPTH = 10
MAX_VARIABLE_NAME_LENGTH = 50

# Dangerous patterns to block
DANGEROUS_PATTERNS = [
    r'__\w+__',           # Dunder methods
    r'eval\s*\(',         # eval()
    r'exec\s*\(',         # exec()
    r'compile\s*\(',      # compile()
    r'open\s*\(',         # open()
    r'import\s+',         # import statements
    r'__import__',        # __import__
    r'globals\s*\(',      # globals()
    r'locals\s*\(',       # locals()
    r'getattr\s*\(',      # getattr()
    r'setattr\s*\(',      # setattr()
    r'delattr\s*\(',      # delattr()
    r'hasattr\s*\(',      # hasattr() - can be used for probing
    r'vars\s*\(\s*\)',    # vars() without argument
    r'dir\s*\(',          # dir()
    r'type\s*\(',         # type()
    r'isinstance\s*\(',   # can be used to probe
    r'issubclass\s*\(',   # can be used to probe
    r'callable\s*\(',     # callable()
    r'classmethod',       # classmethod
    r'staticmethod',      # staticmethod
    r'property\s*\(',     # property
    r'super\s*\(',        # super()
    r'lambda\s+',         # lambda expressions
    r'yield\s+',          # generators
    r'async\s+',          # async (should not be in user code)
    r'await\s+',          # await (should not be in user code)
    r'\bos\.',            # os module access
    r'\bsys\.',           # sys module access
    r'\bsubprocess\.',    # subprocess
    r'\bshutil\.',        # shutil
    r'\bpickle\.',        # pickle
    r'\bsocket\.',        # socket
    r'\brequests\.',      # requests
    r'\burllib\.',        # urllib
    r'\bhttp\.',          # http
    r'\.read\s*\(',       # file read
    r'\.write\s*\(',      # file write
    r'\.execute\s*\(',    # SQL execute
    r'\bshell\s*=',       # shell=True
    r'\\x[0-9a-fA-F]',    # hex escapes
    r'\\u[0-9a-fA-F]',    # unicode escapes
]

# Allowed built-in functions in generated code
ALLOWED_BUILTINS = {
    'str', 'int', 'float', 'bool', 'len', 'range', 'min', 'max', 
    'abs', 'round', 'sum', 'sorted', 'list', 'dict', 'tuple', 'set',
    'enumerate', 'zip', 'map', 'filter', 'any', 'all', 'print',
}

# Safe modules that can be imported
SAFE_MODULES = {'random', 'time', 'datetime', 'math', 're', 'json'}


# ============================================================================
# Result Types
# ============================================================================

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SECURITY = "security"


@dataclass
class CompilerMessage:
    severity: Severity
    message: str
    location: str = ""
    suggestion: str = ""
    code: str = ""


@dataclass
class CompilationResult:
    success: bool
    code: str = ""
    messages: List[CompilerMessage] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    security_hash: str = ""  # Hash of generated code for verification


# ============================================================================
# Security Validators
# ============================================================================

class SecurityValidator:
    """Validates inputs for security issues."""
    
    @staticmethod
    def validate_string(value: str, context: str = "") -> List[CompilerMessage]:
        """Validate a string value for dangerous patterns."""
        messages = []
        
        if not isinstance(value, str):
            return messages
        
        # Check length
        if len(value) > MAX_STRING_LENGTH:
            messages.append(CompilerMessage(
                Severity.SECURITY,
                f"String too long ({len(value)} chars, max {MAX_STRING_LENGTH})",
                location=context,
                code="SEC001"
            ))
        
        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                messages.append(CompilerMessage(
                    Severity.SECURITY,
                    f"Potentially dangerous pattern detected: {pattern}",
                    location=context,
                    suggestion="Remove or sanitize this input",
                    code="SEC002"
                ))
        
        # Check for null bytes
        if '\x00' in value:
            messages.append(CompilerMessage(
                Severity.SECURITY,
                "Null byte detected in string",
                location=context,
                code="SEC003"
            ))
        
        return messages
    
    @staticmethod
    def validate_identifier(name: str, context: str = "") -> List[CompilerMessage]:
        """Validate an identifier (variable/function name)."""
        messages = []
        
        if not isinstance(name, str):
            messages.append(CompilerMessage(
                Severity.ERROR,
                "Identifier must be a string",
                location=context
            ))
            return messages
        
        if len(name) > MAX_VARIABLE_NAME_LENGTH:
            messages.append(CompilerMessage(
                Severity.ERROR,
                f"Identifier too long ({len(name)} chars)",
                location=context
            ))
        
        # Must be valid Python identifier
        if not name.isidentifier():
            messages.append(CompilerMessage(
                Severity.ERROR,
                f"Invalid identifier: {name}",
                location=context,
                suggestion="Use only letters, numbers, and underscores"
            ))
        
        # No dunders
        if name.startswith('__') or name.endswith('__'):
            messages.append(CompilerMessage(
                Severity.SECURITY,
                f"Dunder identifiers not allowed: {name}",
                location=context,
                code="SEC004"
            ))
        
        # No Python keywords/builtins
        import keyword
        if keyword.iskeyword(name):
            messages.append(CompilerMessage(
                Severity.ERROR,
                f"Python keyword not allowed as identifier: {name}",
                location=context
            ))
        
        return messages
    
    @staticmethod
    def validate_number(value: Any, context: str = "") -> List[CompilerMessage]:
        """Validate a numeric value."""
        messages = []
        
        try:
            num = float(value)
            # Prevent extremely large numbers
            if abs(num) > 1e15:
                messages.append(CompilerMessage(
                    Severity.WARNING,
                    f"Very large number: {num}",
                    location=context,
                    suggestion="Consider using a smaller value"
                ))
        except (ValueError, TypeError):
            messages.append(CompilerMessage(
                Severity.ERROR,
                f"Invalid number: {value}",
                location=context
            ))
        
        return messages


class ASTValidator:
    """Validates generated Python code using AST analysis."""
    
    # Imports allowed in generated code
    ALLOWED_IMPORTS = {
        'chaos_sdk.core.plugin': {'BasePlugin'},
        'random': None,  # None = allow all
        'time': None,
        'asyncio': None,
    }
    
    FORBIDDEN_NODES = {
        ast.Global, ast.Nonlocal,    # No scope manipulation
        ast.Delete,                   # No deletions
        ast.Exec if hasattr(ast, 'Exec') else None,  # No exec (Python 2)
    }
    
    FORBIDDEN_NODES = {n for n in FORBIDDEN_NODES if n is not None}
    
    @staticmethod
    def validate_code(code: str, allow_safe_imports: bool = True) -> List[CompilerMessage]:
        """Validate generated Python code."""
        messages = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            messages.append(CompilerMessage(
                Severity.ERROR,
                f"Generated code has syntax error: {e.msg}",
                location=f"line {e.lineno}",
                code="AST001"
            ))
            return messages
        
        # Walk the AST
        for node in ast.walk(tree):
            node_type = type(node)
            
            # Check for forbidden node types
            if node_type in ASTValidator.FORBIDDEN_NODES:
                messages.append(CompilerMessage(
                    Severity.SECURITY,
                    f"Forbidden AST node: {node_type.__name__}",
                    code="AST002"
                ))
            
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not ASTValidator._is_allowed_import(alias.name):
                        messages.append(CompilerMessage(
                            Severity.SECURITY,
                            f"Forbidden import: {alias.name}",
                            code="AST005"
                        ))
            
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if not ASTValidator._is_allowed_import(module):
                    messages.append(CompilerMessage(
                        Severity.SECURITY,
                        f"Forbidden import from: {module}",
                        code="AST006"
                    ))
            
            # Check function calls
            if isinstance(node, ast.Call):
                messages.extend(ASTValidator._check_call(node))
            
            # Check attribute access
            if isinstance(node, ast.Attribute):
                messages.extend(ASTValidator._check_attribute(node))
        
        return messages
    
    @staticmethod
    def _is_allowed_import(module_name: str) -> bool:
        """Check if an import is allowed."""
        for allowed in ASTValidator.ALLOWED_IMPORTS:
            if module_name == allowed or module_name.startswith(allowed + "."):
                return True
        return False
        
        return messages
    
    @staticmethod
    def _check_call(node: ast.Call) -> List[CompilerMessage]:
        """Check function call nodes."""
        messages = []
        
        # Get function name
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        
        # Check for dangerous calls
        dangerous_calls = {'eval', 'exec', 'compile', 'open', '__import__', 
                          'getattr', 'setattr', 'delattr', 'globals', 'locals'}
        
        if func_name in dangerous_calls:
            messages.append(CompilerMessage(
                Severity.SECURITY,
                f"Dangerous function call: {func_name}()",
                code="AST003"
            ))
        
        return messages
    
    @staticmethod
    def _check_attribute(node: ast.Attribute) -> List[CompilerMessage]:
        """Check attribute access nodes."""
        messages = []
        
        # Check for dunder access
        if node.attr.startswith('__') and node.attr.endswith('__'):
            messages.append(CompilerMessage(
                Severity.SECURITY,
                f"Dunder attribute access: {node.attr}",
                code="AST004"
            ))
        
        return messages


# ============================================================================
# Safe String Builder
# ============================================================================

class SafeStringBuilder:
    """Builds Python code strings safely."""
    
    @staticmethod
    def escape_string(s: str) -> str:
        """Safely escape a string for Python code."""
        if not isinstance(s, str):
            s = str(s)
        
        # Limit length
        if len(s) > MAX_STRING_LENGTH:
            s = s[:MAX_STRING_LENGTH]
        
        # Escape special characters
        s = s.replace('\\', '\\\\')
        s = s.replace("'", "\\'")
        s = s.replace('"', '\\"')
        s = s.replace('\n', '\\n')
        s = s.replace('\r', '\\r')
        s = s.replace('\t', '\\t')
        s = s.replace('\0', '')  # Remove null bytes
        
        # Remove any remaining control characters
        s = ''.join(c for c in s if ord(c) >= 32 or c in '\n\r\t')
        
        return s
    
    @staticmethod
    def safe_identifier(name: str) -> str:
        """Convert to safe Python identifier."""
        if not name:
            return "_empty"
        
        # Remove invalid characters
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Ensure starts with letter or underscore
        if safe[0].isdigit():
            safe = '_' + safe
        
        # Limit length
        safe = safe[:MAX_VARIABLE_NAME_LENGTH]
        
        # Avoid Python keywords
        import keyword
        if keyword.iskeyword(safe):
            safe = safe + '_'
        
        return safe
    
    @staticmethod
    def safe_number(value: Any) -> str:
        """Convert to safe number representation."""
        try:
            num = float(value)
            if num != num:  # NaN check
                return "0"
            if abs(num) == float('inf'):
                return "0"
            if num == int(num):
                return str(int(num))
            return str(num)
        except (ValueError, TypeError):
            return "0"


# ============================================================================
# Secure Code Emitter
# ============================================================================

class SecureCodeEmitter:
    """Generates secure Python code from blueprint nodes."""
    
    def __init__(self):
        self.messages: List[CompilerMessage] = []
        self.indent_level = 0
        self.nesting_depth = 0
        self.used_permissions: Set[str] = set()
    
    def emit_plugin(self, bp: Dict[str, Any], class_name: str = None) -> Tuple[str, List[CompilerMessage]]:
        """Generate complete plugin code."""
        self.messages = []
        
        # Validate structure
        if not self._validate_structure(bp):
            return "", self.messages
        
        meta = {
            "name": SafeStringBuilder.escape_string(bp.get("name", "Plugin")),
            "version": SafeStringBuilder.escape_string(bp.get("version", "1.0.0")),
            "author": SafeStringBuilder.escape_string(bp.get("author", "Unknown")),
            "description": SafeStringBuilder.escape_string(bp.get("description", "")),
        }
        
        cls = class_name or SafeStringBuilder.safe_identifier(meta["name"])
        commands = bp.get("commands", {})
        
        # Validate command count
        if len(commands) > MAX_COMMANDS:
            self.messages.append(CompilerMessage(
                Severity.ERROR,
                f"Too many commands ({len(commands)}, max {MAX_COMMANDS})"
            ))
            return "", self.messages
        
        lines = []
        
        # Header
        lines.append('"""')
        lines.append(f'Plugin: {meta["name"]} v{meta["version"]}')
        lines.append(f'Author: {meta["author"]}')
        lines.append(f'Description: {meta["description"]}')
        lines.append('')
        lines.append('Generated by Chaos Blueprint Compiler v3.0 (Secure)')
        lines.append('DO NOT EDIT - Regenerate from blueprint if changes needed')
        lines.append('"""')
        lines.append('')
        lines.append('from chaos_sdk.core.plugin import BasePlugin')
        lines.append('import random')
        lines.append('import time')
        lines.append('')
        lines.append('')
        lines.append(f'class {cls}(BasePlugin):')
        lines.append(f'    """Plugin gerado de blueprint."""')
        lines.append('')
        lines.append(f'    name = "{meta["name"]}"')
        lines.append(f'    version = "{meta["version"]}"')
        lines.append(f'    author = "{meta["author"]}"')
        lines.append(f'    description = "{meta["description"]}"')
        lines.append('')
        
        # Generate command handlers
        cmd_lines = []
        for cmd_name, cmd_data in commands.items():
            safe_cmd = SafeStringBuilder.safe_identifier(cmd_name)
            
            if isinstance(cmd_data, dict) and 'nodes' in cmd_data:
                handler = self._emit_visual_command(safe_cmd, cmd_data)
            elif isinstance(cmd_data, list):
                handler = self._emit_step_command(safe_cmd, cmd_data)
            else:
                self.messages.append(CompilerMessage(
                    Severity.WARNING,
                    f"Unknown command format for '{cmd_name}'"
                ))
                continue
            
            if handler:
                cmd_lines.append(handler)
        
        # Add permissions
        perms = tuple(sorted(self.used_permissions | {'core:log'}))
        lines.append(f'    required_permissions = {perms}')
        lines.append('')
        
        # on_load
        lines.append('    def on_load(self):')
        lines.append('        """Registra comandos do plugin."""')
        for cmd_name in commands.keys():
            safe_cmd = SafeStringBuilder.safe_identifier(cmd_name)
            lines.append(f'        self.register_command("{safe_cmd}", self.cmd_{safe_cmd})')
        lines.append('')
        
        # Command handlers
        for handler in cmd_lines:
            lines.extend(handler.split('\n'))
            lines.append('')
        
        code = '\n'.join(lines)
        
        # Final AST validation
        ast_messages = ASTValidator.validate_code(code)
        self.messages.extend(ast_messages)
        
        # Check for any security issues
        has_security_issues = any(m.severity == Severity.SECURITY for m in self.messages)
        if has_security_issues:
            self.messages.append(CompilerMessage(
                Severity.ERROR,
                "Compilation blocked due to security issues"
            ))
            return "", self.messages
        
        return code, self.messages
    
    def _validate_structure(self, bp: Dict[str, Any]) -> bool:
        """Validate blueprint structure."""
        required = ["name", "commands"]
        
        for field in required:
            if field not in bp:
                self.messages.append(CompilerMessage(
                    Severity.ERROR,
                    f"Missing required field: {field}"
                ))
                return False
        
        # Validate metadata strings
        for field in ["name", "version", "author", "description"]:
            if field in bp:
                msgs = SecurityValidator.validate_string(str(bp[field]), f"metadata.{field}")
                self.messages.extend(msgs)
        
        if not isinstance(bp["commands"], dict):
            self.messages.append(CompilerMessage(
                Severity.ERROR,
                "'commands' must be an object"
            ))
            return False
        
        return not any(m.severity in (Severity.ERROR, Severity.SECURITY) for m in self.messages)
    
    def _emit_step_command(self, cmd_name: str, steps: List[Dict]) -> str:
        """Generate handler from step list."""
        if len(steps) > MAX_STEPS_PER_COMMAND:
            self.messages.append(CompilerMessage(
                Severity.ERROR,
                f"Too many steps in '{cmd_name}' ({len(steps)}, max {MAX_STEPS_PER_COMMAND})"
            ))
            return ""
        
        lines = []
        lines.append(f'    def cmd_{cmd_name}(self, username: str, args: list, **kwargs) -> str:')
        lines.append(f'        """Handler for !{cmd_name}"""')
        lines.append('        responses = []')
        lines.append('        ctx = self.context')
        lines.append('        if not ctx:')
        lines.append("            return 'Sistema indisponível'")
        lines.append('        vars = {}')
        lines.append('')
        
        self.nesting_depth = 0
        for i, step in enumerate(steps):
            step_code = self._emit_step(step, f"{cmd_name}[{i}]")
            if step_code:
                lines.append(step_code)
        
        lines.append('')
        lines.append("        return ' '.join(str(x) for x in responses if x)")
        
        return '\n'.join(lines)
    
    def _emit_visual_command(self, cmd_name: str, cmd_data: Dict) -> str:
        """Generate handler from visual node graph."""
        nodes = cmd_data.get('nodes', [])
        connections = cmd_data.get('connections', [])
        
        if len(nodes) > MAX_NODES_PER_COMMAND:
            self.messages.append(CompilerMessage(
                Severity.ERROR,
                f"Too many nodes in '{cmd_name}' ({len(nodes)}, max {MAX_NODES_PER_COMMAND})"
            ))
            return ""
        
        if len(connections) > MAX_CONNECTIONS:
            self.messages.append(CompilerMessage(
                Severity.ERROR,
                f"Too many connections in '{cmd_name}'"
            ))
            return ""
        
        # Convert visual to steps and use step emitter
        steps = self._convert_visual_to_steps(nodes, connections)
        return self._emit_step_command(cmd_name, steps)
    
    def _convert_visual_to_steps(self, nodes: List[Dict], connections: List[Dict]) -> List[Dict]:
        """Convert visual nodes to step list."""
        steps = []
        nodes_by_id = {n.get('id'): n for n in nodes if 'id' in n}
        
        # Find event_start node
        start_node = None
        for node in nodes:
            if node.get('type') == 'event_start':
                start_node = node
                break
        
        if not start_node:
            return steps
        
        # Follow exec flow
        visited = set()
        self._traverse_visual_flow(start_node, nodes_by_id, connections, steps, visited)
        
        return steps
    
    def _traverse_visual_flow(self, node: Dict, nodes_by_id: Dict, connections: List[Dict], 
                              steps: List[Dict], visited: Set):
        """Traverse visual execution flow."""
        node_id = node.get('id')
        if node_id in visited:
            return
        visited.add(node_id)
        
        node_type = node.get('type', '')
        
        # Skip event_start
        if node_type != 'event_start':
            step = self._visual_node_to_step(node, nodes_by_id, connections)
            if step:
                steps.append(step)
        
        # Find next exec node
        for conn in connections:
            from_pin = conn.get('fromPin', '')
            if from_pin.startswith(f"{node_id}_") and 'exec' in from_pin.lower():
                next_id = conn.get('toNode')
                if next_id in nodes_by_id:
                    self._traverse_visual_flow(nodes_by_id[next_id], nodes_by_id, 
                                               connections, steps, visited)
    
    def _visual_node_to_step(self, node: Dict, nodes_by_id: Dict, connections: List[Dict]) -> Optional[Dict]:
        """Convert a visual node to a step dict."""
        node_type = node.get('type', '')
        data = node.get('data', {})
        
        # Map visual node types to step types
        step = {'type': node_type}
        
        if node_type == 'respond':
            step['message'] = self._resolve_visual_input(node, 'message', data.get('message', ''), 
                                                          nodes_by_id, connections)
        elif node_type == 'chat_send':
            step['message'] = self._resolve_visual_input(node, 'message', data.get('message', ''),
                                                          nodes_by_id, connections)
            step['platform'] = data.get('platform', 'twitch')
        elif node_type == 'audio_tts':
            step['text'] = self._resolve_visual_input(node, 'text', data.get('text', ''),
                                                       nodes_by_id, connections)
            step['lang'] = data.get('lang', 'pt-br')
        elif node_type == 'audio_play':
            step['name'] = self._resolve_visual_input(node, 'name', data.get('name', ''),
                                                       nodes_by_id, connections)
        elif node_type == 'points_add':
            step['user'] = '{username}'
            step['amount'] = self._resolve_visual_input(node, 'amount', data.get('amount', 10),
                                                         nodes_by_id, connections)
            step['reason'] = data.get('reason', '')
        elif node_type == 'points_remove':
            step['user'] = '{username}'
            step['amount'] = self._resolve_visual_input(node, 'amount', data.get('amount', 10),
                                                         nodes_by_id, connections)
            step['reason'] = data.get('reason', '')
        elif node_type == 'macro_run_keys':
            step['keys'] = self._resolve_visual_input(node, 'keys', data.get('keys', ''),
                                                       nodes_by_id, connections)
            step['delay'] = data.get('delay', 0.08)
        elif node_type == 'variable_set':
            step['name'] = SafeStringBuilder.safe_identifier(data.get('name', 'var'))
            step['value'] = self._resolve_visual_input(node, 'value', data.get('value', ''),
                                                        nodes_by_id, connections)
        elif node_type == 'delay':
            step['seconds'] = min(float(data.get('seconds', 1)), 30)  # Max 30 seconds
        else:
            # Copy data for other types
            step.update({k: v for k, v in data.items() if k != 'type'})
        
        return step
    
    def _resolve_visual_input(self, node: Dict, input_name: str, default: Any,
                               nodes_by_id: Dict, connections: List[Dict]) -> Any:
        """Resolve a visual input, checking connections."""
        node_id = node.get('id')
        input_pin_id = f"{node_id}_{input_name}"
        
        # Check for connection
        for conn in connections:
            if conn.get('toPin') == input_pin_id:
                # Has connection - would need full graph resolution
                # For now, use placeholder
                return default
        
        return default
    
    def _emit_step(self, step: Dict, location: str) -> str:
        """Emit code for a single step."""
        step_type = step.get('type', '')
        sp = '        '  # Base indent
        
        # Validate step type
        from chaos_sdk.blueprints.compiler_v2 import ALLOWED_ACTIONS
        if step_type not in ALLOWED_ACTIONS:
            self.messages.append(CompilerMessage(
                Severity.WARNING,
                f"Unknown action type: {step_type}",
                location=location
            ))
            return f"{sp}# Unknown action: {step_type}"
        
        # Track permissions
        from chaos_sdk.blueprints.compiler_v2 import ACTION_PERMISSIONS
        if step_type in ACTION_PERMISSIONS:
            self.used_permissions.add(ACTION_PERMISSIONS[step_type])
        
        # Emit based on type
        if step_type == 'respond':
            msg = self._safe_string_expr(step.get('message', ''))
            return f"{sp}responses.append(f{msg})"
        
        elif step_type == 'chat_send':
            msg = self._safe_string_expr(step.get('message', ''))
            platform = SafeStringBuilder.escape_string(step.get('platform', 'twitch'))
            return f'''{sp}try:
{sp}    import asyncio
{sp}    asyncio.get_event_loop().run_until_complete(
{sp}        ctx.send_chat(f{msg}, platform='{platform}')
{sp}    )
{sp}except Exception:
{sp}    pass'''
        
        elif step_type == 'audio_tts':
            text = self._safe_string_expr(step.get('text', ''))
            lang = SafeStringBuilder.escape_string(step.get('lang', 'pt-br'))
            return f"{sp}ctx.audio_tts(text=f{text}, lang='{lang}')"
        
        elif step_type == 'audio_play':
            name = self._safe_string_expr(step.get('name', ''))
            return f"{sp}ctx.audio_play({name})"
        
        elif step_type == 'audio_stop':
            return f"{sp}ctx.audio_stop()"
        
        elif step_type == 'audio_clear':
            return f"{sp}ctx.audio_clear_queue()"
        
        elif step_type == 'points_add':
            amount = SafeStringBuilder.safe_number(step.get('amount', 0))
            reason = SafeStringBuilder.escape_string(step.get('reason', ''))
            user = step.get('user', '{username}')
            user_expr = 'username' if user == '{username}' else f"'{SafeStringBuilder.escape_string(user)}'"
            return f"{sp}ctx.add_points({user_expr}, {amount}, '{reason}')"
        
        elif step_type == 'points_remove':
            amount = SafeStringBuilder.safe_number(step.get('amount', 0))
            reason = SafeStringBuilder.escape_string(step.get('reason', ''))
            user = step.get('user', '{username}')
            user_expr = 'username' if user == '{username}' else f"'{SafeStringBuilder.escape_string(user)}'"
            return f"{sp}ctx.remove_points({user_expr}, {amount}, '{reason}')"
        
        elif step_type == 'macro_run_keys':
            keys = SafeStringBuilder.escape_string(step.get('keys', ''))
            delay = SafeStringBuilder.safe_number(step.get('delay', 0.08))
            return f"{sp}ctx.macro_run_keys(username=username, keys='{keys}', delay={delay}, command='blueprint')"
        
        elif step_type == 'variable_set':
            name = SafeStringBuilder.safe_identifier(step.get('name', 'var'))
            value = self._safe_value_expr(step.get('value', ''))
            return f"{sp}vars['{name}'] = {value}"
        
        elif step_type == 'variable_increment':
            name = SafeStringBuilder.safe_identifier(step.get('name', 'counter'))
            amount = SafeStringBuilder.safe_number(step.get('amount', 1))
            return f"{sp}vars['{name}'] = vars.get('{name}', 0) + {amount}"
        
        elif step_type == 'delay':
            seconds = min(float(step.get('seconds', 1)), 30)  # Max 30 seconds
            return f"{sp}time.sleep({seconds})"
        
        elif step_type == 'if_points_at_least':
            min_pts = SafeStringBuilder.safe_number(step.get('min', 0))
            user = step.get('user', '{username}')
            user_expr = 'username' if user == '{username}' else f"'{SafeStringBuilder.escape_string(user)}'"
            
            code = f"{sp}if int(ctx.get_points({user_expr})) >= {min_pts}:\n"
            
            then_steps = step.get('then', [])
            if then_steps:
                for ts in then_steps:
                    inner = self._emit_step(ts, f"{location}/then")
                    if inner:
                        code += '    ' + inner + '\n'
            else:
                code += f"{sp}    pass\n"
            
            else_steps = step.get('else', [])
            if else_steps:
                code += f"{sp}else:\n"
                for es in else_steps:
                    inner = self._emit_step(es, f"{location}/else")
                    if inner:
                        code += '    ' + inner + '\n'
            
            return code.rstrip()
        
        elif step_type == 'leaderboard':
            limit = min(int(step.get('limit', 10)), 100)
            category = SafeStringBuilder.escape_string(step.get('category', 'points'))
            return f'''{sp}_lb = ctx.get_leaderboard(limit={limit}, category='{category}')
{sp}responses.append(', '.join([f'{{u}}:{{p}}' for u, p in _lb]))'''
        
        else:
            return f"{sp}# Action: {step_type} (not implemented in secure compiler)"
    
    def _safe_string_expr(self, value: Any) -> str:
        """Create a safe string expression."""
        if not isinstance(value, str):
            value = str(value)
        
        # Validate
        msgs = SecurityValidator.validate_string(value, "string expression")
        if any(m.severity == Severity.SECURITY for m in msgs):
            self.messages.extend(msgs)
            return "'[BLOCKED]'"
        
        escaped = SafeStringBuilder.escape_string(value)
        
        # Handle placeholders
        if '{username}' in escaped:
            escaped = escaped.replace('{username}', '{username}')
            return f"'{escaped}'"
        
        return f"'{escaped}'"
    
    def _safe_value_expr(self, value: Any) -> str:
        """Create a safe value expression."""
        if isinstance(value, bool):
            return 'True' if value else 'False'
        if isinstance(value, (int, float)):
            return SafeStringBuilder.safe_number(value)
        if isinstance(value, str):
            if value == '{username}':
                return 'username'
            if value.startswith('{var:') and value.endswith('}'):
                var_name = SafeStringBuilder.safe_identifier(value[5:-1])
                return f"vars.get('{var_name}', '')"
            return self._safe_string_expr(value)
        return "''"


# ============================================================================
# Main Compile Function
# ============================================================================

def compile_blueprint_secure(bp: Dict[str, Any], class_name: str = None) -> CompilationResult:
    """
    Compile blueprint with full security validation.
    
    This is the recommended entry point for production use.
    
    Args:
        bp: Blueprint dictionary
        class_name: Optional class name override
    
    Returns:
        CompilationResult with code or error messages
    """
    result = CompilationResult(success=False)
    
    # Basic type check
    if not isinstance(bp, dict):
        result.messages.append(CompilerMessage(
            Severity.ERROR,
            "Blueprint must be a JSON object"
        ))
        return result
    
    # Emit code
    emitter = SecureCodeEmitter()
    code, messages = emitter.emit_plugin(bp, class_name)
    
    result.messages = messages
    
    # Check for errors
    has_errors = any(m.severity in (Severity.ERROR, Severity.SECURITY) for m in messages)
    
    if has_errors:
        result.success = False
        result.code = f"# Compilation failed due to errors\n# See messages for details"
    else:
        result.success = True
        result.code = code
        
        # Generate security hash
        result.security_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        
        result.stats = {
            "code_lines": len(code.split('\n')),
            "permissions": list(emitter.used_permissions),
            "security_hash": result.security_hash,
        }
        
        result.messages.append(CompilerMessage(
            Severity.INFO,
            f"Compilation successful (hash: {result.security_hash})"
        ))
    
    return result


# Alias for backward compatibility
compile_blueprint_v3 = compile_blueprint_secure


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python compiler_v3.py input.json output.py [--class ClassName]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    class_name = None
    
    for i, arg in enumerate(sys.argv):
        if arg == "--class" and i + 1 < len(sys.argv):
            class_name = sys.argv[i + 1]
    
    with open(input_file, 'r', encoding='utf-8') as f:
        bp = json.load(f)
    
    result = compile_blueprint_secure(bp, class_name)
    
    # Print messages
    for msg in result.messages:
        icon = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️', 'security': '🔒'}.get(msg.severity.value, '•')
        print(f"{icon} [{msg.severity.value.upper()}] {msg.message}")
        if msg.location:
            print(f"   Location: {msg.location}")
        if msg.suggestion:
            print(f"   💡 {msg.suggestion}")
    
    if result.success:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.code)
        print(f"\n✅ Compiled successfully to: {output_file}")
        print(f"   Security hash: {result.security_hash}")
    else:
        print(f"\n❌ Compilation failed")
        sys.exit(1)
