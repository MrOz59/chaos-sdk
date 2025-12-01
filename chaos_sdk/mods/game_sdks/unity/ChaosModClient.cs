/**
 * Chaos Mod SDK for Unity (C#)
 * ============================
 * 
 * Integrate your Unity game with Chaos platform for
 * viewer-controlled chaos events!
 * 
 * Quick Start:
 * 1. Add this script to your project
 * 2. Create a ChaosModClient instance
 * 3. Register command handlers
 * 4. Send events when things happen in-game
 * 
 * Example:
 *   var client = new ChaosModClient("my_game");
 *   client.OnCommand("spawn_enemy", cmd => SpawnEnemy(cmd));
 *   client.Connect("ws://localhost:8080/mod");
 */

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;

#if UNITY_2019_1_OR_NEWER
using UnityEngine.Networking;
#endif

namespace ChaosMod
{
    /// <summary>
    /// Main client for Chaos Mod integration.
    /// </summary>
    public class ChaosModClient : MonoBehaviour
    {
        #region Configuration
        
        [Header("Connection Settings")]
        [SerializeField] private string gameId = "unity_game";
        [SerializeField] private string modName = "Chaos Integration";
        [SerializeField] private string modVersion = "1.0.0";
        [SerializeField] private string serverUrl = "ws://localhost:8080/mod";
        [SerializeField] private bool autoReconnect = true;
        [SerializeField] private float reconnectDelay = 5f;
        
        [Header("Capabilities")]
        [SerializeField] private List<string> capabilities = new List<string> 
        { 
            "spawn", "items", "effects", "messages" 
        };
        
        #endregion
        
        #region Events
        
        /// <summary>Called when connected to Chaos server.</summary>
        public event Action OnConnected;
        
        /// <summary>Called when disconnected from Chaos server.</summary>
        public event Action OnDisconnected;
        
        /// <summary>Called when connection error occurs.</summary>
        public event Action<string> OnError;
        
        /// <summary>Called for any incoming message (for debugging).</summary>
        public event Action<string> OnRawMessage;
        
        #endregion
        
        #region Private Fields
        
        private WebSocket websocket;
        private Dictionary<string, Action<ModCommand>> commandHandlers = new Dictionary<string, Action<ModCommand>>();
        private bool isConnected = false;
        private bool shouldReconnect = true;
        
        #endregion
        
        #region Unity Lifecycle
        
        private void Awake()
        {
            DontDestroyOnLoad(gameObject);
        }
        
        private void OnDestroy()
        {
            shouldReconnect = false;
            Disconnect();
        }
        
        private void Update()
        {
            // Process WebSocket messages on main thread
            ProcessMessages();
        }
        
        #endregion
        
        #region Public API
        
        /// <summary>
        /// Connect to the Chaos server.
        /// </summary>
        public async Task Connect(string url = null)
        {
            if (url != null) serverUrl = url;
            
            try
            {
                websocket = new WebSocket(serverUrl);
                
                websocket.OnOpen += () =>
                {
                    isConnected = true;
                    SendHandshake();
                    OnConnected?.Invoke();
                    Debug.Log($"[ChaosMod] Connected to {serverUrl}");
                };
                
                websocket.OnClose += (code) =>
                {
                    isConnected = false;
                    OnDisconnected?.Invoke();
                    Debug.Log("[ChaosMod] Disconnected");
                    
                    if (autoReconnect && shouldReconnect)
                    {
                        StartCoroutine(ReconnectAfterDelay());
                    }
                };
                
                websocket.OnError += (error) =>
                {
                    OnError?.Invoke(error);
                    Debug.LogError($"[ChaosMod] Error: {error}");
                };
                
                websocket.OnMessage += HandleMessage;
                
                await websocket.Connect();
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ChaosMod] Connection failed: {ex.Message}");
                OnError?.Invoke(ex.Message);
            }
        }
        
        /// <summary>
        /// Disconnect from the Chaos server.
        /// </summary>
        public void Disconnect()
        {
            shouldReconnect = false;
            if (websocket != null)
            {
                websocket.Close();
                websocket = null;
            }
            isConnected = false;
        }
        
