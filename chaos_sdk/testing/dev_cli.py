"""
Chaos SDK - CLI para Desenvolvimento Local
===========================================

Comandos para testar plugins e mods localmente.

Uso:
    chaos dev run plugin.py      # Rodar plugin localmente
    chaos dev test plugin.py     # Testar plugin
    chaos dev chat               # Simular chat interativo
    chaos dev mod connect        # Conectar mod de teste
    chaos dev server             # Iniciar servidor completo
"""
from __future__ import annotations

import os
import sys
import json
import time
import signal
import asyncio
import argparse
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import click
    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False


def load_plugin_from_file(file_path: str):
    """Carregar plugin de arquivo Python."""
    path = Path(file_path).resolve()
    
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    
    if not path.suffix == '.py':
        raise ValueError(f"Arquivo deve ser .py: {path}")
    
    # Importar módulo
    spec = importlib.util.spec_from_file_location("user_plugin", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["user_plugin"] = module
    
    # Adicionar diretório ao path
    sys.path.insert(0, str(path.parent))
    
    spec.loader.exec_module(module)
    
    # Procurar classe de plugin
    from chaos_sdk import Plugin
    
    for name in dir(module):
        obj = getattr(module, name)
        if (isinstance(obj, type) and 
            issubclass(obj, Plugin) and 
            obj is not Plugin):
            return obj
    
    # Tentar importar ModBridgePlugin também
    try:
        from chaos_sdk.mods.bridge import ModBridgePlugin
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                issubclass(obj, ModBridgePlugin) and 
                obj is not ModBridgePlugin):
                return obj
    except ImportError:
        pass
    
    raise ValueError(f"Nenhum plugin encontrado em {path}")


