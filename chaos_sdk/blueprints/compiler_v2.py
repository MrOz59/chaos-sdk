"""
Blueprint Compiler v2.0 - Intelligent Code Generator with Graph Resolution

Enhanced compiler that:
- Supports all action types from actions_meta.json
- Properly resolves pure data nodes through connection traversal
- Supports event hooks (on_message, on_follow, etc)
- Generates optimized, secure Python plugins
- Provides detailed diagnostics and suggestions

Usage:
  python -m chaos_sdk.blueprints.compiler_v2 input.json output.py [--class MyPlugin]
"""
from __future__ import annotations

import json
import os
import sys
import re
from typing import Dict, Any, List, Set, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# ============================================================================
# Compilation Result Types
# ============================================================================

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"

@dataclass
class CompilerMessage:
    severity: Severity
    message: str
    location: str = ""
    suggestion: str = ""
    code: str = ""  # Error code for programmatic handling

@dataclass
class CompilationResult:
    success: bool
    code: str = ""
    messages: List[CompilerMessage] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

# ============================================================================
# All Supported Actions (expanded from actions_meta.json)
# ============================================================================

ALLOWED_ACTIONS = {
    # Responses / chat
    "respond", "chat_send",
    
    # Pure Data nodes
    "const_string", "const_number", "const_bool",
    "get_username", "get_display_name", "get_args", "get_arg",
    "format_string",
    
    # String operations
    "string_concat", "string_length", "string_substring",
    "string_contains", "string_replace", "string_split",
    "string_upper", "string_lower", "string_trim",
    "string_starts_with", "string_ends_with",
    
    # Math operations
    "math_add", "math_subtract", "math_multiply", "math_divide",
    "math_modulo", "math_power", "math_sqrt", "math_abs",
    "math_min", "math_max", "math_clamp",
    "math_floor", "math_ceil", "math_round",
    "add", "subtract", "multiply", "divide",  # aliases
    
    # Logic operations
    "compare_greater", "compare_less", "compare_equal",
    "compare_not_equal", "compare_greater_equal", "compare_less_equal",
    "logic_and", "logic_or", "logic_not", "logic_xor",
    
    # Flow control
    "branch", "for_loop", "while_loop", "sequence",
    
    # Variables
    "variable_get", "variable_set", "variable_increment",
    
    # Arrays
    "array_create", "array_get", "array_length",
    "array_contains", "array_join", "array_push", "array_pop",
    
    # Conversion
    "convert_to_string", "convert_to_number", "convert_to_bool",
    
    # Random
    "random_number", "random_choice", "random_bool", "random_shuffle",
    
    # Time
    "delay", "get_timestamp", "get_date_time",
    
    # Macros
    "macro_run_keys", "macro_press_key", "macro_click",
    
    # Points
    "points_get", "points_add", "points_remove", "if_points_at_least",
    
    # Audio
    "audio_tts", "audio_play", "audio_stop", "audio_clear", "audio_queue_size",
    
    # Voting
    "voting_start", "voting_vote", "voting_end",
    "get_active_poll", "get_poll_results",
    
    # Leaderboard
    "leaderboard",
    
    # Minigames
    "minigames_command",
    
    # Events (for hook registration)
    "event_start", "event_message", "event_follow",
    "event_subscribe", "event_bits", "event_raid",
    "event_stream_start", "event_stream_end",
    
    # Comments (visual only, ignored in compilation)
    "comment", "reroute",
}

DEFAULT_PERMISSIONS = ["core:log"]

# Permission mapping for actions
ACTION_PERMISSIONS = {
    "chat_send": "chat:send",
    "respond": "chat:send",
    "points_get": "points:read",
    "points_add": "points:write",
    "points_remove": "points:write",
    "if_points_at_least": "points:read",
    "audio_tts": "audio:tts",
    "audio_play": "audio:play",
    "audio_stop": "audio:control",
    "audio_clear": "audio:control",
    "voting_start": "voting:manage",
    "voting_vote": "voting:vote",
    "voting_end": "voting:manage",
    "get_active_poll": "voting:read",
    "get_poll_results": "voting:read",
    "leaderboard": "leaderboard:read",
    "minigames_command": "minigames:play",
    "macro_run_keys": "macro:enqueue",
    "macro_press_key": "macro:enqueue",
    "macro_click": "macro:enqueue",
}

# ============================================================================
# Graph Resolution - Traverse connections to resolve pure node values
# ============================================================================

