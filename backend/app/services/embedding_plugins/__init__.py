"""
Embedding 扩展插件模块

该模块实现了可插拔的向量嵌入扩展架构，包括：
1. EmbeddingPlugin - 插件基类
2. PluginRegistry - 插件注册器
3. EmbeddingPluginManager - 插件管理器
4. TensorEmbeddingBridge - 张量数据桥接器【新增】

设计原则：
- 所有插件共享 EmbeddingService 核心能力
- 统一的生命周期管理（initialize, on_turn_start, on_turn_end）
- 通过 SimulationContext 共享数据
- 支持存档的导入/导出
- 必需字段缺失时自动降级
- 【张量集成】优先从 TensorState 获取种群/环境数据

可用插件（按实现优先级）：
- behavior_strategy: 行为策略向量 [Phase 1]
- food_web: 生态网络向量 [Phase 1]
- tile_biome: 区域地块向量 [Phase 1]
- prompt_optimizer: Prompt 优化 [Phase 2]
- evolution_space: 演化向量空间 [Phase 2]
- ancestry: 血统压缩向量 [Phase 2]
"""

from .base import EmbeddingPlugin, PluginConfig
from .registry import PluginRegistry, register_plugin
from .manager import EmbeddingPluginManager
from .config_loader import load_plugin_configs, get_default_plugin_config
from .tensor_bridge import (
    TensorEmbeddingBridge,
    TensorSpeciesDistribution,
    TensorEnvironmentProfile,
    TensorSpeciationSignal,
    get_tensor_bridge,
    reset_tensor_bridge,
)


def load_all_plugins() -> list[str]:
    """加载所有内置插件
    
    Returns:
        成功加载的插件名称列表
    """
    loaded = []
    
    # Phase 1 插件
    try:
        from . import behavior_strategy
        loaded.append("behavior_strategy")
    except ImportError:
        pass
    
    try:
        from . import food_web_embedding
        loaded.append("food_web")
    except ImportError:
        pass
    
    try:
        from . import tile_embedding
        loaded.append("tile_biome")
    except ImportError:
        pass
    
    # Phase 2 插件
    try:
        from . import prompt_optimizer
        loaded.append("prompt_optimizer")
    except ImportError:
        pass
    
    try:
        from . import evolution_space
        loaded.append("evolution_space")
    except ImportError:
        pass
    
    try:
        from . import ancestry_embedding
        loaded.append("ancestry")
    except ImportError:
        pass
    
    return loaded


__all__ = [
    # 基类
    "EmbeddingPlugin",
    "PluginConfig",
    # 注册器
    "PluginRegistry",
    "register_plugin",
    # 管理器
    "EmbeddingPluginManager",
    # 配置加载
    "load_plugin_configs",
    "get_default_plugin_config",
    # 张量桥接
    "TensorEmbeddingBridge",
    "TensorSpeciesDistribution",
    "TensorEnvironmentProfile",
    "TensorSpeciationSignal",
    "get_tensor_bridge",
    "reset_tensor_bridge",
    # 加载函数
    "load_all_plugins",
]
