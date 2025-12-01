"""
Sistema de configuração para plugins.

Permite que plugins tenham configurações persistentes e validadas.

Exemplo de uso:

    from chaos_sdk import Plugin
    from chaos_sdk.config import PluginConfig, ConfigField

    class MeuPlugin(Plugin):
        config = PluginConfig(
            prefix=ConfigField(str, default="!", description="Prefixo dos comandos"),
            cooldown=ConfigField(int, default=5, min_value=1, max_value=60),
            enabled_features=ConfigField(list, default=["dice", "poll"]),
            api_key=ConfigField(str, default="", secret=True),
        )
        
        async def on_load(self):
            print(f"Prefixo: {self.config.prefix}")
"""
from typing import Any, Dict, Optional, Type, Union, List
from dataclasses import dataclass, field
import json
import os


@dataclass
class ConfigField:
    """Define um campo de configuração."""
    
    type: Type
    default: Any = None
    description: str = ""
    required: bool = False
    secret: bool = False  # Se True, não mostra no log/UI
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None  # Valores permitidos
    
    def validate(self, value: Any) -> tuple[bool, str]:
        """Valida um valor para este campo."""
        if value is None:
            if self.required:
                return False, "Campo obrigatório"
            return True, ""
        
        # Verificar tipo
        if not isinstance(value, self.type):
            try:
                value = self.type(value)
            except (ValueError, TypeError):
                return False, f"Tipo inválido. Esperado {self.type.__name__}"
        
        # Verificar range numérico
        if self.type in (int, float):
            if self.min_value is not None and value < self.min_value:
                return False, f"Valor mínimo: {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Valor máximo: {self.max_value}"
        
        # Verificar choices
        if self.choices is not None and value not in self.choices:
            return False, f"Valor deve ser um de: {self.choices}"
        
        return True, ""
    
    def coerce(self, value: Any) -> Any:
        """Converte valor para o tipo correto."""
        if value is None:
            return self.default
        try:
            return self.type(value)
        except (ValueError, TypeError):
            return self.default


class PluginConfig:
    """
    Gerenciador de configuração para plugins.
    
    Uso:
        class MeuPlugin(Plugin):
            config = PluginConfig(
                prefix=ConfigField(str, default="!"),
                cooldown=ConfigField(int, default=5),
            )
    """
    
    def __init__(self, **fields: ConfigField):
        self._fields: Dict[str, ConfigField] = fields
        self._values: Dict[str, Any] = {}
        self._plugin_name: str = "unknown"
        self._config_path: Optional[str] = None
        
        # Inicializar com valores default
        for name, field_def in fields.items():
            self._values[name] = field_def.default
    
    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            return super().__getattribute__(name)
        if name in self._values:
            return self._values[name]
        raise AttributeError(f"Config não tem campo '{name}'")
    
    def __setattr__(self, name: str, value: Any):
        if name.startswith('_'):
            super().__setattr__(name, value)
            return
        if name in self._fields:
            field_def = self._fields[name]
            valid, error = field_def.validate(value)
            if not valid:
                raise ValueError(f"Config '{name}': {error}")
            self._values[name] = field_def.coerce(value)
            self._save()
        else:
            super().__setattr__(name, value)
    
    def _bind(self, plugin_name: str, config_dir: str = "config"):
        """Vincula config a um plugin específico."""
        self._plugin_name = plugin_name
        self._config_path = os.path.join(config_dir, f"{plugin_name.lower().replace(' ', '_')}.json")
        self._load()
    
    def _load(self):
        """Carrega configuração do arquivo."""
        if not self._config_path or not os.path.exists(self._config_path):
            return
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for name, value in data.items():
                if name in self._fields:
                    field_def = self._fields[name]
                    valid, _ = field_def.validate(value)
                    if valid:
                        self._values[name] = field_def.coerce(value)
        except Exception:
            pass
    
    def _save(self):
        """Salva configuração no arquivo."""
        if not self._config_path:
            return
        
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            
            # Não salvar campos secretos
            data = {
                name: value 
                for name, value in self._values.items()
                if not self._fields[name].secret
            }
            
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def get(self, name: str, default: Any = None) -> Any:
        """Obtém valor de configuração."""
        return self._values.get(name, default)
    
    def set(self, name: str, value: Any):
        """Define valor de configuração."""
        setattr(self, name, value)
    
    def reset(self, name: str = None):
        """Reseta configuração para valor default."""
        if name:
            if name in self._fields:
                self._values[name] = self._fields[name].default
        else:
            for field_name, field_def in self._fields.items():
                self._values[field_name] = field_def.default
        self._save()
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Exporta configuração como dicionário."""
        return {
            name: value 
            for name, value in self._values.items()
            if include_secrets or not self._fields[name].secret
        }
    
    def get_schema(self) -> Dict[str, Dict]:
        """Retorna schema dos campos para UI."""
        schema = {}
        for name, field_def in self._fields.items():
            schema[name] = {
                "type": field_def.type.__name__,
                "default": field_def.default,
                "description": field_def.description,
                "required": field_def.required,
                "secret": field_def.secret,
                "min": field_def.min_value,
                "max": field_def.max_value,
                "choices": field_def.choices,
            }
        return schema
    
    def validate_all(self) -> Dict[str, str]:
        """Valida todos os campos e retorna erros."""
        errors = {}
        for name, field_def in self._fields.items():
            valid, error = field_def.validate(self._values.get(name))
            if not valid:
                errors[name] = error
        return errors


# Helpers para tipos comuns
def string_field(default: str = "", description: str = "", **kwargs) -> ConfigField:
    return ConfigField(str, default=default, description=description, **kwargs)

def int_field(default: int = 0, description: str = "", **kwargs) -> ConfigField:
    return ConfigField(int, default=default, description=description, **kwargs)

def float_field(default: float = 0.0, description: str = "", **kwargs) -> ConfigField:
    return ConfigField(float, default=default, description=description, **kwargs)

def bool_field(default: bool = False, description: str = "", **kwargs) -> ConfigField:
    return ConfigField(bool, default=default, description=description, **kwargs)

def list_field(default: list = None, description: str = "", **kwargs) -> ConfigField:
    return ConfigField(list, default=default or [], description=description, **kwargs)

def choice_field(choices: List[Any], default: Any = None, description: str = "", **kwargs) -> ConfigField:
    return ConfigField(type(choices[0]) if choices else str, default=default or choices[0], 
                       description=description, choices=choices, **kwargs)

def secret_field(default: str = "", description: str = "", **kwargs) -> ConfigField:
    return ConfigField(str, default=default, description=description, secret=True, **kwargs)
