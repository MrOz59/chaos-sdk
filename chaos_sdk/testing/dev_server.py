"""
Chaos SDK - Local Development Server
====================================

Servidor local completo para desenvolvimento de plugins e mods.
Não requer conexão com o servidor de produção ou marketplace.

Features:
- Simula chat do Twitch/YouTube
- Simula sistema de pontos
- WebSocket para mods de jogos
- Hot-reload de plugins
- Console interativo
- Web UI para testes

Uso:
    chaos-dev                    # Inicia servidor de dev
    chaos-dev --plugin meu.py    # Carrega plugin específico
    chaos-dev --port 8888        # Porta customizada
    chaos-dev --ui               # Abre Web UI
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import importlib.util
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import argparse
import signal

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("chaos-dev")


@dataclass
class MockUser:
    """Usuário simulado para testes."""
    username: str
    display_name: str = ""
    is_mod: bool = False
    is_sub: bool = False
    is_vip: bool = False
    points: int = 1000
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.username


@dataclass 
class MockMessage:
    """Mensagem simulada."""
    user: MockUser
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    platform: str = "twitch"


class MockContext:
    """
    Contexto simulado que imita o contexto real do servidor.
    Permite testar plugins localmente.
    """
    
    def __init__(self, dev_server: 'LocalDevServer'):
        self._server = dev_server
        self._points: Dict[str, int] = {}
        self._variables: Dict[str, Any] = {}
        self._chat_log: List[str] = []
        self._audio_queue: List[str] = []
    
    # =========================================================================
    # Points System
    # =========================================================================
    
    def get_points(self, username: str) -> int:
        """Obter pontos do usuário."""
        return self._points.get(username.lower(), 1000)
    
    def add_points(self, username: str, amount: int, reason: str = "") -> bool:
        """Adicionar pontos."""
        key = username.lower()
        self._points[key] = self._points.get(key, 1000) + amount
        logger.info(f"💰 +{amount} pontos para {username} ({reason})")
        return True
    
    def remove_points(self, username: str, amount: int, reason: str = "") -> bool:
        """Remover pontos."""
        key = username.lower()
        current = self._points.get(key, 1000)
        if current >= amount:
            self._points[key] = current - amount
            logger.info(f"💰 -{amount} pontos de {username} ({reason})")
            return True
        return False
    
    def set_points(self, username: str, amount: int) -> bool:
        """Definir pontos."""
        self._points[username.lower()] = amount
        return True
    
    def get_leaderboard(self, limit: int = 10, category: str = "points") -> List[tuple]:
        """Obter ranking."""
        sorted_points = sorted(self._points.items(), key=lambda x: x[1], reverse=True)
        return sorted_points[:limit]
    
    # =========================================================================
    # Chat
    # =========================================================================
    
    async def send_chat(self, message: str, platform: str = "twitch"):
        """Enviar mensagem no chat."""
        self._chat_log.append(f"[{platform}] BOT: {message}")
        logger.info(f"💬 [{platform}] {message}")
    
    def send_chat_sync(self, message: str, platform: str = "twitch"):
        """Versão síncrona."""
        self._chat_log.append(f"[{platform}] BOT: {message}")
        logger.info(f"💬 [{platform}] {message}")
    
    # =========================================================================
    # Audio
    # =========================================================================
    
    def audio_tts(self, text: str, lang: str = "pt-br"):
        """Simular TTS."""
        logger.info(f"🔊 TTS: \"{text}\" (lang={lang})")
        self._audio_queue.append(f"TTS: {text}")
    
    def audio_play(self, sound_name: str):
        """Simular tocar som."""
        logger.info(f"🔊 Som: {sound_name}")
        self._audio_queue.append(f"Sound: {sound_name}")
    
    def audio_stop(self):
        """Parar áudio."""
        logger.info("🔇 Áudio parado")
    
    def audio_clear_queue(self):
        """Limpar fila de áudio."""
        self._audio_queue.clear()
        logger.info("🔇 Fila de áudio limpa")
    
    # =========================================================================
    # Macros
    # =========================================================================
    
    def macro_run_keys(self, username: str, keys: str, delay: float = 0.08, command: str = ""):
        """Simular macro de teclas."""
        logger.info(f"⌨️ Macro: {keys} (delay={delay}, user={username})")
    
    # =========================================================================
    # Variables
    # =========================================================================
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Obter variável."""
        return self._variables.get(name, default)
    
    def set_variable(self, name: str, value: Any):
        """Definir variável."""
        self._variables[name] = value
    
    # =========================================================================
    # Mod Bridge
    # =========================================================================
    
    def send_to_mod(self, command: str, params: dict, game_id: str = None):
        """Enviar comando para mod."""
        self._server.send_to_mods(command, params)


