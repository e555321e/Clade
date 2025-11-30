"""Embedding 插件基类

所有向量扩展插件的基类，提供统一的生命周期管理。
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..system.embedding import EmbeddingService
    from ...simulation.context import SimulationContext

logger = logging.getLogger(__name__)


@dataclass
class PluginConfig:
    """插件配置"""
    enabled: bool = True
    index_name: str = ""              # 向量索引名称（默认使用插件名）
    update_frequency: int = 1         # 每 N 回合更新一次
    cache_ttl: int = 10               # 缓存有效回合数
    fallback_on_error: bool = True    # 出错时是否降级
    params: dict = field(default_factory=dict)  # 插件特定参数


@dataclass
class PluginStats:
    """插件运行统计"""
    updates: int = 0
    searches: int = 0
    errors: int = 0
    fallback_count: int = 0
    last_update_time: str = ""
    last_build_duration_ms: float = 0
    index_size: int = 0
    degraded_mode: bool = False
    quality_warnings: list[str] = field(default_factory=list)


class EmbeddingPlugin(ABC):
    """Embedding 插件基类
    
    所有扩展功能必须继承此类，实现标准生命周期方法。
    
    生命周期:
    1. initialize() - 服务启动时调用
    2. on_turn_start(ctx) - 回合开始时调用
    3. on_turn_end(ctx) - 回合结束时调用
    4. build_index(ctx) - 构建/更新向量索引
    5. search(query) - 执行相似度搜索
    6. export_for_save() / import_from_save() - 存档支持
    
    数据契约:
    - 每个插件声明 required_context_fields 指定依赖的 Context 字段
    - 声明 optional_context_fields 指定可选但影响质量的字段
    - 如果必需字段缺失，插件应降级处理而非抛异常
    """
    
    # 子类可覆盖：声明依赖的 Context 字段
    required_context_fields: set[str] = set()
    # 子类可覆盖：可选但影响质量的字段
    optional_context_fields: set[str] = set()
    
    def __init__(
        self, 
        embedding_service: 'EmbeddingService',
        config: PluginConfig | None = None
    ):
        self.embeddings = embedding_service
        self.config = config or PluginConfig()
        self._initialized = False
        self._last_update_turn = -1
        
        # 统计信息
        self._stats = PluginStats()
        self._degraded_mode = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称（用于日志和配置）"""
        pass
    
    @property
    def index_name(self) -> str:
        """向量索引名称"""
        return self.config.index_name or self.name
    
    # ==================== 生命周期方法 ====================
    
    def initialize(self) -> None:
        """初始化插件（服务启动时调用）"""
        if self._initialized:
            return
        
        try:
            self._do_initialize()
            self._initialized = True
            logger.info(f"[{self.name}] 插件初始化完成 (更新频率: 每 {self.config.update_frequency} 回合)")
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"[{self.name}] 初始化失败: {e}")
            if not self.config.fallback_on_error:
                raise
    
    def _do_initialize(self) -> None:
        """子类实现初始化逻辑（可选覆盖）"""
        pass
    
    def on_turn_start(self, ctx: 'SimulationContext') -> None:
        """回合开始时的钩子（可选覆盖）"""
        pass
    
    def on_turn_end(self, ctx: 'SimulationContext') -> None:
        """回合结束时的钩子"""
        if not self._initialized:
            return
        
        turn = ctx.turn_index
        if self._should_update(turn):
            start_time = time.time()
            
            try:
                # 检查必需字段
                missing = self._check_required_fields(ctx)
                if missing:
                    logger.warning(f"[{self.name}] 缺少必需字段 {missing}，使用降级模式")
                    self._degraded_mode = True
                    self._stats.degraded_mode = True
                    count = self._build_index_fallback(ctx)
                else:
                    # 检查数据质量
                    quality = self._check_data_quality(ctx)
                    self._stats.quality_warnings = quality.get("warnings", [])
                    
                    if quality.get("warnings"):
                        logger.info(f"[{self.name}] 数据质量提示: 使用降级模式，输出精度较低")
                        for warn in quality["warnings"]:
                            logger.debug(f"[{self.name}]   - {warn}")
                        self._degraded_mode = True
                        self._stats.degraded_mode = True
                    else:
                        self._degraded_mode = False
                        self._stats.degraded_mode = False
                    
                    count = self.build_index(ctx)
                
                # 更新统计
                duration_ms = (time.time() - start_time) * 1000
                self._last_update_turn = turn
                self._stats.updates += 1
                self._stats.last_update_time = datetime.now().isoformat()
                self._stats.last_build_duration_ms = round(duration_ms, 2)
                self._stats.index_size = count
                
                logger.debug(f"[{self.name}] 索引更新完成: {count} 条, 耗时 {duration_ms:.1f}ms")
                
            except Exception as e:
                self._stats.errors += 1
                logger.error(f"[{self.name}] 索引更新失败: {e}")
                if not self.config.fallback_on_error:
                    raise
    
    def _should_update(self, turn: int) -> bool:
        """判断是否需要更新索引"""
        if self._last_update_turn < 0:
            return True
        return (turn - self._last_update_turn) >= self.config.update_frequency
    
    def _check_required_fields(self, ctx: 'SimulationContext') -> set[str]:
        """检查必需字段，返回缺失的字段集合"""
        missing = set()
        for field_name in self.required_context_fields:
            value = getattr(ctx, field_name, None)
            if value is None or (isinstance(value, (list, dict)) and len(value) == 0):
                missing.add(field_name)
        return missing
    
    def _check_data_quality(self, ctx: 'SimulationContext') -> dict[str, list[str]]:
        """检查数据质量，返回警告信息
        
        子类可覆盖此方法添加特定的数据质量检查。
        
        Returns:
            {"warnings": [...], "missing_optional": [...]}
        """
        warnings = []
        missing_optional = []
        
        # 基本物种数据检查
        if hasattr(ctx, 'all_species') and ctx.all_species:
            sample = ctx.all_species[:10]  # 抽样检查
            sample_size = len(sample)
            
            missing_counts = {
                "populations": 0,
                "abstract_traits": 0,
                "prey_species": 0,
            }
            
            for sp in sample:
                if getattr(sp, 'populations', None) is None:
                    missing_counts["populations"] += 1
                if getattr(sp, 'abstract_traits', None) is None:
                    missing_counts["abstract_traits"] += 1
                if getattr(sp, 'prey_species', None) is None:
                    missing_counts["prey_species"] += 1
            
            # 注意: reproduction_r 不是 Species 模型字段，
            # 插件会从 abstract_traits 推断，无需检查
            
            # 报告缺失率超过 30% 的字段
            for field, count in missing_counts.items():
                if count > sample_size * 0.3:
                    missing_optional.append(f"Species.{field}")
            
            if missing_optional:
                warnings.append(
                    f"部分物种缺少字段 {missing_optional}，"
                    "使用降级模式，向量质量可能较低"
                )
        
        return {"warnings": warnings, "missing_optional": list(set(missing_optional))}
    
    # ==================== 核心抽象方法 ====================
    
    @abstractmethod
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建/更新向量索引
        
        Args:
            ctx: 模拟上下文
            
        Returns:
            更新的记录数量
        """
        pass
    
    def _build_index_fallback(self, ctx: 'SimulationContext') -> int:
        """降级的索引构建（当必需字段缺失时调用）
        
        子类可覆盖此方法提供降级逻辑
        """
        self._stats.fallback_count += 1
        return 0
    
    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """执行相似度搜索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            搜索结果列表
        """
        pass
    
    # ==================== 存档支持 ====================
    
    def export_for_save(self) -> dict[str, Any]:
        """导出数据用于存档"""
        return {
            "name": self.name,
            "last_update": self._last_update_turn,
            "stats": self._stats.copy(),
        }
    
    def import_from_save(self, data: dict[str, Any]) -> None:
        """从存档导入数据"""
        if not data:
            return
        self._last_update_turn = data.get("last_update", -1)
        # 不恢复统计信息（每次启动重新计数）
    
    # ==================== 辅助方法 ====================
    
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        # 获取当前索引大小
        store = self._get_vector_store(create=False)
        current_index_size = store.size if store else 0
        
        return {
            "name": self.name,
            "initialized": self._initialized,
            "enabled": self.config.enabled,
            "update_frequency": self.config.update_frequency,
            "last_update_turn": self._last_update_turn,
            "updates": self._stats.updates,
            "searches": self._stats.searches,
            "errors": self._stats.errors,
            "fallback_count": self._stats.fallback_count,
            "last_update_time": self._stats.last_update_time,
            "last_build_duration_ms": self._stats.last_build_duration_ms,
            "index_size": current_index_size,
            "degraded_mode": self._stats.degraded_mode,
            "quality_warnings": self._stats.quality_warnings,
        }
    
    # ==================== 插件数据共享 ====================
    
    def get_plugin_data(self, ctx: 'SimulationContext', key: str, default: Any = None) -> Any:
        """从 Context 读取本插件的共享数据
        
        Args:
            ctx: SimulationContext
            key: 数据键
            default: 默认值
        """
        if not hasattr(ctx, 'plugin_data') or ctx.plugin_data is None:
            return default
        return ctx.plugin_data.get(self.name, {}).get(key, default)
    
    def set_plugin_data(self, ctx: 'SimulationContext', key: str, value: Any) -> None:
        """向 Context 写入本插件的共享数据
        
        Args:
            ctx: SimulationContext
            key: 数据键
            value: 数据值
        """
        if not hasattr(ctx, 'plugin_data') or ctx.plugin_data is None:
            ctx.plugin_data = {}
        if self.name not in ctx.plugin_data:
            ctx.plugin_data[self.name] = {}
        ctx.plugin_data[self.name][key] = value
    
    def get_other_plugin_data(
        self, 
        ctx: 'SimulationContext', 
        plugin_name: str, 
        key: str, 
        default: Any = None
    ) -> Any:
        """读取其他插件的共享数据
        
        Args:
            ctx: SimulationContext
            plugin_name: 目标插件名称
            key: 数据键
            default: 默认值
        """
        if not hasattr(ctx, 'plugin_data') or ctx.plugin_data is None:
            return default
        return ctx.plugin_data.get(plugin_name, {}).get(key, default)
    
    def _get_vector_store(self, create: bool = True):
        """获取本插件的向量存储"""
        return self.embeddings._vector_stores.get_store(self.index_name, create=create)
    
    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文本（带错误处理）"""
        if not texts:
            return []
        try:
            return self.embeddings.embed(texts)
        except Exception as e:
            logger.error(f"[{self.name}] 嵌入失败: {e}")
            self._stats.errors += 1
            return []