        /// <summary>
        /// Register a handler for a command type.
        /// </summary>
        public void OnCommand(string commandName, Action<ModCommand> handler)
        {
            commandHandlers[commandName] = handler;
            Debug.Log($"[ChaosMod] Registered handler for: {commandName}");
        }
        
        /// <summary>
        /// Send an event to the Chaos plugin.
        /// </summary>
        public void SendEvent(string eventType, object data, string player = null, Vector3? position = null)
        {
            if (!isConnected) 
            {
                Debug.LogWarning("[ChaosMod] Not connected, event not sent");
                return;
            }
            
            var message = new Dictionary<string, object>
            {
                ["type"] = "event",
                ["id"] = Guid.NewGuid().ToString().Substring(0, 8),
                ["timestamp"] = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                ["game_id"] = gameId,
                ["data"] = new Dictionary<string, object>
                {
                    ["event_type"] = eventType,
                    ["event_data"] = data,
                    ["player"] = player,
                    ["position"] = position.HasValue ? new Dictionary<string, float>
                    {
                        ["x"] = position.Value.x,
                        ["y"] = position.Value.y,
                        ["z"] = position.Value.z
                    } : null
                }
            };
            
            SendJson(message);
            Debug.Log($"[ChaosMod] Sent event: {eventType}");
        }
        
        /// <summary>
        /// Send a raw JSON message.
        /// </summary>
        public void SendJson(object data)
        {
            if (!isConnected) return;
            
            string json = JsonUtility.ToJson(data);
            websocket?.Send(json);
        }
        
        #endregion
        
        #region Convenience Methods
        
        /// <summary>Send player died event.</summary>
        public void PlayerDied(string playerName, string cause = null, Vector3? position = null)
        {
            SendEvent("player_died", new { cause = cause }, playerName, position);
        }
        
        /// <summary>Send player respawned event.</summary>
        public void PlayerRespawned(string playerName, Vector3? position = null)
        {
            SendEvent("player_respawned", new { }, playerName, position);
        }
        
        /// <summary>Send enemy killed event.</summary>
        public void EnemyKilled(string playerName, string enemyType, Vector3? position = null)
        {
            SendEvent("enemy_killed", new { enemy_type = enemyType }, playerName, position);
        }
        
        /// <summary>Send boss defeated event.</summary>
        public void BossDefeated(string bossName, List<string> players, float fightDuration)
        {
            SendEvent("boss_defeated", new { 
                boss_name = bossName, 
                players = players,
                duration = fightDuration 
            });
        }
        
        /// <summary>Send item collected event.</summary>
        public void ItemCollected(string playerName, string itemId, int count = 1)
        {
            SendEvent("item_collected", new { 
                item_id = itemId, 
                count = count 
            }, playerName);
        }
        
        /// <summary>Send achievement event.</summary>
        public void AchievementUnlocked(string playerName, string achievementId, string achievementName)
        {
            SendEvent("achievement_unlocked", new { 
                achievement_id = achievementId, 
                name = achievementName 
            }, playerName);
        }
        
        /// <summary>Send custom event.</summary>
        public void CustomEvent(string eventType, Dictionary<string, object> data, string player = null)
        {
            SendEvent(eventType, data, player);
        }
        
        #endregion
        
        #region Private Methods
        
        private void SendHandshake()
        {
            var handshake = new Dictionary<string, object>
            {
                ["type"] = "handshake",
                ["game_id"] = gameId,
                ["mod_id"] = $"{gameId}_{modName.Replace(" ", "_").ToLower()}",
                ["game_name"] = Application.productName,
                ["mod_name"] = modName,
                ["mod_version"] = modVersion,
                ["protocol_version"] = "1.0",
                ["capabilities"] = capabilities
            };
            
            SendJson(handshake);
        }
        