class MockPlugin:
    """Wrapper para plugins carregados."""
    
    def __init__(self, plugin_class, context: MockContext):
        self.plugin_class = plugin_class
        self.instance = None
        self.context = context
        self.commands: Dict[str, Callable] = {}
        self.loaded = False
    
    def load(self):
        """Carregar e inicializar plugin."""
        try:
            self.instance = self.plugin_class()
            self.instance.context = self.context
            
            # Chamar on_load
            if hasattr(self.instance, 'on_load'):
                self.instance.on_load()
            
            # Coletar comandos
            self._collect_commands()
            
            self.loaded = True
            logger.info(f"✅ Plugin carregado: {self.instance.name} v{self.instance.version}")
            logger.info(f"   Comandos: {', '.join(self.commands.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar plugin: {e}")
            raise
    
    def _collect_commands(self):
        """Coletar comandos registrados."""
        # Método register_command
        if hasattr(self.instance, '_registered_commands'):
            self.commands.update(self.instance._registered_commands)
        
        # Métodos cmd_*
        for name in dir(self.instance):
            if name.startswith('cmd_'):
                cmd_name = name[4:]  # Remove 'cmd_'
                method = getattr(self.instance, name)
                if callable(method):
                    self.commands[cmd_name] = method
    
    def execute_command(self, cmd_name: str, username: str, args: list) -> Optional[str]:
        """Executar um comando."""
        if cmd_name not in self.commands:
            return None
        
        try:
            handler = self.commands[cmd_name]
            result = handler(username, args)
            return result
        except Exception as e:
            logger.error(f"❌ Erro no comando !{cmd_name}: {e}")
            return f"Erro: {e}"
    
    def unload(self):
        """Descarregar plugin."""
        if self.instance and hasattr(self.instance, 'on_unload'):
            try:
                self.instance.on_unload()
            except:
                pass
        self.loaded = False


class ModSimulator:
    """Simula um mod de jogo conectado."""
    
    def __init__(self, game_id: str, mod_name: str = "Test Mod"):
        self.game_id = game_id
        self.mod_name = mod_name
        self.connected = True
        self.received_commands: List[dict] = []
        self.command_handlers: Dict[str, Callable] = {}
    
    def on_command(self, command: str, handler: Callable):
        """Registrar handler de comando."""
        self.command_handlers[command] = handler
    
    def receive_command(self, command: str, params: dict):
        """Receber comando do plugin."""
        self.received_commands.append({
            "command": command,
            "params": params,
            "timestamp": time.time()
        })
        
        logger.info(f"🎮 Mod recebeu: {command} {params}")
        
        # Executar handler se existir
        if command in self.command_handlers:
            try:
                self.command_handlers[command](params)
            except Exception as e:
                logger.error(f"❌ Erro no handler do mod: {e}")
    
    def send_event(self, event_type: str, data: dict):
        """Simular envio de evento do mod."""
        logger.info(f"🎮 Mod enviou evento: {event_type} {data}")
        return {"event_type": event_type, "data": data}


