"""
Exemplo de Testes Unitários para Plugin
========================================

Este arquivo demonstra como escrever testes para plugins usando PluginTestCase.

Para rodar:
    chaos-dev test dev_plugin_example.py
    
    # Ou com pytest:
    pytest test_example_plugin.py -v
"""

import unittest
import sys
import os

# Adicionar path do SDK se necessário
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chaos_sdk.testing import PluginTestCase, ModTestCase, quick_test_plugin
from examples.dev_plugin_example import ExampleDevPlugin


class TestExampleDevPlugin(PluginTestCase):
    """Testes para o ExampleDevPlugin."""
    
    plugin_class = ExampleDevPlugin
    
    # =========================================================================
    # Testes Básicos
    # =========================================================================
    
    def test_plugin_loads(self):
        """Plugin deve carregar sem erros."""
        self.assertIsNotNone(self._plugin)
        self.assertEqual(self._plugin.name, "Example Dev Plugin")
    
    def test_plugin_has_version(self):
        """Plugin deve ter versão."""
        self.assertEqual(self._plugin.version, "1.0.0")
    
    def test_commands_exist(self):
        """Comandos principais devem existir."""
        self.assertCommandExists("hello")
        self.assertCommandExists("points")
        self.assertCommandExists("give")
        self.assertCommandExists("gamble")
        self.assertCommandExists("rps")
    
    # =========================================================================
    # Testes do Comando Hello
    # =========================================================================
    
    def test_hello_without_args(self):
        """!hello sem args deve saudar o próprio usuário."""
        result = self.execute_command("hello", "viewer1", [])
        self.assertContains(result, "viewer1")
        self.assertContains(result, "👋")
    
    def test_hello_with_target(self):
        """!hello com target deve saudar o target."""
        result = self.execute_command("hello", "viewer1", ["amigo"])
        self.assertContains(result, "amigo")
        self.assertContains(result, "👋")
    
    def test_hello_increments_counter(self):
        """!hello deve incrementar contador."""
        initial = self.get_variable("total_hellos") or 0
        
        self.execute_command("hello", "viewer1", [])
        self.execute_command("hello", "viewer2", [])
        
        new_count = self.get_variable("total_hellos")
        self.assertEqual(new_count, initial + 2)
    
    def test_custom_greeting(self):
        """Saudação customizada deve funcionar."""
        self.set_variable("custom_greeting", "Opa")
        result = self.execute_command("hello", "viewer1", [])
        self.assertContains(result, "Opa")
    
    # =========================================================================
    # Testes do Comando Points
    # =========================================================================
    
    def test_points_shows_amount(self):
        """!points deve mostrar quantidade de pontos."""
        self.set_points("viewer1", 500)
        result = self.execute_command("points", "viewer1", [])
        self.assertContains(result, "500")
        self.assertContains(result, "viewer1")
    
    def test_points_default_value(self):
        """Novo usuário deve ter pontos padrão."""
        result = self.execute_command("points", "new_viewer", [])
        # Pode ser 0 ou valor default do MockContext
        self.assertIsNotNone(result)
    
    # =========================================================================
    # Testes do Comando Give
    # =========================================================================
    
    def test_give_transfers_points(self):
        """!give deve transferir pontos."""
        self.set_points("viewer1", 100)
        self.set_points("viewer2", 50)
        
        result = self.execute_command("give", "viewer1", ["viewer2", "30"])
        
        self.assertContains(result, "✅")
        self.assertEqual(self.get_points("viewer1"), 70)
        self.assertEqual(self.get_points("viewer2"), 80)
    
    def test_give_insufficient_points(self):
        """!give deve falhar se pontos insuficientes."""
        self.set_points("viewer1", 10)
        result = self.execute_command("give", "viewer1", ["viewer2", "100"])
        self.assertContains(result, "❌")
    
    def test_give_requires_args(self):
        """!give sem args deve mostrar erro."""
        result = self.execute_command("give", "viewer1", [])
        self.assertContains(result, "❌")
    
    def test_give_negative_amount(self):
        """!give com valor negativo deve falhar."""
        self.set_points("viewer1", 100)
        result = self.execute_command("give", "viewer1", ["viewer2", "-10"])
        self.assertContains(result, "❌")
    
    # =========================================================================
    # Testes do Comando Gamble
    # =========================================================================
    
    def test_gamble_requires_amount(self):
        """!gamble precisa de quantidade."""
        result = self.execute_command("gamble", "viewer1", [])
        self.assertContains(result, "❌")
    
    def test_gamble_checks_balance(self):
        """!gamble verifica se tem pontos suficientes."""
        self.set_points("viewer1", 10)
        result = self.execute_command("gamble", "viewer1", ["100"])
        self.assertContains(result, "❌")
    
    def test_gamble_works(self):
        """!gamble deve funcionar com pontos suficientes."""
        self.set_points("viewer1", 100)
        result = self.execute_command("gamble", "viewer1", ["10"])
        
        # Deve ganhar ou perder
        self.assertTrue("ganhou" in result.lower() or "perdeu" in result.lower())
    
    # =========================================================================
    # Testes do Comando RPS
    # =========================================================================
    
    def test_rps_requires_choice(self):
        """!rps precisa de escolha."""
        result = self.execute_command("rps", "viewer1", [])
        self.assertContains(result, "❌")
    
    def test_rps_validates_choice(self):
        """!rps valida escolha válida."""
        result = self.execute_command("rps", "viewer1", ["banana"])
        self.assertContains(result, "❌")
    
    def test_rps_accepts_portuguese(self):
        """!rps aceita escolhas em português."""
        result = self.execute_command("rps", "viewer1", ["pedra"])
        self.assertTrue(
            "venceu" in result.lower() or 
            "empate" in result.lower()
        )
    
    def test_rps_accepts_english(self):
        """!rps aceita escolhas em inglês."""
        result = self.execute_command("rps", "viewer1", ["rock"])
        self.assertIsNotNone(result)
    
    # =========================================================================
    # Testes do Comando Stats
    # =========================================================================
    
    def test_stats_shows_info(self):
        """!stats mostra estatísticas."""
        self.set_variable("total_hellos", 42)
        self.set_variable("custom_greeting", "Opa")
        
        result = self.execute_command("stats", "viewer1", [])
        
        self.assertContains(result, "42")
        self.assertContains(result, "Opa")


class TestExampleDevPluginIntegration(PluginTestCase):
    """Testes de integração mais complexos."""
    
    plugin_class = ExampleDevPlugin
    
    def test_full_game_session(self):
        """Simula uma sessão completa de uso."""
        # Setup usuarios
        self.set_points("player1", 1000)
        self.set_points("player2", 500)
        
        # Player1 diz hello
        result = self.execute_command("hello", "player1", [])
        self.assertContains(result, "player1")
        
        # Player1 transfere pontos
        result = self.execute_command("give", "player1", ["player2", "200"])
        self.assertContains(result, "✅")
        
        # Verificar saldos
        self.assertEqual(self.get_points("player1"), 800)
        self.assertEqual(self.get_points("player2"), 700)
        
        # Player2 joga RPS
        result = self.execute_command("rps", "player2", ["pedra"])
        self.assertIsNotNone(result)
        
        # Verificar stats
        result = self.execute_command("stats", "player1", [])
        self.assertContains(result, "saudações")


# Rodar testes diretamente
if __name__ == '__main__':
    unittest.main(verbosity=2)
