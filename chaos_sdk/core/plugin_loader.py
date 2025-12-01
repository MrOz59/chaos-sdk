#!/usr/bin/env python3
"""
🎮 Chaos Factory - Plugin & Game Manager
Sistema automatizado para download e instalação de plugins e jogos
"""

import asyncio
import json
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import aiohttp
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadados de um plugin"""
    id: str
    name: str
    version: str
    author: str
    description: str
    category: str  # game_plugins, integration_plugins, custom_commands
    download_url: str
    checksum: str
    dependencies: List[str]
    config_required: bool = False


@dataclass
class GameMetadata:
    """Metadados de um jogo"""
    id: str
    name: str
    version: str
    description: str
    download_url: str
    checksum: str
    config_file: str  # Nome do arquivo JSON de config


class PluginManager:
    """Gerenciador de plugins e jogos"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path.cwd()
        self.plugins_dir = self.base_dir / "config/plugins"
        self.games_dir = self.base_dir / "config/games"
        self.cache_dir = self.base_dir / "data/plugin_cache"
        self.registry_file = self.base_dir / "data/plugin_registry.json"
        
        # URLs do repositório de plugins/jogos
        self.repo_base = "https://raw.githubusercontent.com/chaos-factory/plugins/main"
        self.plugins_manifest_url = f"{self.repo_base}/manifest.json"
        
        self._ensure_directories()
        self.installed_plugins = self._load_registry()
    
    def _ensure_directories(self):
        """Cria diretórios necessários"""
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.games_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.plugins_dir / "game_plugins").mkdir(exist_ok=True)
        (self.plugins_dir / "integration_plugins").mkdir(exist_ok=True)
        (self.plugins_dir / "custom_commands").mkdir(exist_ok=True)
    
    def _load_registry(self) -> Dict:
        """Carrega registro de plugins instalados"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar registry: {e}")
        return {"plugins": {}, "games": {}}
    
    def _save_registry(self):
        """Salva registro de plugins instalados"""
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.installed_plugins, f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar registry: {e}")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calcula SHA256 de um arquivo"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    async def fetch_manifest(self) -> Dict:
        """Baixa manifesto de plugins disponíveis"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.plugins_manifest_url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Erro ao buscar manifesto: HTTP {response.status}")
                        return {"plugins": [], "games": []}
        except Exception as e:
            logger.error(f"Erro ao baixar manifesto: {e}")
            return {"plugins": [], "games": []}
    
    async def download_file(self, url: str, destination: Path) -> bool:
        """Baixa um arquivo"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with open(destination, 'wb') as f:
                            f.write(await response.read())
                        logger.info(f"✅ Download concluído: {destination.name}")
                        return True
                    else:
                        logger.error(f"Erro no download: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Erro ao baixar arquivo: {e}")
            return False
    
    async def install_plugin(self, plugin_id: str, manifest: Dict = None) -> bool:
        """Instala um plugin"""
        if manifest is None:
            manifest = await self.fetch_manifest()
        
        # Buscar plugin no manifesto
        plugin_data = None
        for plugin in manifest.get("plugins", []):
            if plugin["id"] == plugin_id:
                plugin_data = PluginMetadata(**plugin)
                break
        
        if not plugin_data:
            logger.error(f"❌ Plugin '{plugin_id}' não encontrado no manifesto")
            return False
        
        logger.info(f"📦 Instalando plugin: {plugin_data.name} v{plugin_data.version}")
        
        # Verificar se já está instalado
        if plugin_id in self.installed_plugins["plugins"]:
            installed_version = self.installed_plugins["plugins"][plugin_id]["version"]
            if installed_version == plugin_data.version:
                logger.info(f"⏭️  Plugin já instalado: v{installed_version}")
                return True
            else:
                logger.info(f"🔄 Atualizando de v{installed_version} para v{plugin_data.version}")
        
        # Baixar plugin
        cache_file = self.cache_dir / f"{plugin_id}.zip"
        if not await self.download_file(plugin_data.download_url, cache_file):
            return False
        
        # Verificar checksum
        if plugin_data.checksum:
            actual_checksum = self._calculate_checksum(cache_file)
            if actual_checksum != plugin_data.checksum:
                logger.error(f"❌ Checksum inválido! Esperado: {plugin_data.checksum}, Obtido: {actual_checksum}")
                cache_file.unlink()
                return False
            logger.info("✅ Checksum verificado")
        
        # Extrair para diretório correto
        target_dir = self.plugins_dir / plugin_data.category
        
        try:
            with zipfile.ZipFile(cache_file, 'r') as zip_ref:
                base_dest = target_dir.resolve()
                for member in zip_ref.namelist():
                    if member.endswith("/"):
                        # Normalizar diretórios
                        dest_path = (base_dest / member).resolve()
                        if not str(dest_path).startswith(str(base_dest)):
                            logger.error(f"❌ Caminho inválido no pacote (path traversal): {member}")
                            return False
                        dest_path.mkdir(parents=True, exist_ok=True)
                        continue
                    # Arquivos
                    dest_path = (base_dest / member).resolve()
                    if not str(dest_path).startswith(str(base_dest)):
                        logger.error(f"❌ Caminho inválido no pacote (path traversal): {member}")
                        return False
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with zip_ref.open(member) as src, open(dest_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
            logger.info(f"✅ Plugin extraído para: {target_dir}")
        except Exception as e:
            logger.error(f"❌ Erro ao extrair plugin: {e}")
            return False
        
        # Registrar instalação
        self.installed_plugins["plugins"][plugin_id] = {
            "name": plugin_data.name,
            "version": plugin_data.version,
            "category": plugin_data.category,
            "installed_at": str(Path.cwd())
        }
        self._save_registry()
        
        logger.info(f"🎉 Plugin '{plugin_data.name}' instalado com sucesso!")
        return True
    
    async def install_game(self, game_id: str, manifest: Dict = None) -> bool:
        """Instala configuração de um jogo"""
        if manifest is None:
            manifest = await self.fetch_manifest()
        
        # Buscar jogo no manifesto
        game_data = None
        for game in manifest.get("games", []):
            if game["id"] == game_id:
                game_data = GameMetadata(**game)
                break
        
        if not game_data:
            logger.error(f"❌ Jogo '{game_id}' não encontrado no manifesto")
            return False
        
        logger.info(f"🎮 Instalando jogo: {game_data.name} v{game_data.version}")
        
        # Verificar se já está instalado
        if game_id in self.installed_plugins["games"]:
            installed_version = self.installed_plugins["games"][game_id]["version"]
            if installed_version == game_data.version:
                logger.info(f"⏭️  Jogo já instalado: v{installed_version}")
                return True
        
        # Baixar config do jogo
        config_file = self.games_dir / game_data.config_file
        if not await self.download_file(game_data.download_url, config_file):
            return False
        
        # Verificar checksum
        if game_data.checksum:
            actual_checksum = self._calculate_checksum(config_file)
            if actual_checksum != game_data.checksum:
                logger.error(f"❌ Checksum inválido!")
                config_file.unlink()
                return False
            logger.info("✅ Checksum verificado")
        
        # Registrar instalação
        self.installed_plugins["games"][game_id] = {
            "name": game_data.name,
            "version": game_data.version,
            "config_file": game_data.config_file,
            "installed_at": str(Path.cwd())
        }
        self._save_registry()
        
        logger.info(f"🎉 Jogo '{game_data.name}' instalado com sucesso!")
        return True
    
    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """Remove um plugin"""
        if plugin_id not in self.installed_plugins["plugins"]:
            logger.error(f"❌ Plugin '{plugin_id}' não está instalado")
            return False
        
        plugin_info = self.installed_plugins["plugins"][plugin_id]
        category = plugin_info["category"]
        
        logger.info(f"🗑️  Removendo plugin: {plugin_info['name']}")
        
        # Remover arquivos do plugin (assumindo que o ID é o nome do arquivo)
        plugin_file = self.plugins_dir / category / f"{plugin_id}.py"
        if plugin_file.exists():
            plugin_file.unlink()
            logger.info(f"✅ Arquivo removido: {plugin_file}")
        
        # Remover do registry
        del self.installed_plugins["plugins"][plugin_id]
        self._save_registry()
        
        logger.info(f"🎉 Plugin '{plugin_info['name']}' removido com sucesso!")
        return True
    
    async def uninstall_game(self, game_id: str) -> bool:
        """Remove configuração de um jogo"""
        if game_id not in self.installed_plugins["games"]:
            logger.error(f"❌ Jogo '{game_id}' não está instalado")
            return False
        
        game_info = self.installed_plugins["games"][game_id]
        
        logger.info(f"🗑️  Removendo jogo: {game_info['name']}")
        
        # Remover arquivo de config
        config_file = self.games_dir / game_info["config_file"]
        if config_file.exists():
            config_file.unlink()
            logger.info(f"✅ Config removido: {config_file}")
        
        # Remover do registry
        del self.installed_plugins["games"][game_id]
        self._save_registry()
        
        logger.info(f"🎉 Jogo '{game_info['name']}' removido com sucesso!")
        return True
    
    def list_installed(self) -> Dict:
        """Lista plugins e jogos instalados"""
        return {
            "plugins": self.installed_plugins.get("plugins", {}),
            "games": self.installed_plugins.get("games", {})
        }
    
    async def list_available(self) -> Dict:
        """Lista plugins e jogos disponíveis"""
        manifest = await self.fetch_manifest()
        return {
            "plugins": manifest.get("plugins", []),
            "games": manifest.get("games", [])
        }
    
    async def update_all(self) -> Dict[str, bool]:
        """Atualiza todos os plugins e jogos instalados"""
        manifest = await self.fetch_manifest()
        results = {"plugins": {}, "games": {}}
        
        # Atualizar plugins
        for plugin_id in list(self.installed_plugins.get("plugins", {}).keys()):
            logger.info(f"🔄 Verificando atualizações para plugin: {plugin_id}")
            results["plugins"][plugin_id] = await self.install_plugin(plugin_id, manifest)
        
        # Atualizar jogos
        for game_id in list(self.installed_plugins.get("games", {}).keys()):
            logger.info(f"🔄 Verificando atualizações para jogo: {game_id}")
            results["games"][game_id] = await self.install_game(game_id, manifest)
        
        return results


async def main():
    """CLI principal"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
