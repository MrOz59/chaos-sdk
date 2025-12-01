"""
Exemplo de Plugin para Desenvolvimento Local
=============================================

Este é um exemplo de plugin completo para testar o ambiente de desenvolvimento.

Para testar:
    chaos-dev run example_dev_plugin.py
    
    # Ou via Python:
    python -m chaos_sdk.testing.dev_cli run example_dev_plugin.py
"""

from chaos_sdk import Plugin


class ExampleDevPlugin(Plugin):
    """Plugin de exemplo para testes locais."""
    
    name = "Example Dev Plugin"
    description = "Plugin para testar ambiente de desenvolvimento local"
    version = "1.0.0"
    author = "Chaos Team"
    
    def on_load(self):
        """Chamado quando plugin carrega."""
        print(f"[{self.name}] Plugin carregado!")
        
        # Inicializar variáveis
        self.context.set_variable("total_hellos", 0)
        self.context.set_variable("custom_greeting", "Olá")
    
    def on_unload(self):
        """Chamado quando plugin descarrega."""
        total = self.context.get_variable("total_hellos", 0)
        print(f"[{self.name}] Plugin descarregado! Total de saudações: {total}")
    
    # =========================================================================
    # Comandos
    # =========================================================================
    
    def cmd_hello(self, username: str, args: list) -> str:
        """
        Comando: !hello [nome]
        Saúda o usuário ou uma pessoa específica.
        """
        target = args[0] if args else username
        greeting = self.context.get_variable("custom_greeting", "Olá")
        
        # Incrementar contador
        total = self.context.get_variable("total_hellos", 0)
        self.context.set_variable("total_hellos", total + 1)
        
        return f"{greeting}, {target}! 👋"
    
    def cmd_points(self, username: str, args: list) -> str:
        """
        Comando: !points
        Mostra quantos pontos o usuário tem.
        """
        points = self.context.get_points(username)
        return f"💰 {username}, você tem {points} pontos!"
    
    def cmd_give(self, username: str, args: list) -> str:
        """
        Comando: !give <target> <amount>
        Transfere pontos para outro usuário.
        """
        if len(args) < 2:
            return "❌ Use: !give <usuário> <quantidade>"
        
        target = args[0]
        try:
            amount = int(args[1])
        except ValueError:
            return "❌ Quantidade inválida!"
        
        if amount <= 0:
            return "❌ Quantidade deve ser positiva!"
        
        my_points = self.context.get_points(username)
        if my_points < amount:
            return f"❌ Você só tem {my_points} pontos!"
        
        # Transferir
        self.context.remove_points(username, amount)
        self.context.add_points(target, amount)
        
        return f"✅ {username} deu {amount} pontos para {target}!"
    
    def cmd_gamble(self, username: str, args: list) -> str:
        """
        Comando: !gamble <amount>
        Apostar pontos (50% de chance de dobrar).
        """
        if not args:
            return "❌ Use: !gamble <quantidade>"
        
        try:
            amount = int(args[0])
        except ValueError:
            return "❌ Quantidade inválida!"
        
        if amount <= 0:
            return "❌ Quantidade deve ser positiva!"
        
        my_points = self.context.get_points(username)
        if my_points < amount:
            return f"❌ Você só tem {my_points} pontos!"
        
        import random
        if random.random() < 0.5:
            # Ganhou!
            self.context.add_points(username, amount)
            new_points = self.context.get_points(username)
            return f"🎉 {username} ganhou! +{amount} pontos (total: {new_points})!"
        else:
            # Perdeu!
            self.context.remove_points(username, amount)
            new_points = self.context.get_points(username)
            return f"😢 {username} perdeu {amount} pontos (total: {new_points})"
    
    def cmd_setgreeting(self, username: str, args: list) -> str:
        """
        Comando: !setgreeting <texto>
        Define a saudação personalizada (requer mod).
        """
        if not args:
            return "❌ Use: !setgreeting <saudação>"
        
        # Em produção, verificaria se é mod
        # if not self.context.is_mod(username):
        #     return "❌ Apenas mods podem mudar a saudação!"
        
        greeting = " ".join(args)
        self.context.set_variable("custom_greeting", greeting)
        
        return f"✅ Saudação alterada para: {greeting}"
    
    def cmd_stats(self, username: str, args: list) -> str:
        """
        Comando: !stats
        Mostra estatísticas do plugin.
        """
        total_hellos = self.context.get_variable("total_hellos", 0)
        greeting = self.context.get_variable("custom_greeting", "Olá")
        
        return (
            f"📊 Estatísticas do Plugin:\n"
            f"  • Total de saudações: {total_hellos}\n"
            f"  • Saudação atual: {greeting}"
        )
    
    def cmd_rps(self, username: str, args: list) -> str:
        """
        Comando: !rps <pedra|papel|tesoura>
        Jogo de pedra, papel, tesoura contra o bot.
        """
        if not args:
            return "❌ Use: !rps <pedra|papel|tesoura>"
        
        choices = {
            'pedra': 'pedra',
            'papel': 'papel',
            'tesoura': 'tesoura',
            'rock': 'pedra',
            'paper': 'papel',
            'scissors': 'tesoura',
            'p': 'pedra',
            't': 'tesoura',
        }
        
        user_choice = args[0].lower()
        if user_choice not in choices:
            return "❌ Escolha: pedra, papel ou tesoura"
        
        user_choice = choices[user_choice]
        
        import random
        bot_choice = random.choice(['pedra', 'papel', 'tesoura'])
        
        if user_choice == bot_choice:
            return f"🤝 Empate! Ambos escolheram {user_choice}"
        
        wins = {
            'pedra': 'tesoura',
            'papel': 'pedra',
            'tesoura': 'papel'
        }
        
        if wins[user_choice] == bot_choice:
            # Ganha 10 pontos
            self.context.add_points(username, 10)
            return f"🎉 {username} venceu! {user_choice} > {bot_choice} (+10 pontos)"
        else:
            return f"😢 Bot venceu! {bot_choice} > {user_choice}"
    
    # =========================================================================
    # Eventos
    # =========================================================================
    
    def on_message(self, username: str, message: str):
        """Chamado em toda mensagem do chat."""
        # Exemplo: responder a palavras-chave
        if "chaos" in message.lower():
            print(f"[{self.name}] {username} mencionou chaos!")


# Para teste direto
if __name__ == '__main__':
    # Quick test
    from chaos_sdk.testing import quick_test_plugin
    
    quick_test_plugin(ExampleDevPlugin, {
        'hello': [[], ['amigo']],
        'points': [[]],
        'stats': [[]],
        'rps': [['pedra'], ['papel']],
    })