class GraphResolver:
    """Resolves pure data nodes by traversing the connection graph."""
    
    def __init__(self, nodes: List[Dict], connections: List[Dict]):
        self.nodes = {n['id']: n for n in nodes}
        self.connections = connections
        self.resolved_cache: Dict[str, str] = {}
        self.resolution_stack: Set[int] = set()  # Prevent infinite recursion
    
    def get_input_value(self, node_id: int, input_name: str, default: Any = None) -> str:
        """Get the value for an input pin, resolving connected pure nodes."""
        node = self.nodes.get(node_id)
        if not node:
            return self._to_python_value(default)
        
        # Find connection to this input
        input_pin_id = f"{node_id}_{input_name}"
        conn = self._find_connection_to(input_pin_id)
        
        if not conn:
            # No connection - use node's data value or default
            val = node.get('data', {}).get(input_name, default)
            return self._resolve_placeholders(val)
        
        # Resolve the connected output
        return self.resolve_output(conn['fromNode'], conn['fromPin'])
    
    def resolve_output(self, node_id: int, output_pin_id: str) -> str:
        """Resolve the value of an output pin."""
        cache_key = f"{node_id}:{output_pin_id}"
        if cache_key in self.resolved_cache:
            return self.resolved_cache[cache_key]
        
        # Prevent infinite recursion
        if node_id in self.resolution_stack:
            return "'<circular_reference>'"
        
        self.resolution_stack.add(node_id)
        
        try:
            node = self.nodes.get(node_id)
            if not node:
                return "''"
            
            result = self._generate_node_expression(node, output_pin_id)
            self.resolved_cache[cache_key] = result
            return result
        finally:
            self.resolution_stack.discard(node_id)
    
    def _generate_node_expression(self, node: Dict, output_pin_id: str) -> str:
        """Generate Python expression for a pure node's output."""
        node_type = node.get('type', '')
        data = node.get('data', {})
        node_id = node['id']
        
        # Extract output name from pin ID (format: {nodeId}_{outputName})
        output_name = output_pin_id.replace(f"{node_id}_", "")
        
        # Constant values
        if node_type == 'const_string':
            val = data.get('value', '')
            return f"'{self._escape_string(val)}'"
        
        if node_type == 'const_number':
            val = data.get('value', 0)
            return str(val)
        
        if node_type == 'const_bool':
            val = data.get('value', False)
            return 'True' if val else 'False'
        
        # Context values
        if node_type == 'get_username':
            return 'username'
        
        if node_type == 'get_display_name':
            return "kwargs.get('display_name', username)"
        
        if node_type == 'get_args':
            return 'args'
        
        if node_type == 'get_arg':
            index = self.get_input_value(node_id, 'index', 0)
            default = self.get_input_value(node_id, 'default', '')
            return f"(args[{index}] if len(args) > {index} else {default})"
        
        # String operations
        if node_type == 'format_string':
            fmt = self.get_input_value(node_id, 'format', '')
            args = [
                self.get_input_value(node_id, f'arg{i}', '')
                for i in range(4)
            ]
            return f"str({fmt}).format({', '.join(args)})"
        
        if node_type == 'string_concat':
            a = self.get_input_value(node_id, 'a', '')
            b = self.get_input_value(node_id, 'b', '')
            return f"str({a}) + str({b})"
        
        if node_type == 'string_length':
            val = self.get_input_value(node_id, 'value', '')
            return f"len(str({val}))"
        
        if node_type == 'string_upper':
            val = self.get_input_value(node_id, 'value', '')
            return f"str({val}).upper()"
        
        if node_type == 'string_lower':
            val = self.get_input_value(node_id, 'value', '')
            return f"str({val}).lower()"
        
        if node_type == 'string_trim':
            val = self.get_input_value(node_id, 'value', '')
            return f"str({val}).strip()"
        
        if node_type == 'string_contains':
            text = self.get_input_value(node_id, 'text', '')
            search = self.get_input_value(node_id, 'search', '')
            return f"({search} in str({text}))"
        
        if node_type == 'string_replace':
            text = self.get_input_value(node_id, 'text', '')
            old = self.get_input_value(node_id, 'old', '')
            new = self.get_input_value(node_id, 'new', '')
            return f"str({text}).replace({old}, {new})"
        
        if node_type == 'string_split':
            text = self.get_input_value(node_id, 'text', '')
            sep = self.get_input_value(node_id, 'separator', "' '")
            return f"str({text}).split({sep})"
        
        if node_type == 'string_substring':
            val = self.get_input_value(node_id, 'value', '')
            start = self.get_input_value(node_id, 'start', 0)
            end = self.get_input_value(node_id, 'end', -1)
            return f"str({val})[{start}:{end}]"
        
        if node_type == 'string_starts_with':
            text = self.get_input_value(node_id, 'text', '')
            prefix = self.get_input_value(node_id, 'prefix', '')
            return f"str({text}).startswith({prefix})"
        
        if node_type == 'string_ends_with':
            text = self.get_input_value(node_id, 'text', '')
            suffix = self.get_input_value(node_id, 'suffix', '')
            return f"str({text}).endswith({suffix})"
        
        # Math operations
        if node_type in ('math_add', 'add'):
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 0)
            return f"({a} + {b})"
        
        if node_type in ('math_subtract', 'subtract'):
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 0)
            return f"({a} - {b})"
        
        if node_type in ('math_multiply', 'multiply'):
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 1)
            return f"({a} * {b})"
        
        if node_type in ('math_divide', 'divide'):
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 1)
            return f"({a} / {b} if {b} != 0 else 0)"
        
        if node_type == 'math_modulo':
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 1)
            return f"({a} % {b} if {b} != 0 else 0)"
        
        if node_type == 'math_power':
            base = self.get_input_value(node_id, 'base', 2)
            exp = self.get_input_value(node_id, 'exponent', 2)
            return f"({base} ** {exp})"
        
        if node_type == 'math_sqrt':
            val = self.get_input_value(node_id, 'value', 0)
            return f"(({val}) ** 0.5)"
        
        if node_type == 'math_abs':
            val = self.get_input_value(node_id, 'value', 0)
            return f"abs({val})"
        
        if node_type == 'math_min':
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 0)
            return f"min({a}, {b})"
        
        if node_type == 'math_max':
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 0)
            return f"max({a}, {b})"
        
        if node_type == 'math_clamp':
            val = self.get_input_value(node_id, 'value', 0)
            min_val = self.get_input_value(node_id, 'min', 0)
            max_val = self.get_input_value(node_id, 'max', 100)
            return f"max({min_val}, min({max_val}, {val}))"
        
        if node_type == 'math_floor':
            val = self.get_input_value(node_id, 'value', 0)
            return f"int({val})"
        
        if node_type == 'math_ceil':
            val = self.get_input_value(node_id, 'value', 0)
            return f"(-(-{val} // 1))"
        
        if node_type == 'math_round':
            val = self.get_input_value(node_id, 'value', 0)
            return f"round({val})"
        
        # Comparison operations
        if node_type == 'compare_greater':
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 0)
            return f"({a} > {b})"
        
        if node_type == 'compare_less':
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 0)
            return f"({a} < {b})"
        
        if node_type == 'compare_equal':
            a = self.get_input_value(node_id, 'a', '')
            b = self.get_input_value(node_id, 'b', '')
            return f"({a} == {b})"
        
        if node_type == 'compare_not_equal':
            a = self.get_input_value(node_id, 'a', '')
            b = self.get_input_value(node_id, 'b', '')
            return f"({a} != {b})"
        
        if node_type == 'compare_greater_equal':
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 0)
            return f"({a} >= {b})"
        
        if node_type == 'compare_less_equal':
            a = self.get_input_value(node_id, 'a', 0)
            b = self.get_input_value(node_id, 'b', 0)
            return f"({a} <= {b})"
        
        # Logic operations
        if node_type == 'logic_and':
            a = self.get_input_value(node_id, 'a', 'False')
            b = self.get_input_value(node_id, 'b', 'False')
            return f"({a} and {b})"
        
        if node_type == 'logic_or':
            a = self.get_input_value(node_id, 'a', 'False')
            b = self.get_input_value(node_id, 'b', 'False')
            return f"({a} or {b})"
        
        if node_type == 'logic_not':
            val = self.get_input_value(node_id, 'value', 'False')
            return f"(not {val})"
        
        if node_type == 'logic_xor':
            a = self.get_input_value(node_id, 'a', 'False')
            b = self.get_input_value(node_id, 'b', 'False')
            return f"(bool({a}) != bool({b}))"
        
        # Random
        if node_type == 'random_number':
            min_val = self.get_input_value(node_id, 'min', 0)
            max_val = self.get_input_value(node_id, 'max', 100)
            return f"random.randint({min_val}, {max_val})"
        
        if node_type == 'random_bool':
            chance = self.get_input_value(node_id, 'chance', 50)
            return f"(random.random() * 100 < {chance})"
        
        if node_type == 'random_choice':
            choices = self.get_input_value(node_id, 'choices', '')
            return f"random.choice(str({choices}).split(','))"
        
        # Conversion
        if node_type == 'convert_to_string':
            val = self.get_input_value(node_id, 'value', '')
            return f"str({val})"
        
        if node_type == 'convert_to_number':
            val = self.get_input_value(node_id, 'value', '')
            return f"(int({val}) if str({val}).isdigit() else 0)"
        
        if node_type == 'convert_to_bool':
            val = self.get_input_value(node_id, 'value', '')
            return f"bool({val})"
        
        # Array operations
        if node_type == 'array_create':
            items = [
                self.get_input_value(node_id, f'item{i}', '')
                for i in range(4)
            ]
            return f"[{', '.join(items)}]"
        
        if node_type == 'array_get':
            arr = self.get_input_value(node_id, 'array', '[]')
            idx = self.get_input_value(node_id, 'index', 0)
            return f"({arr}[{idx}] if len({arr}) > {idx} else None)"
        
        if node_type == 'array_length':
            arr = self.get_input_value(node_id, 'array', '[]')
            return f"len({arr})"
        
        if node_type == 'array_contains':
            arr = self.get_input_value(node_id, 'array', '[]')
            val = self.get_input_value(node_id, 'value', '')
            return f"({val} in {arr})"
        
        if node_type == 'array_join':
            arr = self.get_input_value(node_id, 'array', '[]')
            sep = self.get_input_value(node_id, 'separator', "', '")
            return f"{sep}.join(str(x) for x in {arr})"
        
        # Time
        if node_type == 'get_timestamp':
            return 'int(time.time())'
        
        if node_type == 'get_date_time':
            fmt = self.get_input_value(node_id, 'format', "'%Y-%m-%d %H:%M:%S'")
            return f"time.strftime({fmt})"
        
        # Variable get (runtime resolution)
        if node_type == 'variable_get':
            name = data.get('name', 'var')
            return f"vars.get('{name}', '')"
        
        # Points get (API call)
        if node_type == 'points_get':
            user = self.get_input_value(node_id, 'user', 'username')
            if user == "'username'" or user == 'username':
                return "ctx.get_points(username)"
            return f"ctx.get_points({user})"
        
        # Default fallback
        return f"'<unresolved:{node_type}>'"
    
    def _find_connection_to(self, to_pin_id: str) -> Optional[Dict]:
        """Find connection that ends at the given pin."""
        for conn in self.connections:
            if conn.get('toPin') == to_pin_id:
                return conn
        return None
    
    def _to_python_value(self, val: Any) -> str:
        """Convert a value to Python literal."""
        if val is None:
            return "''"
        if isinstance(val, bool):
            return 'True' if val else 'False'
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            return f"'{self._escape_string(val)}'"
        return repr(val)
    
    def _escape_string(self, s: str) -> str:
        """Escape string for Python."""
        return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    
    def _resolve_placeholders(self, val: Any) -> str:
        """Resolve {username} and {var:name} placeholders."""
        if not isinstance(val, str):
            return self._to_python_value(val)
        
        if val == '{username}':
            return 'username'
        
        if val.startswith('{var:') and val.endswith('}'):
            var_name = val[5:-1]
            return f"vars.get('{var_name}', '')"
        
        # Check if string contains placeholders
        if '{username}' in val:
            return f"f'{self._escape_string(val)}'"
        
        return f"'{self._escape_string(val)}'"


