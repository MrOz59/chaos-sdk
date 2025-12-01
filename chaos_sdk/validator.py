"""
Validador de plugins para garantir compatibilidade e segurança.

Uso:
    python -m chaos_sdk.validator /caminho/para/plugin.py
"""
import ast
import sys
import os
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Resultado de validação."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    info: Dict[str, Any]


# Imports proibidos por segurança
FORBIDDEN_IMPORTS = {
    'os.system', 'subprocess', 'eval', 'exec', 'compile',
    'pickle', 'marshal', 'ctypes', 'multiprocessing',
    '__import__', 'importlib.import_module',
}

# Imports perigosos (warning)
DANGEROUS_IMPORTS = {
    'os', 'sys', 'socket', 'requests', 'urllib', 'http',
    'shutil', 'pathlib', 'glob', 'tempfile',
}

# Permissões válidas
VALID_PERMISSIONS = {
    'core:log',
    'chat:send',
    'points:read', 'points:write',
    'voting:read', 'voting:vote', 'voting:manage',
    'audio:play', 'audio:tts', 'audio:control',
    'minigames:play',
    'leaderboard:read',
    'macro:enqueue',
    'config:read', 'config:write',
}


class PluginValidator:
    """Valida arquivos de plugin."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: Dict[str, Any] = {}
    
    def validate(self) -> ValidationResult:
        """Executa validação completa."""
        self.errors = []
        self.warnings = []
        self.info = {}
        
        # Verificar se arquivo existe
        if not os.path.exists(self.file_path):
            self.errors.append(f"Arquivo não encontrado: {self.file_path}")
            return self._result()
        
        # Ler conteúdo
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.errors.append(f"Erro ao ler arquivo: {e}")
            return self._result()
        
        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            self.errors.append(f"Erro de sintaxe linha {e.lineno}: {e.msg}")
            return self._result()
        
        # Validações
        self._check_imports(tree)
        self._check_classes(tree)
        self._check_dangerous_patterns(content)
        self._check_best_practices(tree, content)
        
        return self._result()
    
    def _result(self) -> ValidationResult:
        return ValidationResult(
            valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings,
            info=self.info
        )
    
    def _check_imports(self, tree: ast.AST):
        """Verifica imports."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_import_name(alias.name, node.lineno)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._check_import_name(node.module, node.lineno)
                    for alias in node.names:
                        full_name = f"{node.module}.{alias.name}"
                        self._check_import_name(full_name, node.lineno)
    
    def _check_import_name(self, name: str, lineno: int):
        """Verifica um nome de import."""
        if name in FORBIDDEN_IMPORTS or any(name.startswith(f) for f in FORBIDDEN_IMPORTS):
            self.errors.append(f"Linha {lineno}: Import proibido '{name}'")
        elif name in DANGEROUS_IMPORTS:
            self.warnings.append(f"Linha {lineno}: Import potencialmente perigoso '{name}'")
    
    def _check_classes(self, tree: ast.AST):
        """Verifica classes de plugin."""
        plugin_classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Verificar se herda de BasePlugin ou Plugin
                bases = [self._get_base_name(b) for b in node.bases]
                if any(b in ('BasePlugin', 'Plugin', 'GamePlugin') for b in bases):
                    plugin_classes.append(node)
                    self._validate_plugin_class(node)
        
        if not plugin_classes:
            self.warnings.append("Nenhuma classe de plugin encontrada (herde de Plugin ou BasePlugin)")
        
        self.info['plugin_count'] = len(plugin_classes)
        self.info['plugins'] = [c.name for c in plugin_classes]
    
    def _get_base_name(self, base: ast.expr) -> str:
        """Extrai nome da classe base."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return base.attr
        return ""
    
    def _validate_plugin_class(self, cls: ast.ClassDef):
        """Valida uma classe de plugin."""
        has_name = False
        has_version = False
        has_on_load = False
        commands = []
        permissions = []
        
        for node in cls.body:
            # Verificar atributos
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == 'name':
                            has_name = True
                            if isinstance(node.value, ast.Constant):
                                self.info['name'] = node.value.value
                        elif target.id == 'version':
                            has_version = True
                            if isinstance(node.value, ast.Constant):
                                self.info['version'] = node.value.value
                        elif target.id == 'required_permissions':
                            if isinstance(node.value, ast.Tuple):
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Constant):
                                        permissions.append(elt.value)
            
            # Verificar métodos
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == 'on_load':
                    has_on_load = True
                
                # Verificar decoradores
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call):
                        func = dec.func
                        if isinstance(func, ast.Name) and func.id == 'command':
                            if dec.args and isinstance(dec.args[0], ast.Constant):
                                commands.append(dec.args[0].value)
        
        # Validações
        if not has_name:
            self.warnings.append(f"Classe {cls.name}: atributo 'name' não definido")
        if not has_version:
            self.warnings.append(f"Classe {cls.name}: atributo 'version' não definido")
        if not has_on_load:
            self.warnings.append(f"Classe {cls.name}: método 'on_load' não implementado")
        
        # Validar permissões
        for perm in permissions:
            if perm not in VALID_PERMISSIONS:
                self.warnings.append(f"Permissão desconhecida: {perm}")
        
        self.info['commands'] = commands
        self.info['permissions'] = permissions
    
    def _check_dangerous_patterns(self, content: str):
        """Verifica padrões perigosos no código."""
        dangerous_patterns = [
            (r'\beval\s*\(', "Uso de eval() detectado"),
            (r'\bexec\s*\(', "Uso de exec() detectado"),
            (r'\b__import__\s*\(', "Uso de __import__() detectado"),
            (r'\bopen\s*\([^)]*["\']w', "Escrita em arquivo detectada"),
            (r'os\.remove|os\.unlink|shutil\.rmtree', "Remoção de arquivos detectada"),
        ]
        
        import re
        for pattern, message in dangerous_patterns:
            if re.search(pattern, content):
                self.warnings.append(message)
    
    def _check_best_practices(self, tree: ast.AST, content: str):
        """Verifica boas práticas."""
        lines = content.split('\n')
        
        # Verificar docstring
        if not ast.get_docstring(tree):
            self.warnings.append("Plugin sem docstring no topo do arquivo")
        
        # Verificar tamanho
        if len(lines) > 1000:
            self.warnings.append(f"Plugin muito grande ({len(lines)} linhas). Considere dividir em módulos.")
        
        # Verificar funções muito longas
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                if func_lines > 100:
                    self.warnings.append(f"Função '{node.name}' muito longa ({func_lines} linhas)")


def validate_plugin(file_path: str) -> ValidationResult:
    """Valida um arquivo de plugin."""
    validator = PluginValidator(file_path)
    return validator.validate()


def main():
    """CLI principal."""
    if len(sys.argv) < 2:
        print("Uso: python -m chaos_sdk.validator <arquivo.py>")
        print("")
        print("Valida um plugin para garantir compatibilidade e segurança.")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
    
    result = validate_plugin(file_path)
    
    print("=" * 50)
    print(f"📋 Validação: {os.path.basename(file_path)}")
    print("=" * 50)
    
    if result.info:
        print(f"\n📦 Plugin: {result.info.get('name', 'N/A')} v{result.info.get('version', 'N/A')}")
        if result.info.get('commands'):
            print(f"🎮 Comandos: {', '.join(result.info['commands'])}")
        if result.info.get('permissions'):
            print(f"🔐 Permissões: {', '.join(result.info['permissions'])}")
    
    if result.errors:
        print(f"\n❌ ERROS ({len(result.errors)}):")
        for error in result.errors:
            print(f"   • {error}")
    
    if result.warnings:
        print(f"\n⚠️  AVISOS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"   • {warning}")
    
    print("")
    if result.valid:
        print("✅ Plugin válido!")
    else:
        print("❌ Plugin com erros - corrija antes de enviar")
    
    sys.exit(0 if result.valid else 1)


if __name__ == "__main__":
    main()
