"""
Chaos SDK - Testing Module
==========================

Ferramentas para desenvolvimento e teste local de plugins e mods.

Componentes:
- LocalDevServer: Servidor local para testar plugins
- MockContext: Contexto mock para simulação
- PluginTestCase: Classe base para testes de plugins
- ModTestCase: Classe base para testes de mods
- ChatSimulator: Simulador de chat interativo

Uso Básico:
    # Modo interativo
    chaos dev run meu_plugin.py
    
    # Testar
    chaos dev test meu_plugin.py
    
    # Programático
    from chaos_sdk.testing import LocalDevServer
    
    server = LocalDevServer()
    plugin = server.load_plugin(MyPlugin)
    
    # Simular comando
    result = server.simulate_command("hello", "viewer1", [])
    print(result)

Testes Unitários:
    from chaos_sdk.testing import PluginTestCase
    
    class TestMyPlugin(PluginTestCase):
        plugin_class = MyPlugin
        
        def test_hello(self):
            result = self.execute_command("hello", "viewer1", [])
            self.assertContains(result, "Olá")

Para Mods:
    from chaos_sdk.testing import ModTestCase
    
    class TestMinecraft(ModTestCase):
        plugin_class = MinecraftPlugin
        game_id = "minecraft"
        
        def test_spawn(self):
            result = self.execute_command("spawn", "viewer1", ["zombie"])
            self.assertModReceivedCommand("spawn_enemy")
"""

from .dev_server import (
    LocalDevServer,
    MockContext,
    MockUser,
    ChatSimulator,
    ModSimulator,
)

from .test_runner import (
    PluginTestCase,
    ModTestCase,
    AsyncPluginTestCase,
    quick_test_plugin,
    create_test_suite,
)

__all__ = [
    # Server
    'LocalDevServer',
    'MockContext',
    'MockUser',
    'ChatSimulator',
    'ModSimulator',
    
    # Testing
    'PluginTestCase',
    'ModTestCase',
    'AsyncPluginTestCase',
    'quick_test_plugin',
    'create_test_suite',
]