# ============================================================================
# Visual Graph to Flat Steps Converter
# ============================================================================

class GraphToStepsConverter:
    """Converts visual node graph to flat step list for legacy compiler."""
    
    def __init__(self, visual_data: Dict):
        self.nodes = visual_data.get('nodes', [])
        self.connections = visual_data.get('connections', [])
        self.nodes_by_id = {n['id']: n for n in self.nodes}
        self.resolver = GraphResolver(self.nodes, self.connections)
    
    def convert(self) -> List[Dict]:
        """Convert graph to step list by following exec flow."""
        steps = []
        
        # Find start event node
        start_node = None
        for node in self.nodes:
            if node.get('type') == 'event_start':
                start_node = node
                break
        
        if not start_node:
            return steps
        
        # Follow exec flow
        visited = set()
        self._traverse_exec_flow(start_node, steps, visited)
        
        return steps
    
    def _traverse_exec_flow(self, node: Dict, steps: List[Dict], visited: Set[int]):
        """Recursively traverse execution flow."""
        if node['id'] in visited:
            return
        visited.add(node['id'])
        
        node_type = node.get('type', '')
        
        # Skip event start - it's just entry point
        if node_type != 'event_start':
            step = self._node_to_step(node)
            if step:
                steps.append(step)
        
        # Find next exec nodes
        exec_outputs = [p for p in node.get('outputs', []) if p.get('type') == 'exec']
        
        for exec_out in exec_outputs:
            next_conn = self._find_connection_from(exec_out['id'])
            if next_conn:
                next_node = self.nodes_by_id.get(next_conn['toNode'])
                if next_node:
                    # Handle branch nodes specially
                    if node_type == 'branch' and exec_out.get('label') in ('True', 'False'):
                        branch_key = 'then' if exec_out['label'] == 'True' else 'else'
                        branch_steps = []
                        self._traverse_exec_flow(next_node, branch_steps, visited.copy())
                        if steps and steps[-1].get('type') == 'branch':
                            steps[-1][branch_key] = branch_steps
                    else:
                        self._traverse_exec_flow(next_node, steps, visited)
    
    def _node_to_step(self, node: Dict) -> Optional[Dict]:
        """Convert a node to a step dict."""
        node_type = node.get('type', '')
        node_id = node['id']
        data = node.get('data', {})
        
        # Skip pure nodes - they're resolved through connections
        if node.get('isPure', False):
            return None
        
        # Skip visual-only nodes
        if node_type in ('comment', 'reroute'):
            return None
        
        step = {'type': node_type}
        
        # Resolve input values
        if node_type == 'respond':
            step['message'] = self._resolve_input(node_id, 'message', data.get('message', ''))
        
        elif node_type == 'chat_send':
            step['message'] = self._resolve_input(node_id, 'message', data.get('message', ''))
            step['platform'] = data.get('platform', 'twitch')
        
        elif node_type == 'branch':
            step['condition'] = self._resolve_input(node_id, 'condition', 'False')
            step['then'] = []
            step['else'] = []
        
        elif node_type == 'for_loop':
            step['start'] = self._resolve_input(node_id, 'start', 0)
            step['end'] = self._resolve_input(node_id, 'end', 10)
            step['step'] = self._resolve_input(node_id, 'step', 1)
            step['loop_body'] = []
        
        elif node_type == 'while_loop':
            step['condition'] = self._resolve_input(node_id, 'condition', 'False')
            step['loop_body'] = []
        
        elif node_type == 'variable_set':
            step['name'] = data.get('name', 'var')
            step['value'] = self._resolve_input(node_id, 'value', '')
        
        elif node_type == 'variable_increment':
            step['name'] = data.get('name', 'counter')
            step['amount'] = self._resolve_input(node_id, 'amount', 1)
        
        elif node_type == 'delay':
            step['seconds'] = self._resolve_input(node_id, 'seconds', 1)
        
        elif node_type == 'macro_run_keys':
            step['keys'] = self._resolve_input(node_id, 'keys', '')
            step['delay'] = self._resolve_input(node_id, 'delay', 0.08)
        
        elif node_type == 'points_add':
            step['user'] = self._resolve_input(node_id, 'user', '{username}')
            step['amount'] = self._resolve_input(node_id, 'amount', 10)
            step['reason'] = self._resolve_input(node_id, 'reason', '')
        
        elif node_type == 'points_remove':
            step['user'] = self._resolve_input(node_id, 'user', '{username}')
            step['amount'] = self._resolve_input(node_id, 'amount', 10)
            step['reason'] = self._resolve_input(node_id, 'reason', '')
        
        elif node_type == 'if_points_at_least':
            step['user'] = self._resolve_input(node_id, 'user', '{username}')
            step['min'] = self._resolve_input(node_id, 'min', 0)
            step['then'] = []
            step['else'] = []
        
        elif node_type == 'audio_tts':
            step['text'] = self._resolve_input(node_id, 'text', '')
            step['lang'] = data.get('lang', 'pt-br')
        
        elif node_type == 'audio_play':
            step['name'] = self._resolve_input(node_id, 'name', '')
        
        elif node_type == 'voting_start':
            step['title'] = self._resolve_input(node_id, 'title', '')
            step['options'] = data.get('options', [])
            step['duration_minutes'] = self._resolve_input(node_id, 'duration_minutes', 5)
            step['allow_change'] = data.get('allow_change', True)
            step['require_points'] = self._resolve_input(node_id, 'require_points', 0)
            step['creator'] = self._resolve_input(node_id, 'creator', '{username}')
            step['store_as'] = data.get('store_as', 'poll_id')
        
        elif node_type == 'voting_vote':
            step['poll_id'] = self._resolve_input(node_id, 'poll_id', '{var:poll_id}')
            step['option_index'] = self._resolve_input(node_id, 'option_index', 0)
        
        elif node_type == 'voting_end':
            step['poll_id'] = self._resolve_input(node_id, 'poll_id', '{var:poll_id}')
            step['reason'] = self._resolve_input(node_id, 'reason', 'manual')
        
        elif node_type == 'leaderboard':
            step['limit'] = self._resolve_input(node_id, 'limit', 10)
            step['category'] = self._resolve_input(node_id, 'category', 'points')
        
        elif node_type == 'minigames_command':
            step['command'] = self._resolve_input(node_id, 'command', '')
            step['args'] = data.get('args', [])
        
        else:
            # Copy all data as-is for unknown types
            step.update(data)
        
        return step
    
    def _resolve_input(self, node_id: int, input_name: str, default: Any) -> Any:
        """Resolve an input value, checking for connections first."""
        # Check for connection
        input_pin_id = f"{node_id}_{input_name}"
        conn = self._find_connection_to(input_pin_id)
        
        if conn:
            # Return expression that will be evaluated at runtime
            return f"{{expr:{self.resolver.resolve_output(conn['fromNode'], conn['fromPin'])}}}"
        
        return default
    
    def _find_connection_from(self, from_pin_id: str) -> Optional[Dict]:
        for conn in self.connections:
            if conn.get('fromPin') == from_pin_id:
                return conn
        return None
    
    def _find_connection_to(self, to_pin_id: str) -> Optional[Dict]:
        for conn in self.connections:
            if conn.get('toPin') == to_pin_id:
                return conn
        return None


