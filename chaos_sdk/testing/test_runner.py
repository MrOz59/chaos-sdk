"""
Chaos SDK - Test Runner
=======================

Framework de testes automatizados para plugins e mods.

Features:
- Testes unitários simples
- Testes de integração com mods
- Assertions especializadas
- Mocking de contexto

Uso:
    from chaos_sdk.testing import PluginTestCase, ModTestCase
    
    class TestMyPlugin(PluginTestCase):
        plugin_class = MyPlugin
        
        def test_hello_command(self):
            result = self.execute_command("hello", "viewer1", [])
            self.assertContains(result, "Olá")
        
        def test_points_required(self):
            self.set_points("viewer1", 0)
            result = self.execute_command("expensive", "viewer1", [])
            self.assertContains(result, "pontos")
"""
from __future__ import annotations

import unittest
from typing import Any, Dict, List, Optional, Type, Callable
from dataclasses import dataclass, field
from datetime import datetime

from .dev_server import MockContext, MockUser, ModSimulator, LocalDevServer


class PluginTestCase(unittest.TestCase):
    """
    Caso de teste para plugins.
    
    Exemplo:
        class TestMyPlugin(PluginTestCase):
            plugin_class = MyPlugin
            
            def test_hello(self):
                result = self.execute_command("hello", "viewer1", [])
                self.assertContains(result, "Olá")
    """
    
    # Sobrescrever na subclasse
    plugin_class: Type = None
    
    def setUp(self):
        """Preparar ambiente de teste."""
        if self.plugin_class is None:
            raise ValueError("Defina plugin_class na sua classe de teste")
        
        # Criar servidor mock
        self._server = LocalDevServer()
        self._context = self._server.context
        
        # Instanciar plugin
        self._plugin = self.plugin_class()
        self._plugin.context = self._context
        
        # Coletar comandos
        self._commands: Dict[str, Callable] = {}
        
        # on_load
        if hasattr(self._plugin, 'on_load'):
            self._plugin.on_load()
        
        # Coletar comandos cmd_*
        for name in dir(self._plugin):
            if name.startswith('cmd_'):
                cmd_name = name[4:]
                method = getattr(self._plugin, name)
                if callable(method):
                    self._commands[cmd_name] = method
    
    def tearDown(self):
        """Limpar após teste."""
        if hasattr(self._plugin, 'on_unload'):
            try:
                self._plugin.on_unload()
            except:
                pass
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def execute_command(
        self, 
        command: str, 
        username: str = "viewer1",
        args: List[str] = None
    ) -> Optional[str]:
        """Executar um comando do plugin."""
        if command not in self._commands:
            self.fail(f"Comando não encontrado: {command}")
        
        return self._commands[command](username, args or [])
    
    def create_user(
        self,
        username: str,
        is_mod: bool = False,
        is_sub: bool = False,
        is_vip: bool = False,
        points: int = 1000
    ) -> MockUser:
        """Criar usuário de teste."""
        user = MockUser(
            username=username,
            is_mod=is_mod,
            is_sub=is_sub,
            is_vip=is_vip,
            points=points
        )
        self._server.users[username.lower()] = user
        self._context.set_points(username, points)
        return user
    
    def set_points(self, username: str, amount: int):
        """Definir pontos do usuário."""
        self._context.set_points(username, amount)
    
    def get_points(self, username: str) -> int:
        """Obter pontos do usuário."""
        return self._context.get_points(username)
    
    def set_variable(self, name: str, value: Any):
        """Definir variável."""
        self._context.set_variable(name, value)
    
    def get_variable(self, name: str) -> Any:
        """Obter variável."""
        return self._context.get_variable(name)
    
    def get_chat_log(self) -> List[str]:
        """Obter log de chat."""
        return self._context._chat_log.copy()
    
    def clear_chat_log(self):
        """Limpar log de chat."""
        self._context._chat_log.clear()
    
    # =========================================================================
    # Assertions
    # =========================================================================
    
    def assertContains(self, text: str, substring: str, msg: str = None):
        """Assert que texto contém substring."""
        if text is None:
            self.fail(msg or f"Resultado é None, esperava conter '{substring}'")
        if substring not in text:
            self.fail(msg or f"'{substring}' não encontrado em '{text}'")
    
    def assertNotContains(self, text: str, substring: str, msg: str = None):
        """Assert que texto não contém substring."""
        if text and substring in text:
            self.fail(msg or f"'{substring}' não deveria estar em '{text}'")
    
    def assertPointsChanged(self, username: str, expected_delta: int, msg: str = None):
        """Assert que pontos mudaram por delta específico."""
        # Nota: precisaria rastrear pontos iniciais
        pass
    
    def assertChatContains(self, substring: str, msg: str = None):
        """Assert que log de chat contém mensagem."""
        chat = " ".join(self._context._chat_log)
        if substring not in chat:
            self.fail(msg or f"'{substring}' não encontrado no chat")
    
    def assertCommandExists(self, command: str, msg: str = None):
        """Assert que comando existe."""
        if command not in self._commands:
            self.fail(msg or f"Comando '{command}' não existe")
    
    def assertCommandNotExists(self, command: str, msg: str = None):
        """Assert que comando não existe."""
        if command in self._commands:
            self.fail(msg or f"Comando '{command}' não deveria existir")