        private void HandleMessage(string json)
        {
            OnRawMessage?.Invoke(json);
            
            try
            {
                var message = JsonUtility.FromJson<ModMessage>(json);
                
                switch (message.type)
                {
                    case "command":
                        HandleCommand(json);
                        break;
                    
                    case "ping":
                        SendPong();
                        break;
                    
                    case "handshake_ack":
                        Debug.Log("[ChaosMod] Handshake acknowledged");
                        break;
                    
                    default:
                        Debug.Log($"[ChaosMod] Received: {message.type}");
                        break;
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ChaosMod] Failed to parse message: {ex.Message}");
            }
        }
        
        private void HandleCommand(string json)
        {
            try
            {
                var cmdData = JsonUtility.FromJson<CommandMessage>(json);
                var command = cmdData.data.command;
                
                if (commandHandlers.TryGetValue(command, out var handler))
                {
                    var cmd = new ModCommand
                    {
                        messageId = cmdData.id,
                        command = command,
                        parameters = cmdData.data.@params,
                        triggeredBy = cmdData.data.triggered_by,
                        client = this
                    };
                    
                    try
                    {
                        handler(cmd);
                    }
                    catch (Exception ex)
                    {
                        cmd.Respond(false, $"Handler error: {ex.Message}", "HANDLER_ERROR");
                    }
                }
                else
                {
                    Debug.LogWarning($"[ChaosMod] No handler for command: {command}");
                    SendCommandResult(cmdData.id, false, $"Unknown command: {command}", "UNKNOWN_COMMAND");
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ChaosMod] Failed to handle command: {ex.Message}");
            }
        }
        
        private void SendPong()
        {
            SendJson(new Dictionary<string, object>
            {
                ["type"] = "pong",
                ["game_id"] = gameId,
                ["timestamp"] = DateTimeOffset.UtcNow.ToUnixTimeSeconds()
            });
        }
        
        internal void SendCommandResult(string originalId, bool success, string message, string errorCode = null, object data = null)
        {
            SendJson(new Dictionary<string, object>
            {
                ["type"] = "command_result",
                ["game_id"] = gameId,
                ["data"] = new Dictionary<string, object>
                {
                    ["original_id"] = originalId,
                    ["success"] = success,
                    ["message"] = message,
                    ["error_code"] = errorCode,
                    ["response_data"] = data
                }
            });
        }
        
        private void ProcessMessages()
        {
            // WebSocket implementation handles this
            websocket?.DispatchMessageQueue();
        }
        
        private System.Collections.IEnumerator ReconnectAfterDelay()
        {
            yield return new WaitForSeconds(reconnectDelay);
            
            if (shouldReconnect && !isConnected)
            {
                Debug.Log("[ChaosMod] Attempting to reconnect...");
                _ = Connect();
            }
        }
        