# ============================================================================
# Code Emitter v2 - Direct graph compilation
# ============================================================================

class CodeEmitterV2:
    """Generates Python code directly from visual graph."""
    
    def __init__(self, graph_data: Dict, resolver: GraphResolver):
        self.nodes = graph_data.get('nodes', [])
        self.connections = graph_data.get('connections', [])
        self.nodes_by_id = {n['id']: n for n in self.nodes}
        self.resolver = resolver
        self.indent = 0
    
    def emit_command(self, cmd_name: str) -> str:
        """Generate command handler code."""
        lines = []
        lines.append(f"    def cmd_{cmd_name}(self, username: str, args: list, **kwargs) -> str:")
        lines.append("        responses = []")
        lines.append("        ctx = self.context")
        lines.append("        if not ctx:")
        lines.append("            return 'context unavailable'")
        lines.append("        vars = {}  # per-command variable store")
        lines.append("")
        
        # Find start node
        start_node = None
        for node in self.nodes:
            if node.get('type') == 'event_start':
                start_node = node
                break
        
        if start_node:
            self.indent = 2
            visited = set()
            self._emit_exec_chain(start_node, lines, visited)
        
        lines.append("")
        lines.append("        return ' '.join([str(x) for x in responses if x])")
        
        return "\n".join(lines)
    
    def _emit_exec_chain(self, node: Dict, lines: List[str], visited: Set[int]):
        """Emit code following exec chain."""
        if node['id'] in visited:
            return
        visited.add(node['id'])
        
        node_type = node.get('type', '')
        
        # Emit current node (skip event_start)
        if node_type != 'event_start':
            self._emit_node(node, lines)
        
        # Find next exec node(s)
        exec_outputs = [p for p in node.get('outputs', []) if p.get('type') == 'exec']
        
        for exec_out in exec_outputs:
            next_conn = self._find_connection_from(exec_out['id'])
            if next_conn:
                next_node = self.nodes_by_id.get(next_conn['toNode'])
                if next_node:
                    self._emit_exec_chain(next_node, lines, visited)
    
    def _emit_node(self, node: Dict, lines: List[str]):
        """Emit code for a single node."""
        node_type = node.get('type', '')
        node_id = node['id']
        data = node.get('data', {})
        sp = "    " * self.indent
        
        if node_type == 'respond':
            msg = self.resolver.get_input_value(node_id, 'message', data.get('message', ''))
            if msg.startswith("'") or msg.startswith('"'):
                lines.append(f"{sp}responses.append(f{msg})")
            else:
                lines.append(f"{sp}responses.append(str({msg}))")
        
        elif node_type == 'chat_send':
            msg = self.resolver.get_input_value(node_id, 'message', data.get('message', ''))
            platform = data.get('platform', 'twitch')
            lines.append(f"{sp}try:")
            lines.append(f"{sp}    import asyncio")
            if msg.startswith("'") or msg.startswith('"'):
                lines.append(f"{sp}    asyncio.get_event_loop().run_until_complete(ctx.send_chat(f{msg}, platform='{platform}'))")
            else:
                lines.append(f"{sp}    asyncio.get_event_loop().run_until_complete(ctx.send_chat(str({msg}), platform='{platform}'))")
            lines.append(f"{sp}except Exception:")
            lines.append(f"{sp}    pass")
        
        elif node_type == 'branch':
            cond = self.resolver.get_input_value(node_id, 'condition', 'False')
            lines.append(f"{sp}if {cond}:")
            
            # Find True branch
            true_out = next((p for p in node.get('outputs', []) if p.get('label') == 'True'), None)
            if true_out:
                true_conn = self._find_connection_from(true_out['id'])
                if true_conn:
                    true_node = self.nodes_by_id.get(true_conn['toNode'])
                    if true_node:
                        self.indent += 1
                        self._emit_exec_chain(true_node, lines, set())
                        self.indent -= 1
            if not any(l.strip().startswith("if") for l in lines[-3:]):
                lines.append(f"{sp}    pass")
            
            # Find False branch
            false_out = next((p for p in node.get('outputs', []) if p.get('label') == 'False'), None)
            if false_out:
                false_conn = self._find_connection_from(false_out['id'])
                if false_conn:
                    lines.append(f"{sp}else:")
                    false_node = self.nodes_by_id.get(false_conn['toNode'])
                    if false_node:
                        self.indent += 1
                        self._emit_exec_chain(false_node, lines, set())
                        self.indent -= 1
        
        elif node_type == 'for_loop':
            start = self.resolver.get_input_value(node_id, 'start', 0)
            end = self.resolver.get_input_value(node_id, 'end', 10)
            step = self.resolver.get_input_value(node_id, 'step', 1)
            lines.append(f"{sp}for _i in range(int({start}), int({end}), int({step})):")
            lines.append(f"{sp}    vars['index'] = _i")
            
            # Find loop body
            body_out = next((p for p in node.get('outputs', []) if 'body' in p.get('label', '').lower() or 'loop' in p.get('id', '').lower()), None)
            if body_out:
                body_conn = self._find_connection_from(body_out['id'])
                if body_conn:
                    body_node = self.nodes_by_id.get(body_conn['toNode'])
                    if body_node:
                        self.indent += 1
                        self._emit_exec_chain(body_node, lines, set())
                        self.indent -= 1
            else:
                lines.append(f"{sp}    pass")
        
        elif node_type == 'variable_set':
            name = data.get('name', 'var')
            val = self.resolver.get_input_value(node_id, 'value', '')
            lines.append(f"{sp}vars['{name}'] = {val}")
        
        elif node_type == 'variable_increment':
            name = data.get('name', 'counter')
            amount = self.resolver.get_input_value(node_id, 'amount', 1)
            lines.append(f"{sp}vars['{name}'] = vars.get('{name}', 0) + {amount}")
        
        elif node_type == 'delay':
            seconds = self.resolver.get_input_value(node_id, 'seconds', 1)
            lines.append(f"{sp}import time")
            lines.append(f"{sp}time.sleep({seconds})")
        
        elif node_type == 'macro_run_keys':
            keys = self.resolver.get_input_value(node_id, 'keys', '')
            delay = self.resolver.get_input_value(node_id, 'delay', 0.08)
            lines.append(f"{sp}ctx.macro_run_keys(username=username, keys=str({keys}), delay={delay}, command='blueprint')")
        
        elif node_type == 'points_add':
            user = self.resolver.get_input_value(node_id, 'user', 'username')
            amount = self.resolver.get_input_value(node_id, 'amount', 10)
            reason = self.resolver.get_input_value(node_id, 'reason', "''")
            if user == "'username'" or user == 'username':
                user = 'username'
            lines.append(f"{sp}ctx.add_points({user}, int({amount}), {reason})")
        
        elif node_type == 'points_remove':
            user = self.resolver.get_input_value(node_id, 'user', 'username')
            amount = self.resolver.get_input_value(node_id, 'amount', 10)
            reason = self.resolver.get_input_value(node_id, 'reason', "''")
            if user == "'username'" or user == 'username':
                user = 'username'
            lines.append(f"{sp}ctx.remove_points({user}, int({amount}), {reason})")
        
        elif node_type == 'if_points_at_least':
            user = self.resolver.get_input_value(node_id, 'user', 'username')
            min_pts = self.resolver.get_input_value(node_id, 'min', 0)
            if user == "'username'" or user == 'username':
                user = 'username'
            lines.append(f"{sp}if int(ctx.get_points({user})) >= int({min_pts}):")
            # then/else branches would be handled similar to branch node
            lines.append(f"{sp}    pass  # then branch")
        
        elif node_type == 'audio_tts':
            text = self.resolver.get_input_value(node_id, 'text', '')
            lang = data.get('lang', 'pt-br')
            if text.startswith("'"):
                lines.append(f"{sp}ctx.audio_tts(text=f{text}, lang='{lang}')")
            else:
                lines.append(f"{sp}ctx.audio_tts(text=str({text}), lang='{lang}')")
        
        elif node_type == 'audio_play':
            name = self.resolver.get_input_value(node_id, 'name', '')
            lines.append(f"{sp}ctx.audio_play({name})")
        
        elif node_type == 'audio_stop':
            lines.append(f"{sp}ctx.audio_stop()")
        
        elif node_type == 'audio_clear':
            lines.append(f"{sp}ctx.audio_clear_queue()")
        
        elif node_type == 'leaderboard':
            limit = self.resolver.get_input_value(node_id, 'limit', 10)
            category = self.resolver.get_input_value(node_id, 'category', "'points'")
            lines.append(f"{sp}_lb = ctx.get_leaderboard(limit=int({limit}), category={category})")
            lines.append(f"{sp}responses.append(', '.join([str(u)+':'+str(p) for u,p in _lb]))")
        
        elif node_type == 'voting_start':
            title = self.resolver.get_input_value(node_id, 'title', '')
            options = data.get('options', [])
            duration = self.resolver.get_input_value(node_id, 'duration_minutes', 5)
            allow_change = data.get('allow_change', True)
            require_pts = self.resolver.get_input_value(node_id, 'require_points', 0)
            creator = self.resolver.get_input_value(node_id, 'creator', 'username')
            store_as = data.get('store_as', 'poll_id')
            
            if creator == "'username'" or creator == 'username':
                creator = 'username'
            
            lines.append(f"{sp}_res = ctx.start_poll({title}, {repr(options)}, {creator}, int({duration}), {allow_change}, int({require_pts}))")
            lines.append(f"{sp}try:")
            lines.append(f"{sp}    _pid = (_res or {{}}).get('poll', {{}}).get('id') or (_res or {{}}).get('id')")
            lines.append(f"{sp}    vars['{store_as}'] = _pid")
            lines.append(f"{sp}except Exception:")
            lines.append(f"{sp}    pass")
        
        elif node_type == 'minigames_command':
            cmd = self.resolver.get_input_value(node_id, 'command', '')
            mg_args = data.get('args', [])
            lines.append(f"{sp}_mg = ctx.minigames_command({cmd}, username, {mg_args})")
            lines.append(f"{sp}responses.append(str(_mg) if _mg else '')")
        
        else:
            lines.append(f"{sp}# Unsupported action: {node_type}")
    
    def _find_connection_from(self, from_pin_id: str) -> Optional[Dict]:
        for conn in self.connections:
            if conn.get('fromPin') == from_pin_id:
                return conn
        return None