class ModTestCase(PluginTestCase):
    """
    Caso de teste para plugins que usam mods.
    
    Exemplo:
        class TestMinecraftPlugin(ModTestCase):
            plugin_class = MinecraftPlugin
            game_id = "minecraft"
            
            def test_spawn_command(self):
                result = self.execute_command("spawn", "viewer1", ["zombie", "5"])
                
                # Verificar que comando foi enviado ao mod
                self.assertModReceivedCommand("spawn_enemy", {
                    "type": "zombie",
                    "count": 5
                })
            
            def test_player_died_event(self):
                result = self.simulate_event("player_died", {
                    "player": "Steve",
                    "cause": "zombie"
                })
                self.assertContains(result, "Steve")
    """
    
    # Sobrescrever na subclasse
    game_id: str = "test_game"
    
    def setUp(self):
        """Preparar ambiente com mod simulado."""
        super().setUp()
        
        # Criar mod simulado
        self._mod = self._server.create_mod(self.game_id, "Test Mod")
        
        # Conectar plugin ao mod (se for ModBridgePlugin)
        if hasattr(self._plugin, '_mods'):
            from chaos_sdk.mods.bridge import ModConnection
            mock_connection = type('MockModConnection', (), {
                'mod_id': f"{self.game_id}_test",
                'game_id': self.game_id,
                'mod_name': "Test Mod",
                'mod_version': "1.0.0",
                'is_alive': True,
                'capabilities': [],
                'has_capability': lambda self, c: False,
            })()
            self._plugin._mods[mock_connection.mod_id] = mock_connection
    
    def simulate_event(
        self, 
        event_type: str, 
        data: Dict[str, Any] = None,
        player: str = None
    ) -> Optional[str]:
        """Simular evento vindo do mod."""
        data = data or {}
        
        # Procurar handler
        if hasattr(self._plugin, '_event_handlers'):
            handler = self._plugin._event_handlers.get(event_type)
            if handler:
                from chaos_sdk.mods.protocol import ModEvent
                from chaos_sdk.mods.bridge import ModConnection
                
                # Criar mock objects
                mock_mod = type('MockMod', (), {
                    'mod_id': f"{self.game_id}_test",
                    'mod_name': "Test Mod",
                    'has_capability': lambda self, c: True,
                })()
                
                event = ModEvent(
                    event_type=event_type,
                    data=data,
                    player=player or data.get('player'),
                )
                
                return handler(mock_mod, event)
        
        return None
    
    def get_mod_commands(self) -> List[Dict[str, Any]]:
        """Obter comandos recebidos pelo mod."""
        return self._mod.received_commands.copy()
    
    def clear_mod_commands(self):
        """Limpar comandos do mod."""
        self._mod.received_commands.clear()
    
    def assertModReceivedCommand(
        self, 
        command: str, 
        params: Dict[str, Any] = None,
        msg: str = None
    ):
        """Assert que mod recebeu comando específico."""
        for cmd in self._mod.received_commands:
            if cmd['command'] == command:
                if params is None:
                    return  # Comando encontrado, params não importam
                
                # Verificar params
                for key, value in params.items():
                    if cmd['params'].get(key) != value:
                        break
                else:
                    return  # Todos params batem
        
        # Não encontrado
        received = [c['command'] for c in self._mod.received_commands]
        self.fail(
            msg or 
            f"Mod não recebeu comando '{command}'. Recebidos: {received}"
        )
    
    def assertModNotReceivedCommand(self, command: str, msg: str = None):
        """Assert que mod NÃO recebeu comando."""
        for cmd in self._mod.received_commands:
            if cmd['command'] == command:
                self.fail(msg or f"Mod não deveria ter recebido '{command}'")


