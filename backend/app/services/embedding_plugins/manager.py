"""插件管理器

统一管理所有 Embedding 插件的生命周期。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .registry import PluginRegistry
from .base import EmbeddingPlugin, PluginConfig
from .config_loader import load_plugin_configs, merge_configs, get_default_plugin_config

if TYPE_CHECKING:
    from ..system.embedding import EmbeddingService
    from ...simulation.context import SimulationContext

logger = logging.getLogger(__name__)


class EmbeddingPluginManager:
    """Embedding 插件管理器
    
    统一管理所有插件的生命周期，提供批量操作接口。
    
    使用方式:
    ```python
    manager = EmbeddingPluginManager(embedding_service, mode="full")
    manager.load_plugins()
    
    # 在回合中调用
    manager.on_turn_start(ctx)
    # ... 模拟逻辑 ...
    manager.on_turn_end(ctx)
    
    # 存档
    data = manager.export_for_save()
    manager.import_from_save(data)
    ```
    """
    
    def __init__(
        self, 
        embedding_service: 'EmbeddingService',
        mode: str = "full",
        config_path: Path | str | None = None,
        only_configured: bool = False
    ):
        """初始化插件管理器
        
        Args:
            embedding_service: EmbeddingService 实例
            mode: 运行模式 (minimal/standard/full/debug)
            config_path: stage_config.yaml 路径
            only_configured: 是否仅加载配置文件中明确列出的插件
                - False (默认): 加载所有注册的插件，按配置过滤 enabled
                - True: 仅加载配置文件中出现的插件
        """
        self.embeddings = embedding_service
        self.mode = mode
        self.only_configured = only_configured
        self._plugins: list[EmbeddingPlugin] = []
        self._loaded = False
        self._yaml_configs: dict[str, PluginConfig] = {}
        
        # 加载 YAML 配置
        self._load_yaml_configs(config_path)
    
    def _load_yaml_configs(self, config_path: Path | str | None = None) -> None:
        """加载 YAML 配置"""
        try:
            self._yaml_configs = load_plugin_configs(config_path, self.mode)
            if self._yaml_configs:
                logger.debug(f"[PluginManager] 已加载 YAML 配置: {list(self._yaml_configs.keys())}")
        except Exception as e:
            logger.warning(f"[PluginManager] 加载 YAML 配置失败: {e}")
            self._yaml_configs = {}
    
    def _get_plugin_config(self, plugin_name: str) -> PluginConfig:
        """获取插件配置（YAML + 默认合并）"""
        return merge_configs(self._yaml_configs, plugin_name)
    
    def load_plugins(self, plugin_names: list[str] | None = None) -> int:
        """加载插件
        
        Args:
            plugin_names: 要加载的插件名称列表
                - None: 根据 only_configured 决定加载范围
                
        Returns:
            成功加载的插件数量
        """
        self._plugins = []
        
        # 获取要加载的插件名称
        if plugin_names:
            names_to_load = plugin_names
        elif self.only_configured:
            # 仅加载配置文件中明确列出的插件
            names_to_load = list(self._yaml_configs.keys())
            if not names_to_load:
                logger.info(f"[PluginManager] 模式 {self.mode} 配置中无插件，跳过加载")
                self._loaded = True
                return 0
        else:
            # 加载所有注册的插件（默认行为）
            names_to_load = PluginRegistry.list_plugins()
        
        for name in names_to_load:
            config = self._get_plugin_config(name)
            
            # 检查是否启用
            if not config.enabled:
                logger.debug(f"[PluginManager] 跳过禁用的插件: {name}")
                continue
            
            # 检查插件是否已注册
            if name not in PluginRegistry.list_plugins():
                logger.warning(f"[PluginManager] 配置的插件 {name} 未注册，跳过")
                continue
            
            # 创建插件实例
            plugin = PluginRegistry.get_instance(name, self.embeddings, config)
            if plugin:
                self._plugins.append(plugin)
        
        # 初始化所有插件
        success_count = 0
        for plugin in self._plugins:
            try:
                plugin.initialize()
                success_count += 1
            except Exception as e:
                logger.error(f"[PluginManager] 初始化插件 {plugin.name} 失败: {e}")
        
        self._loaded = True
        logger.info(f"[PluginManager] 已加载 {success_count}/{len(self._plugins)} 个插件 (模式: {self.mode})")
        return success_count
    
    @property
    def is_loaded(self) -> bool:
        """是否已加载"""
        return self._loaded
    
    @property
    def plugin_count(self) -> int:
        """已加载的插件数量"""
        return len(self._plugins)
    
    def on_turn_start(self, ctx: 'SimulationContext') -> None:
        """通知所有插件回合开始"""
        for plugin in self._plugins:
            try:
                plugin.on_turn_start(ctx)
            except Exception as e:
                logger.error(f"[{plugin.name}] on_turn_start 失败: {e}")
    
    def on_turn_end(self, ctx: 'SimulationContext') -> None:
        """通知所有插件回合结束"""
        for plugin in self._plugins:
            try:
                plugin.on_turn_end(ctx)
            except Exception as e:
                logger.error(f"[{plugin.name}] on_turn_end 失败: {e}")
    
    def get_plugin(self, name: str) -> EmbeddingPlugin | None:
        """获取指定插件"""
        for plugin in self._plugins:
            if plugin.name == name:
                return plugin
        return None
    
    def list_plugins(self) -> list[str]:
        """列出已加载的插件名称"""
        return [p.name for p in self._plugins]
    
    def get_all_stats(self) -> dict[str, Any]:
        """获取所有插件的统计信息"""
        return {
            "manager": {
                "loaded": self._loaded,
                "plugin_count": len(self._plugins),
            },
            "plugins": {
                plugin.name: plugin.get_stats()
                for plugin in self._plugins
            }
        }
    
    def export_for_save(self) -> dict[str, Any]:
        """导出所有插件数据用于存档"""
        return {
            "version": "1.0",
            "plugins": {
                plugin.name: plugin.export_for_save()
                for plugin in self._plugins
            }
        }
    
    def import_from_save(self, data: dict[str, Any]) -> None:
        """从存档恢复所有插件"""
        if not data:
            return
        
        plugins_data = data.get("plugins", {})
        for plugin in self._plugins:
            if plugin.name in plugins_data:
                try:
                    plugin.import_from_save(plugins_data[plugin.name])
                except Exception as e:
                    logger.error(f"[{plugin.name}] 恢复失败: {e}")
        
        logger.info(f"[PluginManager] 从存档恢复 {len(plugins_data)} 个插件")
    
    def search_all(self, query: str, top_k: int = 5) -> dict[str, list[dict]]:
        """在所有插件中搜索
        
        Args:
            query: 查询文本
            top_k: 每个插件返回的数量
            
        Returns:
            {"plugin_name": [results...], ...}
        """
        results = {}
        for plugin in self._plugins:
            try:
                results[plugin.name] = plugin.search(query, top_k)
            except Exception as e:
                logger.error(f"[{plugin.name}] 搜索失败: {e}")
                results[plugin.name] = []
        return results

