"""
Chaos SDK - Blueprint Visual Editor System

This module provides a visual node-based editor for creating plugins
without writing code, similar to Unreal Engine's Blueprints.

Components:
- compiler.py: Original step-based compiler
- compiler_v2.py: Enhanced compiler with graph resolution
- compiler_v3.py: Secure compiler with full validation
- api.py: FastAPI routes for the blueprint editor
- actions_meta.json: Metadata for all available actions
- node_templates.json: Visual node templates for the editor

Usage:
    from chaos_sdk.blueprints import compile_blueprint, compile_blueprint_v2
    from chaos_sdk.blueprints import compile_blueprint_secure  # Recommended!
    from chaos_sdk.blueprints.api import router as blueprint_router
"""

from .compiler import compile_blueprint, validate_blueprint, ALLOWED_ACTIONS
from .compiler_v2 import (
    compile_blueprint_v2,
    CompilationResult as CompilationResultV2,
    CompilerMessage as CompilerMessageV2,
    Severity as SeverityV2,
    GraphResolver,
    ALLOWED_ACTIONS as ALLOWED_ACTIONS_V2,
    ACTION_PERMISSIONS,
)
from .compiler_v3 import (
    compile_blueprint_secure,
    compile_blueprint_v3,
    CompilationResult,
    CompilerMessage,
    Severity,
    SecurityValidator,
    ASTValidator,
    SafeStringBuilder,
    SecureCodeEmitter,
)

__all__ = [
    # Compiler v1 (legacy)
    "compile_blueprint",
    "validate_blueprint",
    "ALLOWED_ACTIONS",
    
    # Compiler v2 (enhanced)
    "compile_blueprint_v2",
    "CompilationResultV2",
    "CompilerMessageV2",
    "SeverityV2",
    "GraphResolver",
    "ALLOWED_ACTIONS_V2",
    "ACTION_PERMISSIONS",
    
    # Compiler v3 (secure - RECOMMENDED)
    "compile_blueprint_secure",
    "compile_blueprint_v3",
    "CompilationResult",
    "CompilerMessage", 
    "Severity",
    "SecurityValidator",
    "ASTValidator",
    "SafeStringBuilder",
    "SecureCodeEmitter",
]

__version__ = "3.0.0"