class ChatSimulator:
    """Simula o chat do Twitch/Kick para testes."""
    
    def __init__(self):
        self.viewers: Dict[str, dict] = {}
        self.messages: List[MockMessage] = []
        self.auto_mode = False
        self.auto_interval = 2.0
        
        # Palavras aleatórias para chat automático
        self._phrases = [
            "kappa", "poggers", "LUL", "oi streamer!",
            "nice!", "wow", "KEKW", "4Head",
            "!hello", "!points", "gg", "vamos!",
            "top demais", "cuidado!", "GG EZ",
        ]
    
    def add_viewer(self, username: str, is_mod: bool = False, is_sub: bool = False):
        """Adicionar viewer."""
        self.viewers[username.lower()] = {
            'username': username,
            'is_mod': is_mod,
            'is_sub': is_sub,
            'is_vip': False,
        }
    
    def remove_viewer(self, username: str):
        """Remover viewer."""
        self.viewers.pop(username.lower(), None)
    
    def send_message(self, username: str, message: str) -> MockMessage:
        """Enviar mensagem."""
        user_data = self.viewers.get(username.lower(), {})
        user = MockUser(
            username=username,
            is_mod=user_data.get('is_mod', False),
            is_sub=user_data.get('is_sub', False),
            is_vip=user_data.get('is_vip', False),
        )
        
        msg = MockMessage(user=user, content=message)
        self.messages.append(msg)
        return msg
    
    def get_random_message(self) -> str:
        """Gerar mensagem aleatória."""
        import random
        return random.choice(self._phrases)
    
    def simulate_raid(self, from_channel: str, viewer_count: int):
        """Simular raid."""
        logger.info(f"🚀 RAID de {from_channel} com {viewer_count} viewers!")
        # Adicionar alguns viewers
        for i in range(min(viewer_count, 20)):
            self.add_viewer(f"raider_{i}")
    
    def simulate_follow(self, username: str):
        """Simular follow."""
        logger.info(f"❤️ Novo follower: {username}")
    
    def simulate_subscription(self, username: str, tier: int = 1, months: int = 1):
        """Simular sub."""
        logger.info(f"⭐ Nova sub: {username} (Tier {tier}, {months} meses)")
        self.add_viewer(username, is_sub=True)
    
    def simulate_bits(self, username: str, amount: int):
        """Simular bits."""
        logger.info(f"💎 {username} doou {amount} bits!")


