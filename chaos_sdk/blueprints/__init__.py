"""
Chaos SDK - Blueprint Visual Editor System

This module provides a visual node-based editor for creating plugins
without writing code, similar to Unreal Engine's Blueprints.

Components:
- compiler.py: Original step-based compiler
- compiler_v2.py: Enhanced compiler with graph resolution
- api.py: FastAPI routes for the blueprint editor
- actions_meta.json: Metadata for all available actions
- node_templates.json: Visual node templates for the editor

Usage:
    from chaos_sdk.blueprints import compile_blueprint, compile_blueprint_v2
    from chaos_sdk.blueprints.api import router as blueprint_router
"""

from .compiler import compile_blueprint, validate_blueprint, ALLOWED_ACTIONS
from .compiler_v2 import (
    compile_blueprint_v2,
    CompilationResult,
    CompilerMessage,
    Severity,
    GraphResolver,
    ALLOWED_ACTIONS as ALLOWED_ACTIONS_V2,
    ACTION_PERMISSIONS,
)

__all__ = [
    # Compiler v1
    "compile_blueprint",
    "validate_blueprint",
    "ALLOWED_ACTIONS",
    
    # Compiler v2
    "compile_blueprint_v2",
    "CompilationResult",
    "CompilerMessage",
    "Severity",
    "GraphResolver",
    "ALLOWED_ACTIONS_V2",
    "ACTION_PERMISSIONS",
]

__version__ = "2.0.0"