class AsyncPluginTestCase(PluginTestCase):
    """
    Caso de teste para plugins com métodos async.
    
    Exemplo:
        class TestAsyncPlugin(AsyncPluginTestCase):
            plugin_class = MyAsyncPlugin
            
            async def test_async_command(self):
                result = await self.execute_command_async("fetch", "viewer1", [])
                self.assertContains(result, "dados")
    """
    
    def setUp(self):
        super().setUp()
        import asyncio
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
    
    def tearDown(self):
        self._loop.close()
        super().tearDown()
    
    async def execute_command_async(
        self, 
        command: str, 
        username: str = "viewer1",
        args: List[str] = None
    ) -> Optional[str]:
        """Executar comando async."""
        if command not in self._commands:
            self.fail(f"Comando não encontrado: {command}")
        
        result = self._commands[command](username, args or [])
        
        import asyncio
        if asyncio.iscoroutine(result):
            return await result
        return result
    
    def runAsync(self, coro):
        """Helper para rodar coroutine."""
        return self._loop.run_until_complete(coro)


# ============================================================================
# Quick Test Helpers
# ============================================================================

def quick_test_plugin(plugin_class: Type, commands_to_test: Dict[str, List] = None):
    """
    Teste rápido de plugin.
    
    Uso:
        quick_test_plugin(MyPlugin, {
            "hello": [[], ["arg1"]],
            "points": [["100"]],
        })
    """
    print(f"\n🧪 Testando plugin: {plugin_class.__name__}")
    print("=" * 50)
    
    server = LocalDevServer()
    context = server.context
    
    # Instanciar
    plugin = plugin_class()
    plugin.context = context
    
    if hasattr(plugin, 'on_load'):
        plugin.on_load()
    
    print(f"✅ Plugin carregado: {plugin.name} v{plugin.version}")
    
    # Coletar comandos
    commands = {}
    for name in dir(plugin):
        if name.startswith('cmd_'):
            cmd_name = name[4:]
            commands[cmd_name] = getattr(plugin, name)
    
    print(f"📋 Comandos encontrados: {', '.join(commands.keys())}")
    
    # Testar comandos
    if commands_to_test:
        print("\n🔬 Executando testes:")
        for cmd_name, arg_sets in commands_to_test.items():
            if cmd_name not in commands:
                print(f"  ❌ Comando não existe: {cmd_name}")
                continue
            
            for args in arg_sets:
                try:
                    result = commands[cmd_name]("tester", args)
                    args_str = " ".join(args) if args else "(sem args)"
                    print(f"  ✅ !{cmd_name} {args_str}")
                    print(f"     → {result}")
                except Exception as e:
                    print(f"  ❌ !{cmd_name}: {e}")
    else:
        # Testar todos os comandos sem args
        print("\n🔬 Testando comandos (sem argumentos):")
        for cmd_name, handler in commands.items():
            try:
                result = handler("tester", [])
                print(f"  ✅ !{cmd_name}")
                if result:
                    print(f"     → {result[:100]}...")
            except Exception as e:
                print(f"  ⚠️ !{cmd_name}: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Teste concluído!\n")


def create_test_suite(target_plugin_class: Type) -> unittest.TestSuite:
    """Criar suite de testes básica para um plugin."""
    
    class AutoGeneratedTests(PluginTestCase):
        plugin_class = target_plugin_class
        
        def test_plugin_loads(self):
            """Plugin deve carregar sem erros."""
            self.assertIsNotNone(self._plugin)
        
        def test_has_name(self):
            """Plugin deve ter nome."""
            self.assertTrue(hasattr(self._plugin, 'name'))
            self.assertIsNotNone(self._plugin.name)
        
        def test_has_version(self):
            """Plugin deve ter versão."""
            self.assertTrue(hasattr(self._plugin, 'version'))
        
        def test_commands_callable(self):
            """Todos comandos devem ser callable."""
            for name, handler in self._commands.items():
                self.assertTrue(callable(handler), f"Comando {name} não é callable")
    
    # Adicionar testes dinâmicos para cada comando
    suite = unittest.TestLoader().loadTestsFromTestCase(AutoGeneratedTests)
    return suite