# ============================================================================
# Main Compiler Function
# ============================================================================

def compile_blueprint_v2(bp: Dict[str, Any], class_name: str = None, standalone: bool = False) -> CompilationResult:
    """
    Compile visual blueprint to Python plugin.
    
    Supports both:
    - Legacy flat step format (commands: {cmd: [steps]})
    - Visual node graph format (commands: {cmd: {nodes, connections}})
    """
    result = CompilationResult(success=False)
    
    try:
        # Extract metadata
        meta = {
            "name": bp.get("name", "BlueprintPlugin"),
            "version": bp.get("version", "1.0.0"),
            "author": bp.get("author", "Unknown"),
            "description": bp.get("description", "Generated from visual blueprint"),
        }
        
        cls = class_name or meta["name"].replace(" ", "")
        commands = bp.get("commands", {})
        
        # Collect required permissions
        required_perms = set(DEFAULT_PERMISSIONS)
        
        # Generate code
        out: List[str] = []
        
        # Header
        out.append("# " + "=" * 60)
        out.append(f"# Generated by Blueprint Compiler v2.0")
        out.append(f"# Plugin: {meta['name']} v{meta['version']}")
        out.append(f"# Author: {meta['author']}")
        out.append("# " + "=" * 60)
        out.append("")
        
        if standalone:
            out.append("# Standalone mode: using stub base plugin")
            out.append("from chaos_sdk.blueprints.base_stub import BasePluginStub as BasePlugin")
        else:
            out.append("from chaos_sdk.core.plugin import BasePlugin")
        
        out.append("")
        out.append("# Required imports")
        out.append("import random")
        out.append("import time")
        out.append("")
        out.append("")
        out.append(f"class {cls}(BasePlugin):")
        out.append("")
        out.append(f'    name = "{meta["name"]}"')
        out.append(f'    version = "{meta["version"]}"')
        out.append(f'    author = "{meta["author"]}"')
        out.append(f'    description = "{meta["description"]}"')
        out.append("")
        
        # Generate command handlers
        cmd_code = []
        for cmd_name, cmd_data in commands.items():
            # Check if visual format (has nodes/connections)
            if isinstance(cmd_data, dict) and ('nodes' in cmd_data or 'connections' in cmd_data):
                # Visual node format
                resolver = GraphResolver(cmd_data.get('nodes', []), cmd_data.get('connections', []))
                emitter = CodeEmitterV2(cmd_data, resolver)
                cmd_code.append(emitter.emit_command(cmd_name))
                
                # Collect permissions from nodes
                for node in cmd_data.get('nodes', []):
                    node_type = node.get('type', '')
                    if node_type in ACTION_PERMISSIONS:
                        required_perms.add(ACTION_PERMISSIONS[node_type])
            
            elif isinstance(cmd_data, list):
                # Legacy flat step format - use original compiler
                from chaos_sdk.blueprints.compiler import emit_command_handler
                cmd_code.append(emit_command_handler(cmd_name, cmd_data))
                
                # Collect permissions from steps
                for step in cmd_data:
                    step_type = step.get('type', '')
                    if step_type in ACTION_PERMISSIONS:
                        required_perms.add(ACTION_PERMISSIONS[step_type])
        
        # Add permissions
        out.append(f"    required_permissions = {tuple(sorted(required_perms))}")
        out.append("")
        
        # Add on_load
        out.append("    def on_load(self):")
        for cmd_name in commands.keys():
            out.append(f'        self.register_command("{cmd_name}", self.cmd_{cmd_name})')
        out.append("        # Generated by Blueprint Compiler v2.0")
        out.append("")
        
        # Add command handlers
        for handler_code in cmd_code:
            out.append(handler_code)
            out.append("")
        
        result.code = "\n".join(out)
        result.success = True
        result.stats = {
            "commands": len(commands),
            "permissions": list(required_perms),
        }
        
        result.messages.append(CompilerMessage(
            Severity.INFO,
            f"Successfully compiled {len(commands)} command(s)"
        ))
        
    except Exception as e:
        result.success = False
        result.messages.append(CompilerMessage(
            Severity.ERROR,
            f"Compilation failed: {str(e)}",
            suggestion="Check your blueprint structure"
        ))
        result.code = f"# Compilation failed: {e}"
    
    return result