        #endregion
    }
    
    /// <summary>
    /// Represents a command received from Chaos plugin.
    /// </summary>
    public class ModCommand
    {
        internal string messageId;
        internal ChaosModClient client;
        
        public string command;
        public Dictionary<string, object> parameters;
        public string triggeredBy;
        
        /// <summary>Get a string parameter.</summary>
        public string GetString(string key, string defaultValue = "")
        {
            if (parameters != null && parameters.TryGetValue(key, out var value))
                return value?.ToString() ?? defaultValue;
            return defaultValue;
        }
        
        /// <summary>Get an int parameter.</summary>
        public int GetInt(string key, int defaultValue = 0)
        {
            if (parameters != null && parameters.TryGetValue(key, out var value))
            {
                if (int.TryParse(value?.ToString(), out int result))
                    return result;
            }
            return defaultValue;
        }
        
        /// <summary>Get a float parameter.</summary>
        public float GetFloat(string key, float defaultValue = 0f)
        {
            if (parameters != null && parameters.TryGetValue(key, out var value))
            {
                if (float.TryParse(value?.ToString(), out float result))
                    return result;
            }
            return defaultValue;
        }
        
        /// <summary>Get a bool parameter.</summary>
        public bool GetBool(string key, bool defaultValue = false)
        {
            if (parameters != null && parameters.TryGetValue(key, out var value))
            {
                if (bool.TryParse(value?.ToString(), out bool result))
                    return result;
            }
            return defaultValue;
        }
        
        /// <summary>Get a Vector3 from position parameter.</summary>
        public Vector3 GetPosition(string key = "position")
        {
            if (parameters != null && parameters.TryGetValue(key, out var value))
            {
                if (value is Dictionary<string, object> pos)
                {
                    float x = 0, y = 0, z = 0;
                    if (pos.TryGetValue("x", out var xVal)) float.TryParse(xVal.ToString(), out x);
                    if (pos.TryGetValue("y", out var yVal)) float.TryParse(yVal.ToString(), out y);
                    if (pos.TryGetValue("z", out var zVal)) float.TryParse(zVal.ToString(), out z);
                    return new Vector3(x, y, z);
                }
            }
            return Vector3.zero;
        }
        
        /// <summary>Respond to the command.</summary>
        public void Respond(bool success, string message = "", string errorCode = null, object data = null)
        {
            client.SendCommandResult(messageId, success, message, errorCode, data);
        }
    }
    
    #region Internal Message Types
    
    [Serializable]
    internal class ModMessage
    {
        public string type;
        public string id;
        public string game_id;
    }
    
    [Serializable]
    internal class CommandMessage
    {
        public string type;
        public string id;
        public CommandData data;
    }
    
    [Serializable]
    internal class CommandData
    {
        public string command;
        public Dictionary<string, object> @params;
        public string triggered_by;
        public int priority;
        public float timeout;
    }
    
    #endregion
    
    #region Simple WebSocket (Unity Compatible)
    
    /// <summary>
    /// Simple WebSocket wrapper for Unity.
    /// For production, consider using NativeWebSocket or WebSocketSharp.
    /// </summary>
    public class WebSocket
    {
        private string url;
        private System.Net.WebSockets.ClientWebSocket ws;
        private Queue<string> messageQueue = new Queue<string>();
        
        public event Action OnOpen;
        public event Action<int> OnClose;
        public event Action<string> OnError;
        public event Action<string> OnMessage;
        
        public WebSocket(string url)
        {
            this.url = url;
        }
        
        public async Task Connect()
        {
            ws = new System.Net.WebSockets.ClientWebSocket();
            
            try
            {
                await ws.ConnectAsync(new Uri(url), System.Threading.CancellationToken.None);
                OnOpen?.Invoke();
                _ = ReceiveLoop();
            }
            catch (Exception ex)
            {
                OnError?.Invoke(ex.Message);
            }
        }
        
        public void Close()
        {
            ws?.CloseAsync(System.Net.WebSockets.WebSocketCloseStatus.NormalClosure, "", System.Threading.CancellationToken.None);
        }
        
        public void Send(string message)
        {
            if (ws?.State == System.Net.WebSockets.WebSocketState.Open)
            {
                var bytes = System.Text.Encoding.UTF8.GetBytes(message);
                ws.SendAsync(new ArraySegment<byte>(bytes), System.Net.WebSockets.WebSocketMessageType.Text, true, System.Threading.CancellationToken.None);
            }
        }
        
        public void DispatchMessageQueue()
        {
            while (messageQueue.Count > 0)
            {
                var msg = messageQueue.Dequeue();
                OnMessage?.Invoke(msg);
            }
        }
        
        private async Task ReceiveLoop()
        {
            var buffer = new byte[4096];
            
            while (ws?.State == System.Net.WebSockets.WebSocketState.Open)
            {
                try
                {
                    var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), System.Threading.CancellationToken.None);
                    
                    if (result.MessageType == System.Net.WebSockets.WebSocketMessageType.Text)
                    {
                        var message = System.Text.Encoding.UTF8.GetString(buffer, 0, result.Count);
                        messageQueue.Enqueue(message);
                    }
                    else if (result.MessageType == System.Net.WebSockets.WebSocketMessageType.Close)
                    {
                        OnClose?.Invoke((int)result.CloseStatus);
                        break;
                    }
                }
                catch (Exception ex)
                {
                    OnError?.Invoke(ex.Message);
                    break;
                }
            }
        }
    }
    
    #endregion
}