def run_plugin_interactive(plugin_path: str, port: int = 8765):
    """Rodar plugin em modo interativo."""
    from chaos_sdk.testing.dev_server import LocalDevServer, MockUser
    
    print("\n🎮 Chaos Dev Server - Modo Interativo")
    print("=" * 50)
    
    # Carregar plugin
    try:
        plugin_class = load_plugin_from_file(plugin_path)
        print(f"✅ Plugin carregado: {plugin_class.__name__}")
    except Exception as e:
        print(f"❌ Erro ao carregar plugin: {e}")
        return 1
    
    # Criar servidor
    server = LocalDevServer(port=port)
    
    # Carregar plugin
    try:
        plugin = server.load_plugin(plugin_class)
        print(f"✅ Plugin ativo: {plugin.name} v{plugin.version}")
    except Exception as e:
        print(f"❌ Erro ao ativar plugin: {e}")
        return 1
    
    # Coletar comandos
    commands = {}
    for name in dir(plugin):
        if name.startswith('cmd_'):
            cmd_name = name[4:]
            commands[cmd_name] = getattr(plugin, name)
    
    print(f"📋 Comandos: {', '.join(commands.keys())}")
    print(f"🔌 Mod WebSocket: ws://localhost:{port}/mod")
    print("-" * 50)
    print("Digite comandos como: !comando arg1 arg2")
    print("Comandos especiais:")
    print("  /user <nome>     - Mudar usuário atual")
    print("  /mod             - Ativar modo mod")
    print("  /sub             - Ativar modo sub")
    print("  /points <n>      - Definir pontos")
    print("  /event <tipo>    - Simular evento do mod")
    print("  /help            - Ajuda")
    print("  /quit            - Sair")
    print("-" * 50)
    
    current_user = MockUser(username="viewer1", points=1000)
    
    while True:
        try:
            line = input(f"\n[{current_user.username}] > ").strip()
            
            if not line:
                continue
            
            # Comandos especiais
            if line.startswith('/'):
                parts = line[1:].split()
                cmd = parts[0].lower()
                args = parts[1:]
                
                if cmd == 'quit' or cmd == 'exit':
                    print("\n👋 Até mais!")
                    break
                
                elif cmd == 'help':
                    print("Comandos do plugin:", ", ".join(f"!{c}" for c in commands))
                
                elif cmd == 'user':
                    if args:
                        current_user = MockUser(username=args[0], points=1000)
                        print(f"👤 Usuário: {current_user.username}")
                
                elif cmd == 'mod':
                    current_user = MockUser(
                        username=current_user.username,
                        is_mod=True,
                        points=current_user.points
                    )
                    print(f"🛡️ {current_user.username} agora é mod")
                
                elif cmd == 'sub':
                    current_user = MockUser(
                        username=current_user.username,
                        is_sub=True,
                        points=current_user.points
                    )
                    print(f"⭐ {current_user.username} agora é sub")
                
                elif cmd == 'vip':
                    current_user = MockUser(
                        username=current_user.username,
                        is_vip=True,
                        points=current_user.points
                    )
                    print(f"💎 {current_user.username} agora é VIP")
                
                elif cmd == 'points':
                    if args:
                        pts = int(args[0])
                        current_user = MockUser(
                            username=current_user.username,
                            is_mod=current_user.is_mod,
                            is_sub=current_user.is_sub,
                            is_vip=current_user.is_vip,
                            points=pts
                        )
                        server.context.set_points(current_user.username, pts)
                        print(f"💰 Pontos: {pts}")
                
                elif cmd == 'event':
                    if args:
                        event_type = args[0]
                        event_data = {}
                        if len(args) > 1:
                            try:
                                event_data = json.loads(" ".join(args[1:]))
                            except:
                                print("❌ JSON inválido")
                                continue
                        
                        print(f"📨 Simulando evento: {event_type}")
                        # Buscar handler se existir
                        if hasattr(plugin, '_event_handlers'):
                            handler = plugin._event_handlers.get(event_type)
                            if handler:
                                try:
                                    result = handler(None, type('Event', (), {
                                        'event_type': event_type,
                                        'data': event_data,
                                        'player': event_data.get('player'),
                                    })())
                                    if result:
                                        print(f"📤 Resposta: {result}")
                                except Exception as e:
                                    print(f"❌ Erro no handler: {e}")
                        else:
                            print("⚠️ Plugin não tem handlers de eventos")
                
                else:
                    print(f"❓ Comando desconhecido: /{cmd}")
                
                continue
            
            # Comandos do plugin
            if line.startswith('!'):
                parts = line[1:].split()
                cmd_name = parts[0].lower()
                cmd_args = parts[1:]
                
                if cmd_name in commands:
                    try:
                        # Atualizar pontos no contexto
                        server.context.set_points(
                            current_user.username, 
                            current_user.points
                        )
                        
                        result = commands[cmd_name](current_user.username, cmd_args)
                        
                        if result:
                            print(f"💬 {result}")
                        else:
                            print("✅ Comando executado")
                        
                        # Verificar se pontos mudaram
                        new_points = server.context.get_points(current_user.username)
                        if new_points != current_user.points:
                            print(f"💰 Pontos: {current_user.points} → {new_points}")
                            current_user = MockUser(
                                username=current_user.username,
                                is_mod=current_user.is_mod,
                                is_sub=current_user.is_sub,
                                is_vip=current_user.is_vip,
                                points=new_points
                            )
                    
                    except Exception as e:
                        print(f"❌ Erro: {e}")
                else:
                    print(f"❓ Comando não existe: !{cmd_name}")
                    print(f"   Disponíveis: {', '.join(f'!{c}' for c in commands)}")
            
            else:
                # Mensagem normal de chat
                print(f"💬 [CHAT] {current_user.username}: {line}")
                
                # Trigger event
                if hasattr(plugin, 'on_message'):
                    try:
                        plugin.on_message(current_user.username, line)
                    except:
                        pass
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrompido!")
            break
        except EOFError:
            break
    
    return 0


def test_plugin(plugin_path: str, verbose: bool = False):
    """Testar plugin automaticamente."""
    import unittest
    from chaos_sdk.testing.test_runner import PluginTestCase, create_test_suite
    
    print("\n🧪 Chaos Dev - Testador de Plugins")
    print("=" * 50)
    
    # Carregar plugin
    try:
        plugin_class = load_plugin_from_file(plugin_path)
        print(f"✅ Plugin carregado: {plugin_class.__name__}")
    except Exception as e:
        print(f"❌ Erro ao carregar plugin: {e}")
        return 1
    
    # Criar suite de testes
    suite = create_test_suite(plugin_class)
    
    # Executar
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Resumo
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ Todos os testes passaram!")
        return 0
    else:
        print(f"❌ {len(result.failures)} falhas, {len(result.errors)} erros")
        return 1


