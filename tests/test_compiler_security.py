"""
Security Tests for Blueprint Compiler v3
=========================================

Tests that verify the compiler properly blocks:
- Code injection attempts
- Dangerous function calls
- Dunder attribute access
- Import attempts
- File system access attempts
- And more...
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pathlib import Path
from chaos_sdk.blueprints.compiler_v3 import (
    compile_blueprint_secure,
    SecurityValidator,
    ASTValidator,
    SafeStringBuilder,
    Severity,
)


class TestSecurityValidator:
    """Test security validation functions."""
    
    def test_detect_eval(self):
        """Should detect eval() attempts."""
        messages = SecurityValidator.validate_string("eval('malicious')")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_detect_exec(self):
        """Should detect exec() attempts."""
        messages = SecurityValidator.validate_string("exec('code')")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_detect_import(self):
        """Should detect import statements."""
        messages = SecurityValidator.validate_string("import os")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_detect_dunder(self):
        """Should detect dunder access."""
        messages = SecurityValidator.validate_string("__class__.__bases__")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_detect_os_access(self):
        """Should detect os module access."""
        messages = SecurityValidator.validate_string("os.system('rm -rf /')")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_detect_file_ops(self):
        """Should detect file operations."""
        messages = SecurityValidator.validate_string("open('/etc/passwd').read()")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_detect_subprocess(self):
        """Should detect subprocess calls."""
        messages = SecurityValidator.validate_string("subprocess.call(['ls'])")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_detect_getattr(self):
        """Should detect getattr abuse."""
        messages = SecurityValidator.validate_string("getattr(obj, '__code__')")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_detect_null_bytes(self):
        """Should detect null bytes."""
        messages = SecurityValidator.validate_string("hello\x00world")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_detect_long_strings(self):
        """Should warn about very long strings."""
        long_string = "x" * 2000
        messages = SecurityValidator.validate_string(long_string)
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_valid_identifier(self):
        """Should accept valid identifiers."""
        messages = SecurityValidator.validate_identifier("my_variable")
        assert not any(m.severity in (Severity.ERROR, Severity.SECURITY) for m in messages)
    
    def test_invalid_identifier_dunder(self):
        """Should reject dunder identifiers."""
        messages = SecurityValidator.validate_identifier("__init__")
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_invalid_identifier_keyword(self):
        """Should reject Python keywords."""
        messages = SecurityValidator.validate_identifier("class")
        assert any(m.severity == Severity.ERROR for m in messages)


class TestASTValidator:
    """Test AST validation."""
    
    def test_valid_code(self):
        """Should accept valid Python code."""
        code = '''
x = 1
y = x + 2
print(y)
'''
        messages = ASTValidator.validate_code(code)
        assert not any(m.severity in (Severity.ERROR, Severity.SECURITY) for m in messages)
    
    def test_syntax_error(self):
        """Should detect syntax errors."""
        code = "def broken("
        messages = ASTValidator.validate_code(code)
        assert any(m.severity == Severity.ERROR for m in messages)
    
    def test_import_blocked(self):
        """Should block import statements."""
        code = "import os\nos.system('ls')"
        messages = ASTValidator.validate_code(code)
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_from_import_blocked(self):
        """Should block from imports."""
        code = "from os import system"
        messages = ASTValidator.validate_code(code)
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_eval_call_blocked(self):
        """Should block eval calls."""
        code = "eval('1+1')"
        messages = ASTValidator.validate_code(code)
        assert any(m.severity == Severity.SECURITY for m in messages)
    
    def test_dunder_attribute_blocked(self):
        """Should block dunder attribute access."""
        code = "obj.__class__.__bases__"
        messages = ASTValidator.validate_code(code)
        assert any(m.severity == Severity.SECURITY for m in messages)


class TestSafeStringBuilder:
    """Test safe string building."""
    
    def test_escape_quotes(self):
        """Should escape quotes."""
        result = SafeStringBuilder.escape_string("it's a \"test\"")
        assert "\\'" in result or '\\"' in result
    
    def test_escape_newlines(self):
        """Should escape newlines."""
        result = SafeStringBuilder.escape_string("line1\nline2")
        assert "\\n" in result
    
    def test_remove_null_bytes(self):
        """Should remove null bytes."""
        result = SafeStringBuilder.escape_string("hello\x00world")
        assert "\x00" not in result
    
    def test_truncate_long_strings(self):
        """Should truncate very long strings."""
        long_input = "x" * 5000
        result = SafeStringBuilder.escape_string(long_input)
        assert len(result) <= 1000
    
    def test_safe_identifier_from_invalid(self):
        """Should convert invalid names to valid identifiers."""
        result = SafeStringBuilder.safe_identifier("123-test!")
        assert result.isidentifier()
    
    def test_safe_identifier_keyword_avoidance(self):
        """Should avoid Python keywords."""
        result = SafeStringBuilder.safe_identifier("class")
        assert result != "class"
    
    def test_safe_number(self):
        """Should safely convert numbers."""
        assert SafeStringBuilder.safe_number(42) == "42"
        assert SafeStringBuilder.safe_number(3.14) == "3.14"
        assert SafeStringBuilder.safe_number("not a number") == "0"


class TestCompileBlueprint:
    """Test the full compilation pipeline."""
    
    def test_valid_blueprint(self):
        """Should compile valid blueprint."""
        bp = {
            "name": "Test Plugin",
            "version": "1.0.0",
            "author": "Test",
            "commands": {
                "hello": [
                    {"type": "respond", "message": "Hello {username}!"}
                ]
            }
        }
        result = compile_blueprint_secure(bp)
        assert result.success
        assert "class TestPlugin" in result.code or "class Test_Plugin" in result.code
    
    def test_code_injection_in_message(self):
        """Should block code injection in messages."""
        bp = {
            "name": "Evil Plugin",
            "version": "1.0.0",
            "commands": {
                "evil": [
                    {"type": "respond", "message": "' + eval('malicious') + '"}
                ]
            }
        }
        result = compile_blueprint_secure(bp)
        # Either fails or the message is sanitized
        if result.success:
            assert "eval" not in result.code or result.code.count("eval") == 0
    
    def test_import_injection(self):
        """Should block import injection attempts."""
        bp = {
            "name": "Import Attack",
            "version": "1.0.0",
            "commands": {
                "attack": [
                    {"type": "respond", "message": "__import__('os').system('rm -rf /')"}
                ]
            }
        }
        result = compile_blueprint_secure(bp)
        # Should either fail or heavily sanitize
        if result.success:
            assert "rm -rf" not in result.code
    
    def test_dunder_in_variable_name(self):
        """Should reject dunder in variable names."""
        bp = {
            "name": "Dunder Var",
            "version": "1.0.0",
            "commands": {
                "test": [
                    {"type": "variable_set", "name": "__init__", "value": "evil"}
                ]
            }
        }
        result = compile_blueprint_secure(bp)
        # Variable name should be sanitized
        if result.success:
            assert "__init__" not in result.code
    
    def test_missing_required_fields(self):
        """Should fail on missing required fields."""
        bp = {"commands": {}}  # Missing name
        result = compile_blueprint_secure(bp)
        assert not result.success
    
    def test_too_many_commands(self):
        """Should reject too many commands."""
        bp = {
            "name": "Big Plugin",
            "version": "1.0.0",
            "commands": {f"cmd_{i}": [] for i in range(100)}
        }
        result = compile_blueprint_secure(bp)
        assert not result.success or len(bp["commands"]) <= 50
    
    def test_too_many_steps(self):
        """Should reject too many steps."""
        bp = {
            "name": "Step Overload",
            "version": "1.0.0",
            "commands": {
                "big": [{"type": "respond", "message": f"msg{i}"} for i in range(200)]
            }
        }
        result = compile_blueprint_secure(bp)
        # Should fail or truncate
        assert not result.success or "msg199" not in result.code
    
    def test_delay_limit(self):
        """Should limit delay to max 30 seconds."""
        bp = {
            "name": "Delay Plugin",
            "version": "1.0.0",
            "commands": {
                "wait": [
                    {"type": "delay", "seconds": 1000}
                ]
            }
        }
        result = compile_blueprint_secure(bp)
        if result.success:
            assert "1000" not in result.code
            assert "30" in result.code or "sleep" in result.code
    
    def test_security_hash(self):
        """Should generate security hash."""
        bp = {
            "name": "Hash Test",
            "version": "1.0.0",
            "commands": {"test": []}
        }
        result = compile_blueprint_secure(bp)
        assert result.success
        assert len(result.security_hash) == 16


class TestVisualNodeConversion:
    """Test visual node graph compilation."""
    
    def test_basic_visual_flow(self):
        """Should compile basic visual node flow."""
        bp = {
            "name": "Visual Plugin",
            "version": "1.0.0",
            "commands": {
                "greet": {
                    "nodes": [
                        {
                            "id": "start",
                            "type": "event_start",
                            "data": {}
                        },
                        {
                            "id": "respond1",
                            "type": "respond",
                            "data": {"message": "Hello!"}
                        }
                    ],
                    "connections": [
                        {
                            "fromNode": "start",
                            "fromPin": "start_exec_out",
                            "toNode": "respond1",
                            "toPin": "respond1_exec_in"
                        }
                    ]
                }
            }
        }
        result = compile_blueprint_secure(bp)
        assert result.success
        assert "Hello!" in result.code


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_blueprint(self):
        """Should handle empty blueprint."""
        result = compile_blueprint_secure({})
        assert not result.success
    
    def test_non_dict_input(self):
        """Should reject non-dict input."""
        result = compile_blueprint_secure("not a dict")
        assert not result.success
    
    def test_none_input(self):
        """Should reject None input."""
        result = compile_blueprint_secure(None)
        assert not result.success
    
    def test_unicode_in_message(self):
        """Should handle unicode properly."""
        bp = {
            "name": "Unicode Test",
            "version": "1.0.0",
            "commands": {
                "emoji": [
                    {"type": "respond", "message": "Hello 👋 World! 🎉"}
                ]
            }
        }
        result = compile_blueprint_secure(bp)
        assert result.success
        # Unicode should be preserved or safely encoded
    
    def test_special_chars_in_name(self):
        """Should sanitize special chars in plugin name."""
        bp = {
            "name": "Test<Script>Plugin",
            "version": "1.0.0",
            "commands": {}
        }
        result = compile_blueprint_secure(bp)
        if result.success:
            assert "<Script>" not in result.code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