# ============================================================================
# CLI Entry Point
# ============================================================================

def main(argv: List[str]):
    if len(argv) < 3:
        print("Usage: python -m sdk.blueprints.compiler_v2 input.json output.py [--class MyPlugin] [--standalone]")
        sys.exit(2)
    
    inp = argv[1]
    outp = argv[2]
    cls = None
    standalone = False
    
    for i, arg in enumerate(argv):
        if arg == "--class" and i + 1 < len(argv):
            cls = argv[i + 1]
        if arg == "--standalone":
            standalone = True
    
    if not os.path.exists(inp):
        print(f"Input not found: {inp}")
        sys.exit(1)
    
    with open(inp, "r", encoding="utf-8") as f:
        bp = json.load(f)
    
    result = compile_blueprint_v2(bp, class_name=cls, standalone=standalone)
    
    # Print messages
    for msg in result.messages:
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️", "hint": "💡"}.get(msg.severity.value, "•")
        print(f"{icon} {msg.severity.value.upper()}: {msg.message}")
        if msg.location:
            print(f"   Location: {msg.location}")
        if msg.suggestion:
            print(f"   💡 {msg.suggestion}")
    
    with open(outp, "w", encoding="utf-8") as f:
        f.write(result.code)
    
    if result.success:
        print(f"\n✅ Successfully compiled to: {outp}")
        sys.exit(0)
    else:
        print(f"\n❌ Compilation failed. Output written for debugging.")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
