"""插件注册器

管理所有 Embedding 扩展插件的注册和实例化。
"""
from __future__ import annotations

import logging
from typing import Type, Callable, TYPE_CHECKING

from .base import EmbeddingPlugin, PluginConfig

if TYPE_CHECKING:
    from ..system.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class PluginRegistry:
    """插件注册器 - 管理所有 Embedding 扩展插件
    
    使用方式:
    ```python
    # 注册插件（通过装饰器）
    @register_plugin("my_plugin")
    class MyPlugin(EmbeddingPlugin):
        ...
    
    # 配置插件
    PluginRegistry.configure("my_plugin", PluginConfig(enabled=True))
    
    # 获取实例
    plugin = PluginRegistry.get_instance("my_plugin", embedding_service)
    ```
    """
    
    _plugins: dict[str, Type[EmbeddingPlugin]] = {}
    _instances: dict[str, EmbeddingPlugin] = {}
    _configs: dict[str, PluginConfig] = {}
    
    @classmethod
    def register(cls, name: str, plugin_class: Type[EmbeddingPlugin]) -> None:
        """注册插件类"""
        if name in cls._plugins:
            logger.warning(f"[PluginRegistry] 插件 {name} 已存在，将被覆盖")
        cls._plugins[name] = plugin_class
        logger.debug(f"[PluginRegistry] 注册插件: {name}")
    
    @classmethod
    def configure(cls, name: str, config: PluginConfig) -> None:
        """配置插件"""
        cls._configs[name] = config
    
    @classmethod
    def configure_all(cls, configs: dict[str, dict]) -> None:
        """批量配置插件
        
        Args:
            configs: {"plugin_name": {"enabled": True, "params": {...}}, ...}
        """
        for name, cfg_dict in configs.items():
            config = PluginConfig(**cfg_dict)
            cls.configure(name, config)
    
    @classmethod
    def get_instance(
        cls, 
        name: str, 
        embedding_service: 'EmbeddingService',
        config: PluginConfig | None = None
    ) -> EmbeddingPlugin | None:
        """获取插件实例
        
        Args:
            name: 插件名称
            embedding_service: Embedding 服务实例
            config: 可选的插件配置，如果提供则创建新实例
            
        Returns:
            插件实例，如果不存在返回 None
        """
        if name not in cls._plugins:
            logger.warning(f"[PluginRegistry] 插件 {name} 未注册")
            return None
        
        # 如果提供了新配置，更新并创建新实例
        if config is not None:
            cls._configs[name] = config
            # 清除旧实例以使用新配置
            if name in cls._instances:
                del cls._instances[name]
        
        if name not in cls._instances:
            effective_config = cls._configs.get(name, PluginConfig())
            try:
                cls._instances[name] = cls._plugins[name](embedding_service, effective_config)
            except Exception as e:
                logger.error(f"[PluginRegistry] 实例化插件 {name} 失败: {e}")
                return None
        
        return cls._instances[name]
    
    @classmethod
    def get_enabled_instances(
        cls, 
        embedding_service: 'EmbeddingService'
    ) -> list[EmbeddingPlugin]:
        """获取所有启用的插件实例
        
        Args:
            embedding_service: Embedding 服务实例
            
        Returns:
            启用的插件实例列表
        """
        instances = []
        for name in cls._plugins:
            config = cls._configs.get(name, PluginConfig())
            if config.enabled:
                instance = cls.get_instance(name, embedding_service)
                if instance:
                    instances.append(instance)
        return instances
    
    @classmethod
    def list_plugins(cls) -> list[str]:
        """列出所有已注册的插件名称"""
        return list(cls._plugins.keys())
    
    @classmethod
    def list_enabled_plugins(cls) -> list[str]:
        """列出所有启用的插件名称"""
        return [
            name for name in cls._plugins
            if cls._configs.get(name, PluginConfig()).enabled
        ]
    
    @classmethod
    def get_plugin_info(cls, name: str) -> dict | None:
        """获取插件信息"""
        if name not in cls._plugins:
            return None
        
        plugin_cls = cls._plugins[name]
        config = cls._configs.get(name, PluginConfig())
        instance = cls._instances.get(name)
        
        return {
            "name": name,
            "class": plugin_cls.__name__,
            "enabled": config.enabled,
            "update_frequency": config.update_frequency,
            "initialized": instance._initialized if instance else False,
            "required_fields": list(plugin_cls.required_context_fields),
        }
    
    @classmethod
    def clear(cls) -> None:
        """清空所有注册（测试用）"""
        cls._plugins.clear()
        cls._instances.clear()
        cls._configs.clear()
    
    @classmethod
    def reset_instances(cls) -> None:
        """重置所有实例（保留注册和配置）"""
        cls._instances.clear()


def register_plugin(name: str) -> Callable[[Type[EmbeddingPlugin]], Type[EmbeddingPlugin]]:
    """装饰器：注册插件类
    
    使用方式:
    ```python
    @register_plugin("my_plugin")
    class MyPlugin(EmbeddingPlugin):
        @property
        def name(self) -> str:
            return "my_plugin"
        ...
    ```
    """
    def decorator(cls: Type[EmbeddingPlugin]) -> Type[EmbeddingPlugin]:
        PluginRegistry.register(name, cls)
        return cls
    return decorator