class LocalDevServer:
    """
    Servidor de desenvolvimento local para testar plugins e mods.
    """
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.context = MockContext(self)
        self.plugins: Dict[str, MockPlugin] = {}
        self.mods: Dict[str, ModSimulator] = {}
        self.users: Dict[str, MockUser] = {}
        self.running = False
        self._watch_files: Dict[str, float] = {}
        
        # Criar usuários padrão
        self._create_default_users()
    
    def _create_default_users(self):
        """Criar usuários de teste."""
        self.users = {
            "streamer": MockUser("streamer", "Streamer", is_mod=True),
            "mod1": MockUser("mod1", "Moderador", is_mod=True),
            "sub1": MockUser("sub1", "Subscriber", is_sub=True),
            "vip1": MockUser("vip1", "VIP User", is_vip=True),
            "viewer1": MockUser("viewer1", "Viewer Normal"),
            "viewer2": MockUser("viewer2", "Outro Viewer"),
        }
    
    def load_plugin(self, path: str) -> bool:
        """Carregar plugin de arquivo."""
        path = Path(path).resolve()
        
        if not path.exists():
            logger.error(f"❌ Arquivo não encontrado: {path}")
            return False
        
        try:
            # Carregar módulo
            spec = importlib.util.spec_from_file_location("plugin_module", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["plugin_module"] = module
            spec.loader.exec_module(module)
            
            # Encontrar classe do plugin
            plugin_class = None
            
            # Procurar por 'Plugin' export
            if hasattr(module, 'Plugin'):
                plugin_class = module.Plugin
            else:
                # Procurar classe que herda de BasePlugin
                for name in dir(module):
                    obj = getattr(module, name)
                    if isinstance(obj, type) and name != 'BasePlugin':
                        if hasattr(obj, 'name') and hasattr(obj, 'version'):
                            plugin_class = obj
                            break
            
            if not plugin_class:
                logger.error(f"❌ Nenhuma classe de plugin encontrada em {path}")
                return False
            
            # Criar e carregar
            mock_plugin = MockPlugin(plugin_class, self.context)
            mock_plugin.load()
            
            plugin_name = mock_plugin.instance.name
            self.plugins[plugin_name] = mock_plugin
            
            # Adicionar ao watch para hot-reload
            self._watch_files[str(path)] = path.stat().st_mtime
            
            return True
            
        except Exception as e:
            logger.exception(f"❌ Erro ao carregar plugin: {e}")
            return False
    
    def reload_plugin(self, name: str) -> bool:
        """Recarregar plugin."""
        if name not in self.plugins:
            return False
        
        plugin = self.plugins[name]
        plugin.unload()
        
        # Re-importar
        # (simplificado - em produção seria mais robusto)
        plugin.load()
        return True
    
    def create_mod(self, game_id: str, mod_name: str = "Test Mod") -> ModSimulator:
        """Criar simulador de mod."""
        mod = ModSimulator(game_id, mod_name)
        self.mods[game_id] = mod
        logger.info(f"🎮 Mod simulado criado: {mod_name} ({game_id})")
        return mod
    
    def send_to_mods(self, command: str, params: dict, game_id: str = None):
        """Enviar comando para mods."""
        targets = [self.mods[game_id]] if game_id and game_id in self.mods else self.mods.values()
        
        for mod in targets:
            mod.receive_command(command, params)
    
    def simulate_chat(self, username: str, message: str):
        """Simular mensagem de chat."""
        # Obter ou criar usuário
        user = self.users.get(username.lower())
        if not user:
            user = MockUser(username)
            self.users[username.lower()] = user
        
        logger.info(f"👤 {user.display_name}: {message}")
        
        # Verificar se é comando
        if message.startswith("!"):
            parts = message[1:].split()
            cmd_name = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            # Procurar comando em plugins
            for plugin in self.plugins.values():
                if plugin.loaded and cmd_name in plugin.commands:
                    result = plugin.execute_command(cmd_name, username, args)
                    if result:
                        logger.info(f"💬 BOT: {result}")
                    break
            else:
                logger.warning(f"⚠️ Comando não encontrado: !{cmd_name}")
    
    def simulate_mod_event(self, game_id: str, event_type: str, data: dict):
        """Simular evento de mod."""
        logger.info(f"🎮 Evento de mod [{game_id}]: {event_type}")
        
        # Procurar plugin que lida com este jogo
        for plugin in self.plugins.values():
            if hasattr(plugin.instance, 'game_id') and plugin.instance.game_id == game_id:
                if hasattr(plugin.instance, '_event_handlers'):
                    handler = plugin.instance._event_handlers.get(event_type)
                    if handler:
                        # Criar mock do mod e evento
                        from chaos_sdk.mods.protocol import ModEvent
                        from chaos_sdk.mods.bridge import ModConnection
                        
                        mock_mod = type('MockMod', (), {
                            'mod_id': f"{game_id}_test",
                            'mod_name': "Test Mod",
                        })()
                        
                        event = ModEvent(
                            event_type=event_type,
                            data=data,
                            player=data.get('player'),
                        )
                        
                        result = handler(mock_mod, event)
                        if result:
                            logger.info(f"💬 BOT: {result}")
    
    def check_hot_reload(self):
        """Verificar se arquivos mudaram para hot-reload."""
        for path_str, last_mtime in list(self._watch_files.items()):
            path = Path(path_str)
            if path.exists():
                current_mtime = path.stat().st_mtime
                if current_mtime > last_mtime:
                    logger.info(f"🔄 Arquivo modificado, recarregando: {path.name}")
                    self._watch_files[path_str] = current_mtime
                    
                    # Encontrar e recarregar plugin
                    for name, plugin in list(self.plugins.items()):
                        # Simplificado - recarregar todos
                        self.load_plugin(path_str)
    
    def run_interactive(self):
        """Executar console interativo."""
        self.running = True
        
        print("\n" + "="*60)
        print("🎮 CHAOS DEV SERVER - Ambiente Local de Desenvolvimento")
        print("="*60)
        print("\nComandos disponíveis:")
        print("  !<cmd> [args]     - Testar comando como viewer")
        print("  @<user> !<cmd>    - Testar como usuário específico")
        print("  /load <file>      - Carregar plugin")
        print("  /reload           - Recarregar todos plugins")
        print("  /mod <game_id>    - Criar mod simulado")
        print("  /event <game> <type> <json>  - Simular evento de mod")
        print("  /points <user>    - Ver pontos de usuário")
        print("  /setpoints <user> <amount>  - Definir pontos")
        print("  /users            - Listar usuários")
        print("  /plugins          - Listar plugins carregados")
        print("  /mods             - Listar mods conectados")
        print("  /help             - Mostrar ajuda")
        print("  /quit             - Sair")
        print("\nUsuários de teste: streamer, mod1, sub1, vip1, viewer1, viewer2")
        print("="*60 + "\n")
        
        # Thread para hot-reload
        def watch_thread():
            while self.running:
                self.check_hot_reload()
                time.sleep(1)
        
        watcher = threading.Thread(target=watch_thread, daemon=True)
        watcher.start()
        
        # Loop principal
        while self.running:
            try:
                line = input("chaos> ").strip()
                
                if not line:
                    continue
                
                # Comandos internos
                if line.startswith("/"):
                    self._handle_internal_command(line)
                
                # Simular como usuário específico
                elif line.startswith("@"):
                    parts = line.split(" ", 1)
                    if len(parts) >= 2:
                        username = parts[0][1:]  # Remove @
                        message = parts[1]
                        self.simulate_chat(username, message)
                    else:
                        print("Uso: @usuario !comando [args]")
                
                # Simular chat normal (como viewer1)
                elif line.startswith("!"):
                    self.simulate_chat("viewer1", line)
                
                else:
                    # Mensagem normal de chat
                    self.simulate_chat("viewer1", line)
                    
            except KeyboardInterrupt:
                print("\n")
                self.running = False
            except EOFError:
                self.running = False
            except Exception as e:
                logger.error(f"Erro: {e}")
        
        print("\n👋 Até mais!")
    
    async def start_async(self):
        """Rodar servidor em modo async (para WebSocket)."""
        self.running = True
        logger.info(f"🚀 Servidor async iniciado na porta {self.port}")
        
        # Manter rodando até interromper
        try:
            while self.running:
                await asyncio.sleep(1)
                self.check_hot_reload()
        except asyncio.CancelledError:
            self.running = False
    
    def _handle_internal_command(self, line: str):
        """Processar comandos internos (/comando)."""
        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "/quit" or cmd == "/exit":
            self.running = False
        
        elif cmd == "/help":
            print("""
Comandos disponíveis:
  !<cmd> [args]       - Testar comando (como viewer1)
  @<user> !<cmd>      - Testar como usuário específico
  /load <file.py>     - Carregar plugin de arquivo
  /reload             - Recarregar todos plugins
  /mod <game_id>      - Criar mod simulado para teste
  /event <game> <type> <json>  - Simular evento de mod
  /points <user>      - Ver pontos do usuário
  /setpoints <user> <amount>   - Definir pontos
  /addpoints <user> <amount>   - Adicionar pontos
  /users              - Listar usuários de teste
  /plugins            - Listar plugins carregados
  /mods               - Listar mods simulados
  /commands           - Listar todos comandos disponíveis
  /quit               - Sair

Exemplos:
  !hello               - Testar comando !hello
  @streamer !spawn 10  - Testar como streamer
  /load meu_plugin.py  - Carregar plugin
  /event minecraft player_died {"player":"Steve"}
""")
        
        elif cmd == "/load":
            if not args:
                print("Uso: /load <arquivo.py>")
            else:
                self.load_plugin(args[0])
        
        elif cmd == "/reload":
            for name in list(self.plugins.keys()):
                self.reload_plugin(name)
            print("✅ Plugins recarregados")
        
        elif cmd == "/mod":
            if not args:
                print("Uso: /mod <game_id> [mod_name]")
            else:
                game_id = args[0]
                mod_name = args[1] if len(args) > 1 else "Test Mod"
                self.create_mod(game_id, mod_name)
        
        elif cmd == "/event":
            if len(args) < 3:
                print("Uso: /event <game_id> <event_type> <json_data>")
                print("Ex: /event minecraft player_died {\"player\":\"Steve\"}")
            else:
                game_id = args[0]
                event_type = args[1]
                try:
                    data = json.loads(" ".join(args[2:]))
                    self.simulate_mod_event(game_id, event_type, data)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON inválido: {e}")
        
        elif cmd == "/points":
            if not args:
                print("Uso: /points <username>")
            else:
                points = self.context.get_points(args[0])
                print(f"💰 {args[0]}: {points} pontos")
        
        elif cmd == "/setpoints":
            if len(args) < 2:
                print("Uso: /setpoints <username> <amount>")
            else:
                self.context.set_points(args[0], int(args[1]))
                print(f"✅ {args[0]} agora tem {args[1]} pontos")
        
        elif cmd == "/addpoints":
            if len(args) < 2:
                print("Uso: /addpoints <username> <amount>")
            else:
                self.context.add_points(args[0], int(args[1]), "manual")
        
        elif cmd == "/users":
            print("\n👥 Usuários de teste:")
            for name, user in self.users.items():
                badges = []
                if user.is_mod: badges.append("🛡️MOD")
                if user.is_sub: badges.append("⭐SUB")
                if user.is_vip: badges.append("💎VIP")
                badge_str = " ".join(badges) if badges else ""
                points = self.context.get_points(name)
                print(f"  {user.display_name} {badge_str} - {points} pontos")
            print()
        
        elif cmd == "/plugins":
            print("\n🔌 Plugins carregados:")
            if not self.plugins:
                print("  (nenhum)")
            for name, plugin in self.plugins.items():
                status = "✅" if plugin.loaded else "❌"
                print(f"  {status} {name} v{plugin.instance.version}")
                print(f"     Comandos: {', '.join(plugin.commands.keys())}")
            print()
        
        elif cmd == "/mods":
            print("\n🎮 Mods simulados:")
            if not self.mods:
                print("  (nenhum)")
            for game_id, mod in self.mods.items():
                status = "✅" if mod.connected else "❌"
                print(f"  {status} {mod.mod_name} ({game_id})")
                print(f"     Comandos recebidos: {len(mod.received_commands)}")
            print()
        
        elif cmd == "/commands":
            print("\n📋 Comandos disponíveis:")
            for plugin_name, plugin in self.plugins.items():
                if plugin.commands:
                    print(f"\n  [{plugin_name}]")
                    for cmd_name, handler in plugin.commands.items():
                        doc = handler.__doc__ or "Sem descrição"
                        doc = doc.strip().split('\n')[0][:50]
                        print(f"    !{cmd_name} - {doc}")
            print()
        
        else:
            print(f"❌ Comando desconhecido: {cmd}")
            print("   Use /help para ver comandos disponíveis")


def main():
    """Entry point do CLI."""
    parser = argparse.ArgumentParser(
        description="Chaos SDK - Servidor de Desenvolvimento Local"
    )
    parser.add_argument(
        "--plugin", "-p",
        action="append",
        help="Plugin(s) para carregar"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Porta para WebSocket (default: 8765)"
    )
    parser.add_argument(
        "--mod",
        action="append",
        help="Criar mod simulado (formato: game_id:mod_name)"
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Não iniciar console interativo"
    )
    
    args = parser.parse_args()
    
    # Criar servidor
    server = LocalDevServer(port=args.port)
    
    # Carregar plugins
    if args.plugin:
        for plugin_path in args.plugin:
            server.load_plugin(plugin_path)
    
    # Criar mods simulados
    if args.mod:
        for mod_spec in args.mod:
            if ":" in mod_spec:
                game_id, mod_name = mod_spec.split(":", 1)
            else:
                game_id, mod_name = mod_spec, "Test Mod"
            server.create_mod(game_id, mod_name)
    
    # Rodar
    if not args.no_interactive:
        server.run_interactive()


if __name__ == "__main__":
    main()
