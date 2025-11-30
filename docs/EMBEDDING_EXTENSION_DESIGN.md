# Embedding 扩展功能开发文档

> 模块化、可复用的向量嵌入系统扩展设计

## 实现状态

| 组件 | 状态 | 路径 |
|------|------|------|
| 插件基类 | ✅ 已实现 | `embedding_plugins/base.py` |
| 插件注册器 | ✅ 已实现 | `embedding_plugins/registry.py` |
| 插件管理器 | ✅ 已实现 | `embedding_plugins/manager.py` |
| 行为策略插件 | ✅ MVP | `embedding_plugins/behavior_strategy.py` |
| 生态网络插件 | ✅ MVP | `embedding_plugins/food_web_embedding.py` |
| 地块向量插件 | ⏳ 待实现 | - |
| Prompt优化插件 | ⏳ 待实现 | - |
| 演化空间插件 | ⏳ 待实现 | - |
| 血统压缩插件 | ⏳ 待实现 | - |
| Stage 集成 | ❌ 待添加 | `stage_config.yaml` |
| API 路由 | ❌ 待添加 | `embedding_routes.py` |

## 目录

1. [现有架构概览](#1-现有架构概览)
2. [数据契约](#2-数据契约)
3. [插件架构设计](#3-插件架构设计)
4. [插件实现详情](#4-插件实现详情)
5. [Stage 集成](#5-stage-集成)
6. [API 接口设计](#6-api-接口设计)
7. [实施计划](#7-实施计划)

---

## 1. 现有架构概览

### 1.1 核心组件

```
┌─────────────────────────────────────────────────────────────────┐
│                        EmbeddingService                         │
│  backend/app/services/system/embedding.py                       │
├─────────────────────────────────────────────────────────────────┤
│  • embed(texts) → vectors      批量文本转向量                   │
│  • index_species()             物种向量索引                     │
│  • search_species()            语义搜索                         │
│  • compute_similarity_matrix() 相似度矩阵                       │
│  • store_pressure_vector()     压力向量存储                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MultiVectorStore (Faiss)                     │
│  backend/app/services/system/vector_store.py                    │
├─────────────────────────────────────────────────────────────────┤
│  索引类型:                                                      │
│  • species   - 物种描述向量                                     │
│  • plants    - 植物专用向量                                     │
│  • events    - 事件描述向量                                     │
│  • concepts  - 概念定义向量                                     │
│  • pressures - 压力向量                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 现有服务依赖

| 服务 | 路径 | 功能 |
|------|------|------|
| `TaxonomyService` | `services/analytics/taxonomy.py` | 自动分类学 |
| `EvolutionPredictor` | `services/analytics/evolution_predictor.py` | 向量演化预测 |
| `NarrativeEngine` | `services/analytics/narrative_engine.py` | 叙事生成 |
| `EncyclopediaService` | `services/analytics/encyclopedia.py` | 智能百科 |
| `EmbeddingIntegrationService` | `services/analytics/embedding_integration.py` | 集成层 |

### 1.3 模拟流水线集成

现有 `embedding_hooks` Stage（order: 165）在每回合结束时触发：

```yaml
# stage_config.yaml
- name: embedding_hooks
  enabled: true  # 注意：standard 模式下默认 false
  order: 165
```

---

## 2. 数据契约

### 2.1 各插件的数据依赖

| 插件 | 必需字段 | 可选字段 | 降级策略 |
|------|---------|---------|---------|
| `behavior_strategy` | `all_species` | `abstract_traits` | 仅用 trophic_level, reproduction_r |
| `food_web` | `all_species` | `food_web_analysis`, `prey_species` | 基于 trophic_level 推断竞争 |
| `tile_biome` | `all_tiles`, `all_species` | `all_habitats`, populations | 跳过物种分布统计 |
| `prompt_optimizer` | `all_species` | `major_events`, `pressures` | 仅用物种描述 |
| `evolution_space` | `all_species` | `combined_results`, `adaptation_events` | 不记录演化事件 |
| `ancestry` | `all_species` | `branching_events` | 基于 lineage_code 推断祖先 |

### 2.2 Species 模型已有字段（可直接使用）

```python
# backend/app/models/species.py
class Species:
    lineage_code: str       # ✅ 唯一标识
    common_name: str        # ✅ 常用名
    latin_name: str         # ✅ 学名
    description: str        # ✅ 描述文本
    trophic_level: float    # ✅ 营养级 (1-5)
    reproduction_r: float   # ✅ 繁殖率
    abstract_traits: dict   # ✅ 抽象特征 {"攻击性": 5, "防御性": 7, ...}
    status: str             # ✅ 状态 (alive/extinct/endangered)
    populations: list       # ⚠️ 可能为空
    prey_species: list      # ⚠️ 可能为空
    total_population: int   # ✅ 总种群
```

### 2.3 SimulationContext 已有字段

```python
# backend/app/simulation/context.py
@dataclass
class SimulationContext:
    turn_index: int              # ✅ 回合索引
    all_species: list[Species]   # ✅ 物种列表（fetch_species 后填充）
    all_tiles: list[dict]        # ⚠️ 可能为空
    all_habitats: dict           # ⚠️ 可能为空
    pressures: list              # ✅ 压力列表
    major_events: list           # ⚠️ 仅部分回合有
    
    # 食物网相关
    trophic_interactions: dict   # ⚠️ 结构: {predator_code: float}，非关系列表
    food_web_analysis: Any       # ⚠️ 需确认是否存在
    
    # AI 评估结果
    combined_results: list       # ⚠️ 仅 ecological_intelligence 启用时有
    adaptation_events: list      # ⚠️ 可能为空
    branching_events: list       # ⚠️ 可能为空
```

### 2.4 降级设计原则

每个插件必须实现 `_build_index_fallback()` 方法，当必需字段缺失时：

1. **记录警告**而非抛异常
2. **返回 0** 表示未更新索引
3. **使用缓存**如果可用
4. **更新 fallback_count** 统计

```python
def _build_index_fallback(self, ctx: 'SimulationContext') -> int:
    self._stats["fallback_count"] += 1
    logger.warning(f"[{self.name}] 使用降级逻辑")
    return 0  # 或使用已缓存数据
```

---

## 3. 插件架构设计

### 2.1 插件基类

所有新功能模块继承统一的插件基类，确保一致的生命周期管理：

```python
# backend/app/services/embedding_plugins/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..system.embedding import EmbeddingService
    from ...simulation.context import SimulationContext

@dataclass
class PluginConfig:
    """插件配置"""
    enabled: bool = True
    index_name: str = ""
    update_frequency: int = 1  # 每 N 回合更新一次
    cache_ttl: int = 10  # 缓存有效回合数

class EmbeddingPlugin(ABC):
    """Embedding 插件基类
    
    所有扩展功能必须继承此类，实现标准生命周期方法。
    
    生命周期:
    1. initialize() - 服务启动时调用
    2. on_turn_start() - 回合开始时调用
    3. on_turn_end() - 回合结束时调用
    4. build_index() - 构建/更新向量索引
    5. search() - 执行相似度搜索
    6. export_for_save() / import_from_save() - 存档支持
    """
    
    def __init__(
        self, 
        embedding_service: 'EmbeddingService',
        config: PluginConfig | None = None
    ):
        self.embeddings = embedding_service
        self.config = config or PluginConfig()
        self._initialized = False
        self._last_update_turn = -1
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称（用于日志和配置）"""
        pass
    
    @property
    def index_name(self) -> str:
        """向量索引名称"""
        return self.config.index_name or self.name
    
    def initialize(self) -> None:
        """初始化插件（服务启动时调用）"""
        if self._initialized:
            return
        self._do_initialize()
        self._initialized = True
    
    @abstractmethod
    def _do_initialize(self) -> None:
        """子类实现初始化逻辑"""
        pass
    
    def on_turn_start(self, ctx: 'SimulationContext') -> None:
        """回合开始时的钩子"""
        pass
    
    def on_turn_end(self, ctx: 'SimulationContext') -> None:
        """回合结束时的钩子"""
        turn = ctx.turn_index
        if self._should_update(turn):
            self.build_index(ctx)
            self._last_update_turn = turn
    
    def _should_update(self, turn: int) -> bool:
        """判断是否需要更新索引"""
        if self._last_update_turn < 0:
            return True
        return (turn - self._last_update_turn) >= self.config.update_frequency
    
    @abstractmethod
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建/更新向量索引，返回更新数量"""
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """执行相似度搜索"""
        pass
    
    def export_for_save(self) -> dict[str, Any]:
        """导出数据用于存档"""
        return {"name": self.name, "last_update": self._last_update_turn}
    
    def import_from_save(self, data: dict[str, Any]) -> None:
        """从存档导入数据"""
        self._last_update_turn = data.get("last_update", -1)
```

### 2.2 插件注册器

```python
# backend/app/services/embedding_plugins/registry.py

from typing import Type
import logging

from .base import EmbeddingPlugin, PluginConfig

logger = logging.getLogger(__name__)

class PluginRegistry:
    """插件注册器 - 管理所有 Embedding 扩展插件"""
    
    _plugins: dict[str, Type[EmbeddingPlugin]] = {}
    _instances: dict[str, EmbeddingPlugin] = {}
    _configs: dict[str, PluginConfig] = {}
    
    @classmethod
    def register(cls, name: str, plugin_class: Type[EmbeddingPlugin]) -> None:
        """注册插件类"""
        cls._plugins[name] = plugin_class
        logger.info(f"[PluginRegistry] 注册插件: {name}")
    
    @classmethod
    def configure(cls, name: str, config: PluginConfig) -> None:
        """配置插件"""
        cls._configs[name] = config
    
    @classmethod
    def get_instance(cls, name: str, embedding_service) -> EmbeddingPlugin | None:
        """获取插件实例（单例）"""
        if name not in cls._plugins:
            return None
        
        if name not in cls._instances:
            config = cls._configs.get(name)
            cls._instances[name] = cls._plugins[name](embedding_service, config)
        
        return cls._instances[name]
    
    @classmethod
    def get_all_instances(cls, embedding_service) -> list[EmbeddingPlugin]:
        """获取所有启用的插件实例"""
        instances = []
        for name, plugin_cls in cls._plugins.items():
            config = cls._configs.get(name, PluginConfig())
            if config.enabled:
                instance = cls.get_instance(name, embedding_service)
                if instance:
                    instances.append(instance)
        return instances
    
    @classmethod
    def clear(cls) -> None:
        """清空所有插件（测试用）"""
        cls._plugins.clear()
        cls._instances.clear()
        cls._configs.clear()


def register_plugin(name: str):
    """装饰器：注册插件类"""
    def decorator(cls: Type[EmbeddingPlugin]) -> Type[EmbeddingPlugin]:
        PluginRegistry.register(name, cls)
        return cls
    return decorator
```

### 2.3 插件管理器

```python
# backend/app/services/embedding_plugins/manager.py

from typing import TYPE_CHECKING, Any
import logging

from .registry import PluginRegistry
from .base import EmbeddingPlugin

if TYPE_CHECKING:
    from ..system.embedding import EmbeddingService
    from ...simulation.context import SimulationContext

logger = logging.getLogger(__name__)

class EmbeddingPluginManager:
    """Embedding 插件管理器
    
    统一管理所有插件的生命周期，提供批量操作接口。
    在 EmbeddingIntegrationService 中使用。
    """
    
    def __init__(self, embedding_service: 'EmbeddingService'):
        self.embeddings = embedding_service
        self._plugins: list[EmbeddingPlugin] = []
    
    def load_plugins(self) -> int:
        """加载所有已注册的插件"""
        self._plugins = PluginRegistry.get_all_instances(self.embeddings)
        
        for plugin in self._plugins:
            try:
                plugin.initialize()
            except Exception as e:
                logger.error(f"[PluginManager] 初始化插件 {plugin.name} 失败: {e}")
        
        logger.info(f"[PluginManager] 已加载 {len(self._plugins)} 个插件")
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
    
    def export_for_save(self) -> dict[str, Any]:
        """导出所有插件数据"""
        return {
            plugin.name: plugin.export_for_save()
            for plugin in self._plugins
        }
    
    def import_from_save(self, data: dict[str, Any]) -> None:
        """从存档恢复所有插件"""
        for plugin in self._plugins:
            if plugin.name in data:
                try:
                    plugin.import_from_save(data[plugin.name])
                except Exception as e:
                    logger.error(f"[{plugin.name}] 恢复失败: {e}")
```

---

## 3. 新功能模块

### 3.1 行为策略向量 (Behavior Strategy Embedding)

#### 目标

为每个物种生成行为策略的向量表示，支持：
- 行为相似物种聚类
- 行为冲突预测（夜行 vs 昼行）
- 行为生态位分析
- 新行为预测

#### 策略文本模板

```python
BEHAVIOR_TEMPLATE = """
捕食策略: {predation_strategy}
防御策略: {defense_strategy}
繁殖策略: {reproduction_strategy}
活动节律: {activity_pattern}
社会行为: {social_behavior}
觅食方式: {foraging_mode}
领域行为: {territorial_behavior}
"""
```

#### 实现

```python
# backend/app/services/embedding_plugins/behavior_strategy.py

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...simulation.context import SimulationContext

@dataclass
class BehaviorProfile:
    """物种行为档案"""
    lineage_code: str
    predation_strategy: str  # 埋伏/追逐/群体协作/滤食
    defense_strategy: str    # 拟态/结群/穴居/毒素/逃跑
    reproduction_strategy: str  # 高繁殖/低繁殖/父母抚育/r策略/K策略
    activity_pattern: str    # 昼行/夜行/晨昏/潮汐/全天候
    social_behavior: str     # 独居/配对/小群/大群/蜂群社会
    foraging_mode: str       # 主动搜寻/守株待兔/储食/游牧
    territorial_behavior: str  # 强领域/弱领域/无领域/迁徙
    
    def to_text(self) -> str:
        return f"""捕食策略: {self.predation_strategy}
防御策略: {self.defense_strategy}
繁殖策略: {self.reproduction_strategy}
活动节律: {self.activity_pattern}
社会行为: {self.social_behavior}
觅食方式: {self.foraging_mode}
领域行为: {self.territorial_behavior}"""


@register_plugin("behavior_strategy")
class BehaviorStrategyPlugin(EmbeddingPlugin):
    """行为策略向量插件"""
    
    @property
    def name(self) -> str:
        return "behavior_strategy"
    
    def _do_initialize(self) -> None:
        # 初始化策略映射表
        self._strategy_mappings = self._build_strategy_mappings()
    
    def _build_strategy_mappings(self) -> dict[str, dict]:
        """根据物种特征推断行为策略的映射规则"""
        return {
            "predation": {
                # trophic_level -> strategy
                (0, 2): "滤食/光合",
                (2, 3): "机会捕食",
                (3, 4): "主动捕食",
                (4, 5): "顶级掠食者",
            },
            "activity": {
                # 基于眼睛大小、夜视能力推断
                "high_nocturnal": "夜行",
                "high_diurnal": "昼行",
                "default": "晨昏活动",
            }
        }
    
    def infer_behavior_profile(self, species: 'Species') -> BehaviorProfile:
        """从物种特征推断行为档案"""
        traits = species.abstract_traits or {}
        
        # 推断捕食策略
        if species.trophic_level < 2:
            predation = "滤食/光合"
        elif traits.get("攻击性", 5) > 7:
            predation = "群体协作" if traits.get("社会性", 5) > 6 else "主动追逐"
        else:
            predation = "埋伏/机会主义"
        
        # 推断防御策略
        if traits.get("防御性", 5) > 7:
            defense = "坚硬外壳/毒素"
        elif traits.get("运动能力", 5) > 7:
            defense = "逃跑"
        elif traits.get("社会性", 5) > 6:
            defense = "结群"
        else:
            defense = "拟态/隐藏"
        
        # 推断繁殖策略
        if species.reproduction_r > 0.3:
            reproduction = "r策略-高繁殖"
        elif species.reproduction_r < 0.1:
            reproduction = "K策略-精育"
        else:
            reproduction = "中等繁殖-父母抚育"
        
        # 推断活动节律
        if traits.get("夜视能力", 5) > 6:
            activity = "夜行"
        elif traits.get("耐热性", 5) > 7:
            activity = "昼行"
        else:
            activity = "晨昏活动"
        
        # 推断社会行为
        social_val = traits.get("社会性", 5)
        if social_val > 8:
            social = "蜂群社会"
        elif social_val > 6:
            social = "大群"
        elif social_val > 4:
            social = "小群/配对"
        else:
            social = "独居"
        
        return BehaviorProfile(
            lineage_code=species.lineage_code,
            predation_strategy=predation,
            defense_strategy=defense,
            reproduction_strategy=reproduction,
            activity_pattern=activity,
            social_behavior=social,
            foraging_mode="主动搜寻" if traits.get("运动能力", 5) > 5 else "守株待兔",
            territorial_behavior="强领域" if traits.get("攻击性", 5) > 6 else "弱领域"
        )
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建行为策略向量索引"""
        store = self.embeddings._vector_stores.get_store(self.index_name)
        
        species_list = ctx.all_species or []
        if not species_list:
            return 0
        
        texts = []
        ids = []
        metadata_list = []
        
        for sp in species_list:
            profile = self.infer_behavior_profile(sp)
            text = profile.to_text()
            
            texts.append(text)
            ids.append(sp.lineage_code)
            metadata_list.append({
                "common_name": sp.common_name,
                "predation": profile.predation_strategy,
                "activity": profile.activity_pattern,
                "social": profile.social_behavior,
            })
        
        vectors = self.embeddings.embed(texts)
        return store.add_batch(ids, vectors, metadata_list)
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索行为相似的物种"""
        store = self.embeddings._vector_stores.get_store(self.index_name, create=False)
        if not store or store.size == 0:
            return []
        
        query_vec = self.embeddings.embed_single(query)
        results = store.search(query_vec, top_k)
        
        return [
            {
                "lineage_code": r.id,
                "similarity": r.score,
                **r.metadata
            }
            for r in results
        ]
    
    def find_behavior_conflicts(
        self, 
        species_a: 'Species', 
        species_b: 'Species'
    ) -> list[str]:
        """检测两个物种之间的行为冲突"""
        profile_a = self.infer_behavior_profile(species_a)
        profile_b = self.infer_behavior_profile(species_b)
        
        conflicts = []
        
        # 活动节律冲突
        if profile_a.activity_pattern != profile_b.activity_pattern:
            if set([profile_a.activity_pattern, profile_b.activity_pattern]) == {"昼行", "夜行"}:
                conflicts.append(f"活动节律完全错开: {profile_a.activity_pattern} vs {profile_b.activity_pattern}")
        
        # 领域冲突
        if profile_a.territorial_behavior == "强领域" and profile_b.territorial_behavior == "强领域":
            conflicts.append("双方都有强领域行为，可能产生激烈竞争")
        
        # 捕食者-猎物关系推断
        if "顶级掠食者" in profile_a.predation_strategy and "逃跑" in profile_b.defense_strategy:
            conflicts.append("捕食者-猎物关系: A捕食B")
        
        return conflicts
    
    def predict_adoptable_behaviors(
        self, 
        species: 'Species', 
        top_k: int = 3
    ) -> list[dict[str, Any]]:
        """预测物种可能采纳的新行为（向量空间中方向相似的行为）"""
        profile = self.infer_behavior_profile(species)
        current_vec = self.embeddings.embed_single(profile.to_text())
        
        # 搜索相似但不完全相同的行为模式
        results = self.search(profile.to_text(), top_k=top_k + 1)
        
        adoptable = []
        for r in results:
            if r["lineage_code"] != species.lineage_code:
                # 分析差异
                diff_behaviors = []
                if r.get("predation") != profile.predation_strategy:
                    diff_behaviors.append(f"捕食策略: {r.get('predation')}")
                if r.get("activity") != profile.activity_pattern:
                    diff_behaviors.append(f"活动节律: {r.get('activity')}")
                if r.get("social") != profile.social_behavior:
                    diff_behaviors.append(f"社会行为: {r.get('social')}")
                
                if diff_behaviors:
                    adoptable.append({
                        "reference_species": r["lineage_code"],
                        "similarity": r["similarity"],
                        "potential_behaviors": diff_behaviors
                    })
        
        return adoptable[:top_k]
```

---

### 3.2 生态网络向量 (Food Web Embedding)

#### 目标

将食物网关系（捕食、竞争、共生）编码为向量，用于：
- 快速判断生态稳定性
- 识别关键物种 (Keystone Species)
- 灭绝后的补位预测
- 生态中心性分析

#### 实现

```python
# backend/app/services/embedding_plugins/food_web_embedding.py

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...simulation.context import SimulationContext

@dataclass
class EcologicalPosition:
    """物种生态网络位置"""
    lineage_code: str
    predators: list[str] = field(default_factory=list)
    prey: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    mutualists: list[str] = field(default_factory=list)
    
    def to_text(self) -> str:
        """转换为文本描述"""
        parts = [f"物种 {self.lineage_code} 的生态关系:"]
        
        if self.predators:
            parts.append(f"被 {', '.join(self.predators[:5])} 等捕食")
        if self.prey:
            parts.append(f"捕食 {', '.join(self.prey[:5])} 等")
        if self.competitors:
            parts.append(f"与 {', '.join(self.competitors[:5])} 竞争")
        if self.mutualists:
            parts.append(f"与 {', '.join(self.mutualists[:5])} 共生")
        
        # 计算网络度
        total_connections = len(self.predators) + len(self.prey) + len(self.competitors) + len(self.mutualists)
        parts.append(f"总连接数: {total_connections}")
        
        return "; ".join(parts)
    
    @property
    def degree(self) -> int:
        """网络度（连接总数）"""
        return len(self.predators) + len(self.prey) + len(self.competitors) + len(self.mutualists)


@register_plugin("food_web")
class FoodWebEmbeddingPlugin(EmbeddingPlugin):
    """生态网络向量插件"""
    
    @property
    def name(self) -> str:
        return "food_web"
    
    def _do_initialize(self) -> None:
        self._position_cache: dict[str, EcologicalPosition] = {}
    
    def build_ecological_positions(
        self, 
        ctx: 'SimulationContext'
    ) -> dict[str, EcologicalPosition]:
        """从 SimulationContext 构建生态位置信息"""
        positions: dict[str, EcologicalPosition] = {}
        
        # 从食物网数据构建
        food_web = ctx.trophic_interactions or {}
        
        for code in [sp.lineage_code for sp in (ctx.all_species or [])]:
            positions[code] = EcologicalPosition(lineage_code=code)
        
        # 解析捕食关系
        for predator_code, prey_list in food_web.items():
            if predator_code in positions:
                positions[predator_code].prey = [p["code"] for p in prey_list if isinstance(p, dict)]
            
            # 反向记录被捕食关系
            for prey_info in prey_list:
                prey_code = prey_info["code"] if isinstance(prey_info, dict) else prey_info
                if prey_code in positions:
                    positions[prey_code].predators.append(predator_code)
        
        # 推断竞争关系（相同营养级、相似生态位）
        species_by_trophic = {}
        for sp in (ctx.all_species or []):
            level = round(sp.trophic_level)
            if level not in species_by_trophic:
                species_by_trophic[level] = []
            species_by_trophic[level].append(sp.lineage_code)
        
        for level, codes in species_by_trophic.items():
            for i, code_a in enumerate(codes):
                for code_b in codes[i+1:]:
                    if code_a in positions and code_b in positions:
                        positions[code_a].competitors.append(code_b)
                        positions[code_b].competitors.append(code_a)
        
        self._position_cache = positions
        return positions
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建生态网络向量索引"""
        store = self.embeddings._vector_stores.get_store(self.index_name)
        
        positions = self.build_ecological_positions(ctx)
        if not positions:
            return 0
        
        texts = []
        ids = []
        metadata_list = []
        
        for code, pos in positions.items():
            texts.append(pos.to_text())
            ids.append(code)
            metadata_list.append({
                "degree": pos.degree,
                "predator_count": len(pos.predators),
                "prey_count": len(pos.prey),
                "competitor_count": len(pos.competitors),
            })
        
        vectors = self.embeddings.embed(texts)
        return store.add_batch(ids, vectors, metadata_list)
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索生态位置相似的物种"""
        store = self.embeddings._vector_stores.get_store(self.index_name, create=False)
        if not store or store.size == 0:
            return []
        
        query_vec = self.embeddings.embed_single(query)
        results = store.search(query_vec, top_k)
        
        return [{"lineage_code": r.id, "similarity": r.score, **r.metadata} for r in results]
    
    def find_keystone_species(self, top_k: int = 5) -> list[dict[str, Any]]:
        """识别关键物种（生态中心性最高的物种）
        
        关键物种特征：
        1. 高网络度（连接多个物种）
        2. 连接不同营养级
        3. 在向量空间中接近中心
        """
        store = self.embeddings._vector_stores.get_store(self.index_name, create=False)
        if not store or store.size == 0:
            return []
        
        # 计算所有向量的中心点
        import numpy as np
        
        all_ids = store.list_ids()
        vectors = []
        for code in all_ids:
            vec = store.get(code)
            if vec is not None:
                vectors.append(vec)
        
        if not vectors:
            return []
        
        center = np.mean(vectors, axis=0)
        
        # 计算到中心的距离
        candidates = []
        for i, code in enumerate(all_ids):
            if i < len(vectors):
                dist = np.linalg.norm(vectors[i] - center)
                pos = self._position_cache.get(code)
                degree = pos.degree if pos else 0
                
                # 综合评分：低距离 + 高度数
                score = degree / (1 + dist)
                candidates.append({
                    "lineage_code": code,
                    "degree": degree,
                    "centrality_score": float(score),
                    "distance_to_center": float(dist),
                })
        
        # 按评分排序
        candidates.sort(key=lambda x: x["centrality_score"], reverse=True)
        return candidates[:top_k]
    
    def find_replacement_candidates(
        self, 
        extinct_code: str, 
        top_k: int = 3
    ) -> list[dict[str, Any]]:
        """为灭绝物种寻找潜在补位物种
        
        补位物种应该与灭绝物种有相似的生态位置向量。
        """
        store = self.embeddings._vector_stores.get_store(self.index_name, create=False)
        if not store:
            return []
        
        extinct_vec = store.get(extinct_code)
        if extinct_vec is None:
            return []
        
        # 搜索相似物种（排除自己）
        results = store.search(extinct_vec, top_k + 1, exclude_ids={extinct_code})
        
        return [
            {
                "lineage_code": r.id,
                "similarity": r.score,
                "replacement_potential": r.score * 0.8,  # 简单评分
                **r.metadata
            }
            for r in results[:top_k]
        ]
    
    def calculate_ecosystem_stability(self, ctx: 'SimulationContext') -> dict[str, float]:
        """计算生态系统稳定性指标
        
        Returns:
            - connectance: 连接度（实际连接/最大可能连接）
            - average_degree: 平均网络度
            - keystone_concentration: 关键物种集中度
        """
        positions = self._position_cache or self.build_ecological_positions(ctx)
        
        if not positions:
            return {"connectance": 0, "average_degree": 0, "keystone_concentration": 0}
        
        n = len(positions)
        total_connections = sum(p.degree for p in positions.values())
        max_connections = n * (n - 1)  # 完全图的边数
        
        connectance = total_connections / max_connections if max_connections > 0 else 0
        average_degree = total_connections / n if n > 0 else 0
        
        # 关键物种集中度（度数分布的基尼系数）
        degrees = sorted([p.degree for p in positions.values()])
        if sum(degrees) > 0:
            n = len(degrees)
            index = sum((i + 1) * d for i, d in enumerate(degrees))
            keystone_concentration = (2 * index) / (n * sum(degrees)) - (n + 1) / n
        else:
            keystone_concentration = 0
        
        return {
            "connectance": connectance,
            "average_degree": average_degree,
            "keystone_concentration": keystone_concentration,
            "species_count": n,
        }
```

---

### 3.3 区域/地块向量 (Tile/Biome Embedding)

#### 目标

为每个地块生成综合向量，整合：
- 气候特征（温度、降水）
- 植被类型
- 地形特征
- 现有物种特点
- 土壤/资源信息

#### 应用

- 物种-地块匹配度计算（智能迁徙）
- 入侵成功率预测
- 生态热点识别
- 未来物种预测

#### 实现

```python
# backend/app/services/embedding_plugins/tile_embedding.py

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING
import numpy as np

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...simulation.context import SimulationContext
    from ...models.species import Species

@dataclass
class TileProfile:
    """地块综合档案"""
    tile_id: str
    biome: str
    temperature: float
    precipitation: float
    elevation: float
    vegetation_density: float
    soil_fertility: float
    species_diversity: int
    dominant_trophic_level: float
    special_features: list[str]
    
    def to_text(self) -> str:
        features = ", ".join(self.special_features) if self.special_features else "无"
        return f"""地块 {self.tile_id}:
生物群落: {self.biome}
温度: {self.temperature:.1f}°C
降水量: {self.precipitation:.0f}mm
海拔: {self.elevation:.0f}m
植被密度: {self.vegetation_density:.1%}
土壤肥力: {self.soil_fertility:.1f}/10
物种多样性: {self.species_diversity}种
主导营养级: {self.dominant_trophic_level:.1f}
特殊特征: {features}"""


@register_plugin("tile_biome")
class TileBiomePlugin(EmbeddingPlugin):
    """区域/地块向量插件"""
    
    @property
    def name(self) -> str:
        return "tile_biome"
    
    def _do_initialize(self) -> None:
        self._tile_profiles: dict[str, TileProfile] = {}
        self._species_tile_map: dict[str, list[str]] = {}  # tile_id -> [species_codes]
    
    def build_tile_profiles(self, ctx: 'SimulationContext') -> dict[str, TileProfile]:
        """从 Context 构建地块档案"""
        profiles = {}
        
        tiles = ctx.all_tiles or []
        habitats = ctx.all_habitats or {}
        
        # 构建物种-地块映射
        species_in_tile: dict[str, list] = {}
        for sp in (ctx.all_species or []):
            for pop in (sp.populations or []):
                tile_id = pop.get("tile_id", pop.get("habitat_id", ""))
                if tile_id:
                    if tile_id not in species_in_tile:
                        species_in_tile[tile_id] = []
                    species_in_tile[tile_id].append(sp)
        
        self._species_tile_map = {k: [s.lineage_code for s in v] for k, v in species_in_tile.items()}
        
        for tile in tiles:
            tile_id = str(tile.get("id", tile.get("tile_id", "")))
            
            # 获取生态信息
            habitat = habitats.get(tile_id, {})
            species_list = species_in_tile.get(tile_id, [])
            
            # 计算主导营养级
            if species_list:
                avg_trophic = sum(s.trophic_level for s in species_list) / len(species_list)
            else:
                avg_trophic = 1.0
            
            # 识别特殊特征
            features = []
            temp = tile.get("temperature", 20)
            precip = tile.get("precipitation", 500)
            
            if temp < 0:
                features.append("冰冻环境")
            elif temp > 35:
                features.append("极端高温")
            if precip > 2000:
                features.append("高降水热带")
            elif precip < 200:
                features.append("干旱荒漠")
            if tile.get("is_coastal"):
                features.append("沿海地带")
            if tile.get("has_river"):
                features.append("河流水系")
            
            profiles[tile_id] = TileProfile(
                tile_id=tile_id,
                biome=tile.get("biome", habitat.get("biome", "unknown")),
                temperature=temp,
                precipitation=precip,
                elevation=tile.get("elevation", 0),
                vegetation_density=tile.get("vegetation", habitat.get("vegetation_cover", 0.5)),
                soil_fertility=tile.get("fertility", 5.0),
                species_diversity=len(species_list),
                dominant_trophic_level=avg_trophic,
                special_features=features,
            )
        
        self._tile_profiles = profiles
        return profiles
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建地块向量索引"""
        store = self.embeddings._vector_stores.get_store(self.index_name)
        
        profiles = self.build_tile_profiles(ctx)
        if not profiles:
            return 0
        
        texts = []
        ids = []
        metadata_list = []
        
        for tile_id, profile in profiles.items():
            texts.append(profile.to_text())
            ids.append(tile_id)
            metadata_list.append({
                "biome": profile.biome,
                "temperature": profile.temperature,
                "species_count": profile.species_diversity,
            })
        
        vectors = self.embeddings.embed(texts)
        return store.add_batch(ids, vectors, metadata_list)
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索匹配的地块"""
        store = self.embeddings._vector_stores.get_store(self.index_name, create=False)
        if not store or store.size == 0:
            return []
        
        query_vec = self.embeddings.embed_single(query)
        results = store.search(query_vec, top_k)
        
        return [{"tile_id": r.id, "similarity": r.score, **r.metadata} for r in results]
    
    def calculate_species_tile_compatibility(
        self, 
        species: 'Species', 
        tile_id: str
    ) -> dict[str, float]:
        """计算物种与地块的兼容性
        
        Returns:
            - overall_compatibility: 综合兼容度 (0-1)
            - climate_match: 气候匹配度
            - niche_availability: 生态位可用性
            - competition_risk: 竞争风险
        """
        profile = self._tile_profiles.get(tile_id)
        if not profile:
            return {"overall_compatibility": 0}
        
        # 1. 气候匹配
        traits = species.abstract_traits or {}
        temp_tolerance = traits.get("温度耐受范围", 5)
        optimal_temp = 20  # 假设最优温度
        
        temp_diff = abs(profile.temperature - optimal_temp)
        climate_match = max(0, 1 - temp_diff / (10 + temp_tolerance * 3))
        
        # 2. 生态位可用性（物种多样性越低，空间越大）
        max_diversity = 50  # 假设最大容量
        niche_availability = max(0, 1 - profile.species_diversity / max_diversity)
        
        # 3. 竞争风险（基于营养级差异）
        trophic_diff = abs(species.trophic_level - profile.dominant_trophic_level)
        competition_risk = max(0, 1 - trophic_diff / 2)
        
        # 综合评分
        overall = (climate_match * 0.4 + niche_availability * 0.3 + (1 - competition_risk) * 0.3)
        
        return {
            "overall_compatibility": overall,
            "climate_match": climate_match,
            "niche_availability": niche_availability,
            "competition_risk": competition_risk,
        }
    
    def find_best_tiles_for_species(
        self, 
        species: 'Species', 
        top_k: int = 5
    ) -> list[dict[str, Any]]:
        """为物种找到最适合的地块（智能迁徙推荐）"""
        results = []
        
        for tile_id, profile in self._tile_profiles.items():
            compat = self.calculate_species_tile_compatibility(species, tile_id)
            if compat["overall_compatibility"] > 0.3:
                results.append({
                    "tile_id": tile_id,
                    "biome": profile.biome,
                    **compat
                })
        
        results.sort(key=lambda x: x["overall_compatibility"], reverse=True)
        return results[:top_k]
    
    def predict_invasion_success(
        self, 
        species: 'Species', 
        target_tile_id: str
    ) -> dict[str, Any]:
        """预测物种入侵成功率"""
        compat = self.calculate_species_tile_compatibility(species, target_tile_id)
        profile = self._tile_profiles.get(target_tile_id)
        
        if not profile:
            return {"success_probability": 0, "reason": "地块不存在"}
        
        # 入侵成功因素
        factors = {
            "habitat_suitability": compat["overall_compatibility"],
            "low_competition": 1 - compat["competition_risk"],
            "empty_niche": compat["niche_availability"],
            "species_r_strategy": min(1, species.reproduction_r / 0.3),  # 高繁殖率有利
        }
        
        # 综合概率
        success_prob = np.mean(list(factors.values()))
        
        return {
            "success_probability": success_prob,
            "factors": factors,
            "recommendation": "适合入侵" if success_prob > 0.6 else "入侵困难",
        }
    
    def find_ecological_hotspots(self, top_k: int = 10) -> list[dict[str, Any]]:
        """找出最具适应潜力的生态热点区域"""
        hotspots = []
        
        for tile_id, profile in self._tile_profiles.items():
            # 热点评分：高多样性 + 适宜气候 + 高肥力
            diversity_score = min(1, profile.species_diversity / 30)
            climate_score = max(0, 1 - abs(profile.temperature - 20) / 30)
            fertility_score = profile.soil_fertility / 10
            
            hotspot_score = (diversity_score * 0.4 + climate_score * 0.3 + fertility_score * 0.3)
            
            hotspots.append({
                "tile_id": tile_id,
                "biome": profile.biome,
                "hotspot_score": hotspot_score,
                "species_diversity": profile.species_diversity,
                "temperature": profile.temperature,
            })
        
        hotspots.sort(key=lambda x: x["hotspot_score"], reverse=True)
        return hotspots[:top_k]
```

---
---

### 3.4 Embedding 驱动的 Prompt 精简

#### 目标

使用向量相似度为 LLM 筛选最相关的上下文，减少 token 消耗：
- 只加入与物种最相似的历史事件
- 只加入相关的生态压力
- 动态调整 prompt 长度

#### 实现

```python
# backend/app/services/embedding_plugins/prompt_optimizer.py

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, List

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...simulation.context import SimulationContext
    from ...models.history import HistoryRecord

@dataclass
class PromptContext:
    """优化后的 Prompt 上下文"""
    species_summary: str
    relevant_events: List[str]
    relevant_pressures: List[str]
    similar_species_fates: List[str]
    estimated_tokens: int
    
    def to_prompt_section(self) -> str:
        """转换为 Prompt 文本段落"""
        sections = [f"【物种概要】\n{self.species_summary}"]
        
        if self.relevant_events:
            sections.append("【相关历史事件】\n" + "\n".join(f"- {e}" for e in self.relevant_events))
        
        if self.relevant_pressures:
            sections.append("【当前面临压力】\n" + "\n".join(f"- {p}" for p in self.relevant_pressures))
        
        if self.similar_species_fates:
            sections.append("【相似物种命运参考】\n" + "\n".join(f"- {f}" for f in self.similar_species_fates))
        
        return "\n\n".join(sections)


@register_plugin("prompt_optimizer")
class PromptOptimizerPlugin(EmbeddingPlugin):
    """Prompt 优化插件 - 使用 Embedding 精简 LLM 上下文"""
    
    DEFAULT_SIMILARITY_THRESHOLD = 0.65
    DEFAULT_MAX_EVENTS = 5
    DEFAULT_MAX_PRESSURES = 3
    DEFAULT_MAX_SIMILAR_FATES = 3
    
    @property
    def name(self) -> str:
        return "prompt_optimizer"
    
    def _do_initialize(self) -> None:
        self._event_index_built = False
        self._pressure_descriptions: dict[str, str] = {}
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建事件和压力的向量索引"""
        # 事件索引由 EmbeddingService 的 index_events_batch 处理
        # 这里只做增量更新检查
        
        events = self._collect_recent_events(ctx, last_n_turns=10)
        if events:
            self.embeddings.index_events_batch(events)
        
        self._event_index_built = True
        return len(events)
    
    def _collect_recent_events(
        self, 
        ctx: 'SimulationContext', 
        last_n_turns: int = 10
    ) -> list[dict]:
        """收集最近的事件用于索引"""
        events = []
        
        # 从 major_events 收集
        for event in (ctx.major_events or []):
            events.append({
                "id": f"turn_{ctx.turn_index}_{len(events)}",
                "title": event.get("title", event.get("type", "事件")),
                "description": event.get("description", str(event)),
                "metadata": {
                    "turn": ctx.turn_index,
                    "type": event.get("type", "unknown"),
                }
            })
        
        return events
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索相关事件"""
        return [
            {"id": r.id, "similarity": r.score, **r.metadata}
            for r in self.embeddings.search_events(query, top_k)
        ]
    
    def build_optimized_context(
        self,
        species: 'Species',
        ctx: 'SimulationContext',
        max_tokens: int = 1000
    ) -> PromptContext:
        """为物种构建优化的 LLM 上下文
        
        Args:
            species: 目标物种
            ctx: 当前模拟上下文
            max_tokens: 最大 token 数限制
        
        Returns:
            优化后的上下文对象
        """
        # 1. 构建物种描述向量
        species_text = self.embeddings.build_species_text(species)
        
        # 2. 搜索相关历史事件
        relevant_events = self._find_relevant_events(species_text, self.DEFAULT_MAX_EVENTS)
        
        # 3. 搜索相关压力
        relevant_pressures = self._find_relevant_pressures(species, ctx)
        
        # 4. 搜索相似物种的命运
        similar_fates = self._find_similar_species_fates(species, ctx)
        
        # 5. 构建摘要
        species_summary = self._build_species_summary(species)
        
        # 6. 估算 token 数并裁剪
        context = PromptContext(
            species_summary=species_summary,
            relevant_events=[e["description"][:150] for e in relevant_events],
            relevant_pressures=relevant_pressures,
            similar_species_fates=similar_fates,
            estimated_tokens=0
        )
        
        # 粗略估算 token 数（中文约 0.5 字/token）
        full_text = context.to_prompt_section()
        context.estimated_tokens = len(full_text) // 2
        
        # 如果超限，裁剪
        while context.estimated_tokens > max_tokens and (context.relevant_events or context.similar_species_fates):
            if len(context.relevant_events) > 2:
                context.relevant_events.pop()
            elif context.similar_species_fates:
                context.similar_species_fates.pop()
            else:
                break
            context.estimated_tokens = len(context.to_prompt_section()) // 2
        
        return context
    
    def _find_relevant_events(
        self, 
        species_text: str, 
        top_k: int
    ) -> list[dict]:
        """找到与物种最相关的历史事件"""
        results = self.embeddings.search_events(
            species_text, 
            top_k=top_k, 
            threshold=self.DEFAULT_SIMILARITY_THRESHOLD
        )
        
        return [
            {
                "id": r.id,
                "similarity": r.score,
                "description": r.metadata.get("description", ""),
                **r.metadata
            }
            for r in results
        ]
    
    def _find_relevant_pressures(
        self, 
        species: 'Species', 
        ctx: 'SimulationContext'
    ) -> list[str]:
        """找到与物种相关的当前压力"""
        relevant = []
        
        for pressure in (ctx.pressures or []):
            pressure_type = pressure.get("type", "")
            pressure_strength = pressure.get("strength", 0.5)
            
            # 基于物种特征判断相关性
            traits = species.abstract_traits or {}
            
            # 温度相关压力
            if "温度" in pressure_type or "climate" in pressure_type.lower():
                if traits.get("耐热性", 5) < 4 or traits.get("耐寒性", 5) < 4:
                    relevant.append(f"{pressure_type} (强度: {pressure_strength:.1f}) - 物种温度敏感")
            
            # 捕食压力
            if "predation" in pressure_type.lower() or "捕食" in pressure_type:
                if species.trophic_level < 3:
                    relevant.append(f"{pressure_type} (强度: {pressure_strength:.1f}) - 物种为猎物")
            
            # 资源竞争
            if "competition" in pressure_type.lower() or "竞争" in pressure_type:
                relevant.append(f"{pressure_type} (强度: {pressure_strength:.1f})")
        
        return relevant[:self.DEFAULT_MAX_PRESSURES]
    
    def _find_similar_species_fates(
        self, 
        species: 'Species', 
        ctx: 'SimulationContext'
    ) -> list[str]:
        """找到相似物种的命运作为参考"""
        fates = []
        
        # 从物种索引搜索相似物种
        species_text = self.embeddings.build_species_text(species)
        similar = self.embeddings.search_species(
            species_text, 
            top_k=self.DEFAULT_MAX_SIMILAR_FATES + 1,
            exclude_codes={species.lineage_code}
        )
        
        for result in similar:
            # 尝试获取该物种的状态信息
            code = result.id
            metadata = result.metadata
            
            status = metadata.get("status", "alive")
            name = metadata.get("common_name", code)
            
            if status == "extinct":
                fates.append(f"{name} 已灭绝 (相似度: {result.score:.2f})")
            elif status == "endangered":
                fates.append(f"{name} 濒危中 (相似度: {result.score:.2f})")
            else:
                fates.append(f"{name} 存活中 (相似度: {result.score:.2f})")
        
        return fates[:self.DEFAULT_MAX_SIMILAR_FATES]
    
    def _build_species_summary(self, species: 'Species') -> str:
        """构建简洁的物种摘要"""
        traits = species.abstract_traits or {}
        
        # 提取关键特征
        key_traits = []
        for trait, value in traits.items():
            if value > 7:
                key_traits.append(f"高{trait}")
            elif value < 3:
                key_traits.append(f"低{trait}")
        
        summary = f"{species.common_name} ({species.latin_name})"
        summary += f"\n营养级: {species.trophic_level:.1f}, 种群: {species.total_population}"
        
        if key_traits:
            summary += f"\n关键特征: {', '.join(key_traits[:5])}"
        
        return summary
    
    def get_token_savings(self, full_context_tokens: int, optimized_tokens: int) -> dict:
        """计算 token 节省统计"""
        savings = full_context_tokens - optimized_tokens
        savings_percent = (savings / full_context_tokens * 100) if full_context_tokens > 0 else 0
        
        return {
            "full_tokens": full_context_tokens,
            "optimized_tokens": optimized_tokens,
            "savings": savings,
            "savings_percent": round(savings_percent, 1),
        }
```

---

### 3.5 演化向量空间 (Evolution Vector Space)

#### 目标

建立"演化空间"，追踪和分析宏观演化趋势：
- 存储每次 LLM 输出的演化方向
- 周期性聚类分析
- 识别收敛演化模式
- 预测未来演化趋势

#### 实现

```python
# backend/app/services/embedding_plugins/evolution_space.py

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, List, Tuple
from collections import defaultdict
import numpy as np

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...simulation.context import SimulationContext

@dataclass
class EvolutionEvent:
    """演化事件记录"""
    turn: int
    species_code: str
    species_name: str
    direction_text: str  # LLM 输出的演化方向描述
    direction_vector: np.ndarray = field(default_factory=lambda: np.array([]))
    cluster_id: int = -1  # 聚类 ID


@dataclass
class EvolutionTrend:
    """演化趋势"""
    trend_id: int
    name: str
    description: str
    species_count: int
    centroid_vector: np.ndarray
    example_species: List[str]
    strength: float  # 趋势强度


@register_plugin("evolution_space")
class EvolutionSpacePlugin(EmbeddingPlugin):
    """演化向量空间插件"""
    
    @property
    def name(self) -> str:
        return "evolution_space"
    
    def _do_initialize(self) -> None:
        self._evolution_events: List[EvolutionEvent] = []
        self._trend_cache: List[EvolutionTrend] = []
        self._cluster_update_interval = 5  # 每 5 回合更新聚类
        self._last_cluster_turn = -1
        
        # 预定义的演化方向模板
        self._direction_templates = self._build_direction_templates()
    
    def _build_direction_templates(self) -> dict[str, str]:
        """预定义演化方向模板向量"""
        return {
            "cold_adaptation": "向寒冷环境适应，发展保温层、防冻蛋白、低代谢",
            "heat_adaptation": "向炎热环境适应，发展散热机制、夜行性、节水能力",
            "aquatic_transition": "向水生环境过渡，发展鳃呼吸、流线型身体、鳍状附肢",
            "terrestrial_transition": "向陆地环境过渡，发展肺呼吸、四肢、防干燥皮肤",
            "aerial_adaptation": "发展飞行能力，轻量化骨骼、翅膀、高效心肺",
            "size_increase": "体型增大，代谢率降低，寿命延长",
            "size_decrease": "体型缩小，代谢率升高，世代加快",
            "predator_specialization": "捕食者特化，发展锋利牙齿、敏锐感官、高速追逐",
            "defense_enhancement": "防御强化，发展坚硬外壳、毒素、拟态、群体行为",
            "social_evolution": "社会性演化，发展群体协作、通讯系统、分工",
            "sensory_enhancement": "感官强化，发展大眼睛、回声定位、电感受",
            "reproductive_shift_r": "向 r 策略转变，高繁殖率、快速发育、短寿命",
            "reproductive_shift_k": "向 K 策略转变，低繁殖率、高亲代投资、长寿命",
        }
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建演化事件索引"""
        store = self.embeddings._vector_stores.get_store(self.index_name)
        
        # 索引新的演化事件
        new_events = self._collect_evolution_events(ctx)
        
        if not new_events:
            return 0
        
        texts = [e.direction_text for e in new_events]
        vectors = self.embeddings.embed(texts)
        
        ids = [f"{e.turn}_{e.species_code}" for e in new_events]
        metadata_list = [
            {
                "turn": e.turn,
                "species_code": e.species_code,
                "species_name": e.species_name,
            }
            for e in new_events
        ]
        
        # 更新事件向量
        for i, event in enumerate(new_events):
            event.direction_vector = np.array(vectors[i])
            self._evolution_events.append(event)
        
        count = store.add_batch(ids, vectors, metadata_list)
        
        # 定期更新聚类
        if ctx.turn_index - self._last_cluster_turn >= self._cluster_update_interval:
            self._update_clusters()
            self._last_cluster_turn = ctx.turn_index
        
        return count
    
    def _collect_evolution_events(self, ctx: 'SimulationContext') -> List[EvolutionEvent]:
        """从上下文收集演化事件"""
        events = []
        
        # 从 AI 评估结果收集
        for result in (ctx.combined_results or []):
            if isinstance(result, dict):
                direction = result.get("evolution_direction", result.get("direction", ""))
                if direction:
                    events.append(EvolutionEvent(
                        turn=ctx.turn_index,
                        species_code=result.get("lineage_code", ""),
                        species_name=result.get("common_name", ""),
                        direction_text=direction if isinstance(direction, str) else ", ".join(direction),
                    ))
        
        # 从适应事件收集
        for event in (ctx.adaptation_events or []):
            if isinstance(event, dict):
                events.append(EvolutionEvent(
                    turn=ctx.turn_index,
                    species_code=event.get("species_code", ""),
                    species_name=event.get("species_name", ""),
                    direction_text=event.get("adaptation_type", "适应性变化"),
                ))
        
        return events
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索相似的演化事件"""
        store = self.embeddings._vector_stores.get_store(self.index_name, create=False)
        if not store or store.size == 0:
            return []
        
        query_vec = self.embeddings.embed_single(query)
        results = store.search(query_vec, top_k)
        
        return [{"id": r.id, "similarity": r.score, **r.metadata} for r in results]
    
    def _update_clusters(self) -> None:
        """更新演化趋势聚类"""
        if len(self._evolution_events) < 10:
            return
        
        # 收集所有向量
        vectors = np.array([e.direction_vector for e in self._evolution_events if len(e.direction_vector) > 0])
        
        if len(vectors) < 10:
            return
        
        # 使用简单的 K-Means 聚类
        try:
            from sklearn.cluster import KMeans
            
            n_clusters = min(8, len(vectors) // 5)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(vectors)
            
            # 更新事件的聚类标签
            for i, event in enumerate(self._evolution_events):
                if i < len(labels):
                    event.cluster_id = int(labels[i])
            
            # 生成趋势描述
            self._trend_cache = self._generate_trend_descriptions(kmeans.cluster_centers_, labels)
            
        except ImportError:
            # 降级为简单分组
            self._simple_clustering()
    
    def _simple_clustering(self) -> None:
        """简单聚类（无 sklearn 时的降级方案）"""
        # 基于模板向量的相似度分组
        templates_vecs = {}
        for name, desc in self._direction_templates.items():
            templates_vecs[name] = np.array(self.embeddings.embed_single(desc))
        
        for event in self._evolution_events:
            if len(event.direction_vector) == 0:
                continue
            
            best_match = None
            best_sim = -1
            
            for name, template_vec in templates_vecs.items():
                sim = float(np.dot(event.direction_vector, template_vec) / 
                           (np.linalg.norm(event.direction_vector) * np.linalg.norm(template_vec) + 1e-8))
                if sim > best_sim:
                    best_sim = sim
                    best_match = name
            
            event.cluster_id = list(self._direction_templates.keys()).index(best_match) if best_match else -1
    
    def _generate_trend_descriptions(
        self, 
        centroids: np.ndarray, 
        labels: np.ndarray
    ) -> List[EvolutionTrend]:
        """生成趋势描述"""
        trends = []
        
        for cluster_id in range(len(centroids)):
            # 找到属于该聚类的事件
            cluster_events = [e for e in self._evolution_events if e.cluster_id == cluster_id]
            
            if not cluster_events:
                continue
            
            # 找到最接近的模板
            centroid = centroids[cluster_id]
            best_template = self._find_closest_template(centroid)
            
            trends.append(EvolutionTrend(
                trend_id=cluster_id,
                name=best_template,
                description=self._direction_templates.get(best_template, "未知趋势"),
                species_count=len(cluster_events),
                centroid_vector=centroid,
                example_species=[e.species_name for e in cluster_events[:5]],
                strength=len(cluster_events) / len(self._evolution_events),
            ))
        
        # 按强度排序
        trends.sort(key=lambda t: t.strength, reverse=True)
        return trends
    
    def _find_closest_template(self, vector: np.ndarray) -> str:
        """找到最接近向量的模板名称"""
        best_match = "unknown"
        best_sim = -1
        
        for name, desc in self._direction_templates.items():
            template_vec = np.array(self.embeddings.embed_single(desc))
            sim = float(np.dot(vector, template_vec) / 
                       (np.linalg.norm(vector) * np.linalg.norm(template_vec) + 1e-8))
            if sim > best_sim:
                best_sim = sim
                best_match = name
        
        return best_match
    
    def get_current_trends(self, top_k: int = 5) -> List[dict[str, Any]]:
        """获取当前主要演化趋势"""
        return [
            {
                "trend_id": t.trend_id,
                "name": t.name,
                "description": t.description,
                "species_count": t.species_count,
                "strength": round(t.strength, 3),
                "examples": t.example_species,
            }
            for t in self._trend_cache[:top_k]
        ]
    
    def predict_species_trajectory(
        self, 
        species: 'Species'
    ) -> List[dict[str, Any]]:
        """预测物种的演化轨迹"""
        # 找到该物种的历史演化事件
        species_events = [e for e in self._evolution_events if e.species_code == species.lineage_code]
        
        if not species_events:
            return []
        
        # 计算演化方向的趋势
        recent_vectors = [e.direction_vector for e in species_events[-5:] if len(e.direction_vector) > 0]
        
        if not recent_vectors:
            return []
        
        # 平均方向向量
        avg_direction = np.mean(recent_vectors, axis=0)
        
        # 预测可能的未来方向
        predictions = []
        for name, desc in self._direction_templates.items():
            template_vec = np.array(self.embeddings.embed_single(desc))
            sim = float(np.dot(avg_direction, template_vec) / 
                       (np.linalg.norm(avg_direction) * np.linalg.norm(template_vec) + 1e-8))
            if sim > 0.5:
                predictions.append({
                    "direction": name,
                    "description": desc,
                    "probability": round(sim, 3),
                })
        
        predictions.sort(key=lambda x: x["probability"], reverse=True)
        return predictions[:3]
    
    def detect_convergent_evolution(self, min_species: int = 3) -> List[dict[str, Any]]:
        """检测收敛演化（多个不同物种向相同方向演化）"""
        convergences = []
        
        for trend in self._trend_cache:
            if trend.species_count >= min_species:
                # 检查物种是否来自不同谱系
                unique_lineages = set()
                for e in self._evolution_events:
                    if e.cluster_id == trend.trend_id:
                        # 取谱系代码的前缀作为"科"级别
                        lineage_family = e.species_code.split("_")[0] if "_" in e.species_code else e.species_code[:2]
                        unique_lineages.add(lineage_family)
                
                if len(unique_lineages) >= 2:
                    convergences.append({
                        "trend": trend.name,
                        "description": trend.description,
                        "species_count": trend.species_count,
                        "lineage_count": len(unique_lineages),
                        "examples": trend.example_species,
                    })
        
        return convergences
    
    def generate_world_event_feedback(self) -> List[str]:
        """生成可反馈给世界事件系统的演化趋势信息"""
        feedback = []
        
        for trend in self._trend_cache[:3]:
            if trend.strength > 0.2:
                feedback.append(f"宏观演化趋势: {trend.name} - {trend.description} ({trend.species_count} 个物种)")
        
        # 检测异常
        convergences = self.detect_convergent_evolution()
        for conv in convergences:
            feedback.append(f"收敛演化警报: 多个不同谱系向 '{conv['trend']}' 方向演化")
        
        return feedback
    
    def export_for_save(self) -> dict[str, Any]:
        """导出演化空间数据"""
        return {
            "name": self.name,
            "last_update": self._last_update_turn,
            "last_cluster_turn": self._last_cluster_turn,
            "event_count": len(self._evolution_events),
            # 只保存最近 100 个事件的概要
            "recent_events": [
                {
                    "turn": e.turn,
                    "species_code": e.species_code,
                    "direction": e.direction_text[:100],
                    "cluster": e.cluster_id,
                }
                for e in self._evolution_events[-100:]
            ]
        }
```

---

### 3.6 物种记忆与血统压缩 (Ancestry Embedding)

#### 目标

使用 embedding 压缩物种的历史和血统信息：
- 血统语义压缩
- 遗传惯性预测
- 分化信号评估
- 历史数据降维

#### 实现

```python
# backend/app/services/embedding_plugins/ancestry_embedding.py

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, List, Optional
import numpy as np

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...simulation.context import SimulationContext

@dataclass
class AncestryVector:
    """血统向量"""
    lineage_code: str
    vector: np.ndarray
    generation: int
    ancestor_codes: List[str]
    key_events: List[str]
    trait_history: dict[str, List[float]]  # 特征历史变化
    
    @property
    def dimension(self) -> int:
        return len(self.vector)


@register_plugin("ancestry")
class AncestryEmbeddingPlugin(EmbeddingPlugin):
    """物种记忆与血统压缩插件"""
    
    @property
    def name(self) -> str:
        return "ancestry"
    
    def _do_initialize(self) -> None:
        self._ancestry_cache: dict[str, AncestryVector] = {}
        self._trait_history: dict[str, dict[str, List[float]]] = {}  # code -> {trait -> values}
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建血统向量索引"""
        store = self.embeddings._vector_stores.get_store(self.index_name)
        
        species_list = ctx.all_species or []
        if not species_list:
            return 0
        
        updated = 0
        for sp in species_list:
            ancestry_vec = self._compute_ancestry_vector(sp, ctx)
            if ancestry_vec:
                store.add(
                    sp.lineage_code, 
                    ancestry_vec.vector.tolist(),
                    {
                        "generation": ancestry_vec.generation,
                        "ancestor_count": len(ancestry_vec.ancestor_codes),
                        "event_count": len(ancestry_vec.key_events),
                    }
                )
                self._ancestry_cache[sp.lineage_code] = ancestry_vec
                updated += 1
        
        return updated
    
    def _compute_ancestry_vector(
        self, 
        species: 'Species', 
        ctx: 'SimulationContext'
    ) -> Optional[AncestryVector]:
        """计算物种的血统向量
        
        公式: ancestry_vector = weighted_avg(ancestor_vectors) + weighted_avg(key_event_vectors)
        """
        # 1. 收集祖先信息
        ancestor_codes = self._get_ancestor_chain(species)
        ancestor_texts = []
        
        for code in ancestor_codes[-5:]:  # 最近 5 代祖先
            ancestor_sp = self._find_species_by_code(code, ctx)
            if ancestor_sp:
                ancestor_texts.append(self.embeddings.build_species_text(ancestor_sp))
        
        # 2. 收集关键事件
        key_events = self._get_key_events(species, ctx)
        event_texts = [e[:200] for e in key_events[-5:]]  # 最近 5 个关键事件
        
        # 3. 当前物种文本
        current_text = self.embeddings.build_species_text(species)
        
        # 4. 生成向量
        all_texts = [current_text] + ancestor_texts + event_texts
        if not all_texts:
            return None
        
        vectors = self.embeddings.embed(all_texts)
        
        # 5. 加权平均
        # 当前物种权重最高，祖先权重递减，事件权重较低
        weights = [1.0]  # 当前物种
        weights.extend([0.8 ** i for i in range(len(ancestor_texts))])  # 祖先递减
        weights.extend([0.3] * len(event_texts))  # 事件
        
        # 归一化权重
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # 加权平均
        ancestry_vector = np.zeros(len(vectors[0]))
        for i, vec in enumerate(vectors):
            ancestry_vector += weights[i] * np.array(vec)
        
        # 归一化
        norm = np.linalg.norm(ancestry_vector)
        if norm > 0:
            ancestry_vector = ancestry_vector / norm
        
        # 6. 更新特征历史
        self._update_trait_history(species)
        
        return AncestryVector(
            lineage_code=species.lineage_code,
            vector=ancestry_vector,
            generation=self._estimate_generation(species),
            ancestor_codes=ancestor_codes,
            key_events=key_events,
            trait_history=self._trait_history.get(species.lineage_code, {}),
        )
    
    def _get_ancestor_chain(self, species: 'Species') -> List[str]:
        """获取祖先链"""
        ancestors = []
        
        # 从谱系代码解析
        code = species.lineage_code
        parts = code.split("_")
        
        # 假设格式: A_B_C 表示 A 是祖先，B 是父代，C 是当前
        for i in range(len(parts) - 1):
            ancestor_code = "_".join(parts[:i+1])
            ancestors.append(ancestor_code)
        
        return ancestors
    
    def _get_key_events(
        self, 
        species: 'Species', 
        ctx: 'SimulationContext'
    ) -> List[str]:
        """获取物种相关的关键事件"""
        events = []
        
        # 从 branching_events 获取分化事件
        for event in (ctx.branching_events or []):
            if isinstance(event, dict):
                if species.lineage_code in str(event):
                    events.append(f"分化事件: {event.get('description', str(event))}")
        
        # 从 adaptation_events 获取适应事件
        for event in (ctx.adaptation_events or []):
            if isinstance(event, dict):
                if event.get("species_code") == species.lineage_code:
                    events.append(f"适应事件: {event.get('adaptation_type', '未知')}")
        
        return events
    
    def _find_species_by_code(
        self, 
        code: str, 
        ctx: 'SimulationContext'
    ) -> Optional['Species']:
        """根据代码查找物种"""
        for sp in (ctx.all_species or []):
            if sp.lineage_code == code:
                return sp
        return None
    
    def _estimate_generation(self, species: 'Species') -> int:
        """估算物种代数"""
        # 基于谱系代码长度估算
        return len(species.lineage_code.split("_"))
    
    def _update_trait_history(self, species: 'Species') -> None:
        """更新特征历史记录"""
        code = species.lineage_code
        
        if code not in self._trait_history:
            self._trait_history[code] = {}
        
        traits = species.abstract_traits or {}
        for trait, value in traits.items():
            if trait not in self._trait_history[code]:
                self._trait_history[code][trait] = []
            self._trait_history[code][trait].append(value)
            
            # 限制历史长度
            if len(self._trait_history[code][trait]) > 20:
                self._trait_history[code][trait] = self._trait_history[code][trait][-20:]
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索血统相似的物种"""
        store = self.embeddings._vector_stores.get_store(self.index_name, create=False)
        if not store or store.size == 0:
            return []
        
        query_vec = self.embeddings.embed_single(query)
        results = store.search(query_vec, top_k)
        
        return [{"lineage_code": r.id, "similarity": r.score, **r.metadata} for r in results]
    
    def predict_genetic_inertia(
        self, 
        species: 'Species', 
        target_trait: str
    ) -> dict[str, Any]:
        """预测遗传惯性
        
        遗传惯性 = 祖先特征的一致性程度
        如果祖先都是草食，则向肉食演化更困难
        """
        ancestry = self._ancestry_cache.get(species.lineage_code)
        if not ancestry:
            return {"inertia": 0.5, "confidence": 0}
        
        # 分析特征历史
        trait_history = ancestry.trait_history.get(target_trait, [])
        
        if len(trait_history) < 2:
            return {"inertia": 0.5, "confidence": 0.1}
        
        # 计算历史变化幅度
        history_array = np.array(trait_history)
        variance = np.var(history_array)
        mean_value = np.mean(history_array)
        
        # 低变化 = 高惯性
        inertia = 1 / (1 + variance)
        
        # 方向性（是否一直在增加或减少）
        if len(trait_history) >= 3:
            trend = np.polyfit(range(len(trait_history)), trait_history, 1)[0]
        else:
            trend = 0
        
        return {
            "inertia": round(inertia, 3),
            "mean_value": round(mean_value, 2),
            "variance": round(variance, 3),
            "trend": round(trend, 3),
            "trend_direction": "increasing" if trend > 0.1 else ("decreasing" if trend < -0.1 else "stable"),
            "confidence": min(1.0, len(trait_history) / 10),
        }
    
    def should_speciate(
        self, 
        species: 'Species', 
        threshold: float = 0.6
    ) -> dict[str, Any]:
        """判断是否应该发生物种分化
        
        基于血统向量的变化程度
        """
        ancestry = self._ancestry_cache.get(species.lineage_code)
        if not ancestry or len(ancestry.ancestor_codes) == 0:
            return {"should_speciate": False, "reason": "无祖先数据"}
        
        # 获取最近祖先的向量
        parent_code = ancestry.ancestor_codes[-1] if ancestry.ancestor_codes else None
        
        if not parent_code or parent_code not in self._ancestry_cache:
            return {"should_speciate": False, "reason": "无法获取父代向量"}
        
        parent_ancestry = self._ancestry_cache[parent_code]
        
        # 计算与父代的向量距离
        distance = np.linalg.norm(ancestry.vector - parent_ancestry.vector)
        
        # 距离超过阈值则应该分化
        should_speciate = distance > threshold
        
        return {
            "should_speciate": should_speciate,
            "distance_from_parent": round(distance, 3),
            "threshold": threshold,
            "generation": ancestry.generation,
            "reason": "血统向量与祖先差异过大" if should_speciate else "仍在祖先变异范围内",
        }
    
    def calculate_divergence_score(
        self, 
        species_a: 'Species', 
        species_b: 'Species'
    ) -> dict[str, Any]:
        """计算两个物种的分化程度"""
        ancestry_a = self._ancestry_cache.get(species_a.lineage_code)
        ancestry_b = self._ancestry_cache.get(species_b.lineage_code)
        
        if not ancestry_a or not ancestry_b:
            return {"divergence": 0, "confidence": 0}
        
        # 血统向量距离
        vector_distance = np.linalg.norm(ancestry_a.vector - ancestry_b.vector)
        
        # 找共同祖先
        common_ancestors = set(ancestry_a.ancestor_codes) & set(ancestry_b.ancestor_codes)
        
        # 代数差异
        generation_diff = abs(ancestry_a.generation - ancestry_b.generation)
        
        # 综合分化分数
        divergence = vector_distance * 0.6 + (1 - len(common_ancestors) / max(len(ancestry_a.ancestor_codes), 1)) * 0.3 + min(generation_diff / 10, 0.1)
        
        return {
            "divergence": round(divergence, 3),
            "vector_distance": round(vector_distance, 3),
            "common_ancestor_count": len(common_ancestors),
            "generation_diff": generation_diff,
            "confidence": 0.8 if ancestry_a.generation > 2 and ancestry_b.generation > 2 else 0.4,
        }
    
    def get_compressed_lineage_data(self, species: 'Species') -> dict[str, Any]:
        """获取压缩后的谱系数据（用于存档）"""
        ancestry = self._ancestry_cache.get(species.lineage_code)
        if not ancestry:
            return {}
        
        return {
            "lineage_code": ancestry.lineage_code,
            "vector": ancestry.vector.tolist(),
            "generation": ancestry.generation,
            "ancestor_count": len(ancestry.ancestor_codes),
            "key_event_count": len(ancestry.key_events),
            # 压缩后的特征摘要（而非完整历史）
            "trait_summary": {
                trait: {
                    "mean": round(np.mean(values), 2),
                    "trend": round(np.polyfit(range(len(values)), values, 1)[0], 3) if len(values) >= 2 else 0
                }
                for trait, values in ancestry.trait_history.items()
                if values
            }
        }
```

---

## 4. 模块复用机制

### 4.1 共享向量服务

所有插件通过 `EmbeddingService` 共享以下能力：

```python
# 共享能力
class EmbeddingService:
    # 文本 -> 向量
    def embed(self, texts: list[str]) -> list[list[float]]
    
    # 向量存储管理
    def _vector_stores.get_store(name: str) -> VectorStore
    
    # 相似度搜索
    def search_species(query: str, top_k: int) -> list[SearchResult]
    
    # 统一的物种文本构建
    @staticmethod
    def build_species_text(species, include_traits=True) -> str
```

### 4.2 插件间数据共享

通过 `SimulationContext` 传递数据：

```python
# context.py 扩展
@dataclass
class SimulationContext:
    # ... 现有字段 ...
    
    # 插件共享数据
    plugin_data: dict[str, Any] = field(default_factory=dict)
    
    def set_plugin_data(self, plugin_name: str, key: str, value: Any) -> None:
        if plugin_name not in self.plugin_data:
            self.plugin_data[plugin_name] = {}
        self.plugin_data[plugin_name][key] = value
    
    def get_plugin_data(self, plugin_name: str, key: str, default: Any = None) -> Any:
        return self.plugin_data.get(plugin_name, {}).get(key, default)
```

### 4.3 复用模式

| 模式 | 描述 | 示例 |
|------|------|------|
| **向量共享** | 插件可以访问其他插件的向量索引 | `food_web` 插件使用 `behavior_strategy` 的向量增强关系预测 |
| **结果复用** | 通过 Context 共享中间结果 | `prompt_optimizer` 使用 `evolution_space` 的趋势数据 |
| **服务委托** | 插件调用 EmbeddingService 的统一方法 | 所有插件使用 `build_species_text()` 确保向量一致性 |

---

## 5. API 接口设计

### 5.1 新增 API 端点

在 `embedding_routes.py` 中添加：

```python
# ==================== 行为策略 API ====================

@router.get("/behavior/profile/{species_code}")
async def get_behavior_profile(species_code: str) -> dict:
    """获取物种行为档案"""

@router.post("/behavior/conflicts")
async def check_behavior_conflicts(request: BehaviorConflictRequest) -> dict:
    """检测行为冲突"""

@router.get("/behavior/similar/{species_code}")
async def find_similar_behaviors(species_code: str, top_k: int = 5) -> dict:
    """查找行为相似的物种"""

# ==================== 生态网络 API ====================

@router.get("/food-web/keystone")
async def get_keystone_species(top_k: int = 5) -> dict:
    """获取关键物种"""

@router.get("/food-web/stability")
async def get_ecosystem_stability() -> dict:
    """获取生态稳定性指标"""

@router.post("/food-web/replacement")
async def find_replacement(request: ReplacementRequest) -> dict:
    """为灭绝物种找补位候选"""

# ==================== 地块向量 API ====================

@router.get("/tiles/hotspots")
async def get_ecological_hotspots(top_k: int = 10) -> dict:
    """获取生态热点"""

@router.post("/tiles/species-match")
async def match_species_to_tiles(request: SpeciesTileRequest) -> dict:
    """物种-地块匹配"""

@router.post("/tiles/invasion-prediction")
async def predict_invasion(request: InvasionPredictionRequest) -> dict:
    """预测入侵成功率"""

# ==================== 演化空间 API ====================

@router.get("/evolution/trends")
async def get_evolution_trends(top_k: int = 5) -> dict:
    """获取当前演化趋势"""

@router.get("/evolution/convergent")
async def detect_convergent_evolution() -> dict:
    """检测收敛演化"""

@router.get("/evolution/trajectory/{species_code}")
async def predict_trajectory(species_code: str) -> dict:
    """预测物种演化轨迹"""

# ==================== 血统向量 API ====================

@router.get("/ancestry/{species_code}")
async def get_ancestry_vector(species_code: str) -> dict:
    """获取血统向量"""

@router.get("/ancestry/inertia/{species_code}/{trait}")
async def get_genetic_inertia(species_code: str, trait: str) -> dict:
    """获取遗传惯性"""

@router.post("/ancestry/divergence")
async def calculate_divergence(request: DivergenceRequest) -> dict:
    """计算分化程度"""
```

### 5.2 Response Schema

```python
# schemas/embedding_extensions.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any

class BehaviorProfileResponse(BaseModel):
    lineage_code: str
    predation_strategy: str
    defense_strategy: str
    reproduction_strategy: str
    activity_pattern: str
    social_behavior: str

class EcosystemStabilityResponse(BaseModel):
    connectance: float
    average_degree: float
    keystone_concentration: float
    species_count: int

class EvolutionTrendResponse(BaseModel):
    trends: List[Dict[str, Any]]
    convergent_evolutions: List[Dict[str, Any]]

class AncestryResponse(BaseModel):
    lineage_code: str
    generation: int
    ancestor_count: int
    inertia: Dict[str, float]
    should_speciate: bool
```

---

## 6. 实施计划

### Phase 1: 基础架构（1-2 周）

- [ ] 创建 `embedding_plugins/` 目录结构
- [ ] 实现 `EmbeddingPlugin` 基类
- [ ] 实现 `PluginRegistry` 和 `PluginManager`
- [ ] 修改 `EmbeddingIntegrationService` 集成插件管理
- [ ] 更新 `SimulationContext` 添加插件数据共享

### Phase 2: 核心插件（2-3 周）

- [ ] 实现 `BehaviorStrategyPlugin`
- [ ] 实现 `FoodWebEmbeddingPlugin`
- [ ] 实现 `TileBiomePlugin`
- [ ] 编写单元测试

### Phase 3: 高级功能（2-3 周）

- [ ] 实现 `PromptOptimizerPlugin`
- [ ] 实现 `EvolutionSpacePlugin`
- [ ] 实现 `AncestryEmbeddingPlugin`
- [ ] 集成测试

### Phase 4: API 与集成（1 周）

- [ ] 扩展 `embedding_routes.py`
- [ ] 更新前端 API 类型
- [ ] 添加到 `stage_config.yaml`
- [ ] 文档更新

### 目录结构

```
backend/app/services/
├── embedding_plugins/
│   ├── __init__.py
│   ├── base.py              # 插件基类
│   ├── registry.py          # 插件注册器
│   ├── manager.py           # 插件管理器
│   ├── behavior_strategy.py # 行为策略插件
│   ├── food_web_embedding.py # 生态网络插件
│   ├── tile_embedding.py    # 地块向量插件
│   ├── prompt_optimizer.py  # Prompt 优化插件
│   ├── evolution_space.py   # 演化空间插件
│   └── ancestry_embedding.py # 血统向量插件
├── system/
│   ├── embedding.py         # 核心 EmbeddingService
│   └── vector_store.py      # 向量存储
└── analytics/
    └── embedding_integration.py # 集成层（更新）
```

---

## 附录：配置示例

### stage_config.yaml 更新

```yaml
# 添加新的插件配置阶段
- name: embedding_plugins_update
  enabled: true
  order: 166  # 在 embedding_hooks 之后
  params:
    plugins:
      - behavior_strategy
      - food_web
      - tile_biome
      - prompt_optimizer
      - evolution_space
      - ancestry
```

### 插件配置文件

```yaml
# config/embedding_plugins.yaml
plugins:
  behavior_strategy:
    enabled: true
    update_frequency: 1
    
  food_web:
    enabled: true
    update_frequency: 1
    keystone_threshold: 0.7
    
  tile_biome:
    enabled: true
    update_frequency: 5  # 地块变化较慢
    
  prompt_optimizer:
    enabled: true
    max_tokens: 1000
    similarity_threshold: 0.65
    
  evolution_space:
    enabled: true
    cluster_interval: 5
    min_events_for_clustering: 10
    
  ancestry:
    enabled: true
    max_ancestor_depth: 10
    speciation_threshold: 0.6
```


