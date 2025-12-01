"""
Exemplo de Plugin de Integração com Mod de Jogo
Demonstra 3 métodos de comunicação com mods
"""

import sys
import os

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from chaos_sdk.plugins.base_plugin import IntegrationPlugin
import socket
import json
import requests
from typing import Dict, Any


class GameModIntegration(IntegrationPlugin):
    """
    Plugin para integração com mods de jogos
    Suporta múltiplos métodos de comunicação
    """
    
    name = "Game Mod Integration"
    version = "1.0.0"
    author = "StreamBot"
    description = "Integração com mods de jogos (HTTP, Socket, File)"
    
    def __init__(self, bot_instance=None):
        super().__init__(bot_instance)
        self.connection_type = "http"  # http, socket, file
        self.socket_client = None
        self.api_url = "http://localhost:5000"
        self.command_file = "game_commands.txt"
    
    def on_load(self):
        """Conectar ao mod quando carregar"""
        self.log_info("Inicializando integração com mod...")
        
        # Detectar método de conexão disponível
        if self._try_http_connection():
            self.connection_type = "http"
            self.log_info("✅ Conectado via HTTP API")
        elif self._try_socket_connection():
            self.connection_type = "socket"
            self.log_info("✅ Conectado via Socket")
        else:
            self.connection_type = "file"
            self.log_info("✅ Usando comunicação via arquivo")
        
        # Registrar comandos
        self.register_commands({
            "spawn": self.cmd_spawn,
            "weather": self.cmd_weather,
            "tp": self.cmd_teleport,
            "modinfo": self.cmd_mod_info
        })
    
    # ==================== CONEXÕES ====================
    
    def _try_http_connection(self) -> bool:
        """Tenta conectar via HTTP"""
        try:
            response = requests.get(f"{self.api_url}/ping", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _try_socket_connection(self) -> bool:
        """Tenta conectar via Socket"""
        try:
            self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_client.connect(("localhost", 9999))
            self.socket_client.settimeout(5)
            return True
        except:
            self.socket_client = None
            return False
    
    def connect(self):
        """Implementação do método abstrato"""
        return self._try_http_connection() or self._try_socket_connection()
    
    def disconnect(self):
        """Desconecta do mod"""
        if self.socket_client:
            self.socket_client.close()
            self.socket_client = None
    
    # ==================== COMUNICAÇÃO ====================
    
    def send_to_game(self, command: str, params: Dict[str, Any] = None) -> Dict:
        """
        Envia comando para o jogo usando método disponível
        
        Args:
            command: Nome do comando
            params: Parâmetros do comando
        
        Returns:
            Resposta do jogo
        """
        params = params or {}
        
        if self.connection_type == "http":
            return self._send_http(command, params)
        elif self.connection_type == "socket":
            return self._send_socket(command, params)
        else:
            return self._send_file(command, params)
    
    def _send_http(self, command: str, params: Dict) -> Dict:
        """Enviar via HTTP API"""
        try:
            response = requests.post(
                f"{self.api_url}/command",
                json={"command": command, "params": params},
                timeout=5
            )
            return response.json()
        except Exception as e:
            self.log_error(f"Erro HTTP: {e}")
            return {"success": False, "error": str(e)}
    
    def _send_socket(self, command: str, params: Dict) -> Dict:
        """Enviar via Socket"""
        try:
            message = json.dumps({"command": command, "params": params})
            self.socket_client.send(message.encode() + b"\n")
            
            # Aguardar resposta
            response = self.socket_client.recv(4096).decode()
            return json.loads(response)
        except Exception as e:
            self.log_error(f"Erro Socket: {e}")
            return {"success": False, "error": str(e)}
    
    def _send_file(self, command: str, params: Dict) -> Dict:
        """Enviar via arquivo (mod lê o arquivo)"""
        try:
            with open(self.command_file, "a") as f:
                f.write(json.dumps({"command": command, "params": params}) + "\n")
            return {"success": True, "method": "file"}
        except Exception as e:
            self.log_error(f"Erro File: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== COMANDOS ====================
    
    def cmd_spawn(self, username: str, args: list, **kwargs) -> str:
        """!spawn <entity> - Spawna entidade no jogo"""
        if not args:
            return f"{username}, use: !spawn <entidade>"
        
        entity = args[0]
        count = int(args[1]) if len(args) > 1 else 1
        
        # Enviar para jogo
        result = self.send_to_game("spawn", {
            "entity": entity,
            "count": count,
            "spawner": username
        })
        
        if result.get("success"):
            return f"{username} spawnou {count}x {entity}! 🎮"
        else:
            return f"Erro ao spawnar: {result.get('error', 'desconhecido')}"
    
    def cmd_weather(self, username: str, args: list, **kwargs) -> str:
        """!weather <tipo> - Muda o clima"""
        if not kwargs.get('is_mod'):
            return f"{username}, apenas mods podem mudar o clima!"
        
        if not args:
            return "Use: !weather <sol/chuva/tempestade>"
        
        weather = args[0].lower()
        result = self.send_to_game("weather", {"type": weather})
        
        if result.get("success"):
            return f"🌤️ Clima mudado para: {weather}"
        else:
            return f"Erro ao mudar clima"
    
    def cmd_teleport(self, username: str, args: list, **kwargs) -> str:
        """!tp <x> <y> <z> - Teleporta personagem"""
        if len(args) < 3:
            return f"{username}, use: !tp <x> <y> <z>"
        
        try:
            x, y, z = float(args[0]), float(args[1]), float(args[2])
            result = self.send_to_game("teleport", {
                "x": x, "y": y, "z": z,
                "player": username
            })
            
            if result.get("success"):
                return f"{username} teleportado para ({x}, {y}, {z})! 🌀"
            else:
                return "Erro ao teleportar"
        except ValueError:
            return "Coordenadas inválidas!"
    
    def cmd_mod_info(self, username: str, args: list, **kwargs) -> str:
        """!modinfo - Informações sobre o mod"""
        result = self.send_to_game("info", {})
        
        if result.get("success"):
            mod_name = result.get("mod_name", "Unknown")
            mod_version = result.get("version", "?.?.?")
            return f"📦 Mod: {mod_name} v{mod_version} | Método: {self.connection_type.upper()}"
        else:
            return f"Método de comunicação: {self.connection_type.upper()}"
    
    # ==================== HOOKS ====================
    
    def on_stream_start(self):
        """Notifica mod que stream começou"""
        self.send_to_game("stream_event", {"event": "start"})
    
    def on_stream_end(self):
        """Notifica mod que stream terminou"""
        self.send_to_game("stream_event", {"event": "end"})
    
    def on_points_spent(self, username: str, amount: int, reason: str):
        """Notifica mod sobre gasto de pontos (para recompensas no jogo)"""
        if amount >= 100:
            self.send_to_game("points_milestone", {
                "username": username,
                "amount": amount,
                "reason": reason
            })


# ==================== MOD EXEMPLO (Unity C#) ====================
"""
// Exemplo de mod em Unity que recebe comandos do bot

using UnityEngine;
using System.Net;
using System.Net.Sockets;
using Newtonsoft.Json;

public class TwitchBotIntegration : MonoBehaviour
{
    private TcpListener server;
    
    void Start()
    {
        // Iniciar servidor socket
        server = new TcpListener(IPAddress.Any, 9999);
        server.Start();
        Debug.Log("Mod aguardando conexão do bot...");
        
        // Aceitar conexões em thread separada
        System.Threading.ThreadPool.QueueUserWorkItem(HandleClients);
    }
    
    void HandleClients(object state)
    {
        while (true)
        {
            var client = server.AcceptTcpClient();
            var stream = client.GetStream();
            var reader = new System.IO.StreamReader(stream);
            
            string line;
            while ((line = reader.ReadLine()) != null)
            {
                var command = JsonConvert.DeserializeObject<BotCommand>(line);
                ProcessCommand(command);
            }
        }
    }
    
    void ProcessCommand(BotCommand cmd)
    {
        switch (cmd.command)
        {
            case "spawn":
                SpawnEntity(cmd.params["entity"], cmd.params["count"]);
                break;
            case "weather":
                ChangeWeather(cmd.params["type"]);
                break;
            case "teleport":
                TeleportPlayer(cmd.params["x"], cmd.params["y"], cmd.params["z"]);
                break;
        }
    }
    
    void SpawnEntity(string entity, int count)
    {
        // Spawnar entidade no jogo
        Debug.Log($"Spawning {count}x {entity}");
    }
}
"""

if __name__ == "__main__":
    # Teste standalone
    plugin = GameModIntegration()
    plugin.on_load()
    
    print("\n🧪 Testando integração...")
    print(plugin.cmd_modinfo("TestUser", []))
    print(plugin.cmd_spawn("TestUser", ["zombie", "3"]))