def run_chat_simulator():
    """Rodar simulador de chat interativo."""
    from chaos_sdk.testing.dev_server import ChatSimulator
    
    print("\n💬 Chaos Dev - Simulador de Chat")
    print("=" * 50)
    print("Comandos:")
    print("  /add <user>           - Adicionar viewer")
    print("  /mod <user>           - Tornar mod")
    print("  /sub <user>           - Tornar sub")
    print("  /raid <n>             - Simular raid")
    print("  /bits <user> <n>      - Simular bits")
    print("  /follow <user>        - Simular follow")
    print("  /auto <interval>      - Chat automático")
    print("  /stop                 - Parar automático")
    print("  /quit                 - Sair")
    print("-" * 50)
    
    sim = ChatSimulator()
    auto_task = None
    
    while True:
        try:
            line = input("\n[chat] > ").strip()
            
            if not line:
                continue
            
            if line.startswith('/'):
                parts = line[1:].split()
                cmd = parts[0].lower()
                args = parts[1:]
                
                if cmd in ('quit', 'exit'):
                    break
                
                elif cmd == 'add':
                    if args:
                        sim.add_viewer(args[0])
                        print(f"👤 Viewer adicionado: {args[0]}")
                
                elif cmd == 'mod':
                    if args:
                        sim.viewers[args[0].lower()] = {
                            'is_mod': True, 
                            'is_sub': False
                        }
                        print(f"🛡️ {args[0]} é mod")
                
                elif cmd == 'sub':
                    if args:
                        sim.viewers[args[0].lower()] = {
                            'is_mod': False, 
                            'is_sub': True
                        }
                        print(f"⭐ {args[0]} é sub")
                
                elif cmd == 'raid':
                    n = int(args[0]) if args else 50
                    print(f"🚀 RAID com {n} viewers!")
                    for i in range(min(n, 10)):
                        sim.add_viewer(f"raider_{i}")
                
                elif cmd == 'bits':
                    if len(args) >= 2:
                        user, bits = args[0], int(args[1])
                        print(f"💎 {user} doou {bits} bits!")
                
                elif cmd == 'follow':
                    if args:
                        print(f"❤️ Novo follower: {args[0]}")
                
                elif cmd == 'auto':
                    interval = float(args[0]) if args else 2.0
                    print(f"🤖 Chat automático a cada {interval}s")
                    sim.auto_interval = interval
                    sim.auto_mode = True
                
                elif cmd == 'stop':
                    sim.auto_mode = False
                    print("⏹️ Chat automático parado")
                
                else:
                    print(f"❓ Comando: /{cmd}")
            
            else:
                # Mensagem direta
                print(f"📨 > {line}")
        
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    
    print("\n👋 Simulador encerrado!")
    return 0


async def run_dev_server(port: int = 8765, plugin_paths: List[str] = None):
    """Rodar servidor de desenvolvimento completo."""
    from chaos_sdk.testing.dev_server import LocalDevServer
    
    print("\n🚀 Chaos Dev Server")
    print("=" * 50)
    print(f"📡 WebSocket: ws://localhost:{port}")
    print(f"📡 Mod Bridge: ws://localhost:{port}/mod")
    
    server = LocalDevServer(port=port)
    
    # Carregar plugins
    if plugin_paths:
        for path in plugin_paths:
            try:
                plugin_class = load_plugin_from_file(path)
                plugin = server.load_plugin(plugin_class)
                print(f"✅ Plugin: {plugin.name}")
            except Exception as e:
                print(f"⚠️ Erro em {path}: {e}")
    
    print("-" * 50)
    print("Pressione Ctrl+C para parar")
    
    try:
        await server.start_async()
    except KeyboardInterrupt:
        print("\n👋 Servidor encerrado!")
    
    return 0


def main():
    """Ponto de entrada do CLI."""
    parser = argparse.ArgumentParser(
        prog='chaos-dev',
        description='Chaos SDK - Desenvolvimento Local'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comando')
    
    # chaos dev run
    run_parser = subparsers.add_parser('run', help='Rodar plugin interativamente')
    run_parser.add_argument('plugin', help='Arquivo do plugin (.py)')
    run_parser.add_argument('--port', type=int, default=8765, help='Porta do servidor')
    
    # chaos dev test
    test_parser = subparsers.add_parser('test', help='Testar plugin')
    test_parser.add_argument('plugin', help='Arquivo do plugin (.py)')
    test_parser.add_argument('-v', '--verbose', action='store_true', help='Saída verbosa')
    
    # chaos dev chat
    chat_parser = subparsers.add_parser('chat', help='Simulador de chat')
    
    # chaos dev server
    server_parser = subparsers.add_parser('server', help='Servidor de desenvolvimento')
    server_parser.add_argument('--port', type=int, default=8765, help='Porta')
    server_parser.add_argument('--plugin', action='append', dest='plugins', help='Plugins')
    
    args = parser.parse_args()
    
    if args.command == 'run':
        return run_plugin_interactive(args.plugin, args.port)
    
    elif args.command == 'test':
        return test_plugin(args.plugin, args.verbose)
    
    elif args.command == 'chat':
        return run_chat_simulator()
    
    elif args.command == 'server':
        return asyncio.run(run_dev_server(args.port, args.plugins))
    
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