🎪 Chaos Factory - Plugin & Game Manager

Uso:
  plugin-manager.py list                    # Listar instalados
  plugin-manager.py available               # Listar disponíveis
  plugin-manager.py install plugin <id>     # Instalar plugin
  plugin-manager.py install game <id>       # Instalar jogo
  plugin-manager.py uninstall plugin <id>   # Remover plugin
  plugin-manager.py uninstall game <id>     # Remover jogo
  plugin-manager.py update                  # Atualizar tudo
        """)
        return
    
    manager = PluginManager()
    command = sys.argv[1]
    
    if command == "list":
        installed = manager.list_installed()
        print("\n📦 PLUGINS INSTALADOS:")
        for pid, pinfo in installed["plugins"].items():
            print(f"  • {pinfo['name']} (v{pinfo['version']}) - {pid}")
        
        print("\n🎮 JOGOS INSTALADOS:")
        for gid, ginfo in installed["games"].items():
            print(f"  • {ginfo['name']} (v{ginfo['version']}) - {gid}")
    
    elif command == "available":
        available = await manager.list_available()
        print("\n📦 PLUGINS DISPONÍVEIS:")
        for plugin in available["plugins"]:
            print(f"  • {plugin['name']} (v{plugin['version']}) - {plugin['id']}")
            print(f"    {plugin['description']}")
        
        print("\n🎮 JOGOS DISPONÍVEIS:")
        for game in available["games"]:
            print(f"  • {game['name']} (v{game['version']}) - {game['id']}")
            print(f"    {game['description']}")
    
    elif command == "install" and len(sys.argv) >= 4:
        item_type = sys.argv[2]  # plugin ou game
        item_id = sys.argv[3]
        
        if item_type == "plugin":
            success = await manager.install_plugin(item_id)
        elif item_type == "game":
            success = await manager.install_game(item_id)
        else:
            print(f"❌ Tipo inválido: {item_type}")
            return
        
        sys.exit(0 if success else 1)
    
    elif command == "uninstall" and len(sys.argv) >= 4:
        item_type = sys.argv[2]
        item_id = sys.argv[3]
        
        if item_type == "plugin":
            success = await manager.uninstall_plugin(item_id)
        elif item_type == "game":
            success = await manager.uninstall_game(item_id)
        else:
            print(f"❌ Tipo inválido: {item_type}")
            return
        
        sys.exit(0 if success else 1)
    
    elif command == "update":
        results = await manager.update_all()
        print("\n✅ Atualizações concluídas!")
        print(f"Plugins: {sum(results['plugins'].values())}/{len(results['plugins'])} atualizados")
        print(f"Jogos: {sum(results['games'].values())}/{len(results['games'])} atualizados")
    
    else:
        print("❌ Comando inválido")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
