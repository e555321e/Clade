# Embedding 扩展模块指南

聚焦 Embedding 向量系统的插件化扩展功能。

## 实现状态

| 组件 | 状态 | 说明 |
|------|------|------|
| 插件框架 | ✅ 已实现 | base.py, registry.py, manager.py |
| YAML 配置 | ✅ 已实现 | `config/embedding_plugins.yaml` + config_loader.py |
| 生命周期钩子 | ✅ 已实现 | on_turn_start (InitStage) + on_turn_end |
| 数据质量检查 | ✅ 已实现 | `_check_data_quality()` + 降级日志 |
| 性能监控 | ✅ 已实现 | 索引大小、构建耗时、更新频率 |
| API 防护 | ✅ 已实现 | 索引空检测、明确错误信息 |
| behavior_strategy | ✅ MVP | 行为推断、搜索、冲突检测 |
| food_web | ✅ MVP | 生态位置、关键物种、补位预测 |
| tile_biome | ✅ MVP | 地块匹配、热点识别 |
| prompt_optimizer | ✅ MVP | 上下文精简、相关事件筛选 |
| evolution_space | ✅ MVP | 趋势分析、收敛演化检测 |
| ancestry | ✅ MVP | 遗传惯性、分化评估 |
| Stage 集成 | ✅ 已实现 | `embedding_plugins` Stage (order: 166) |
| API 路由 | ✅ 已实现 | 30+ 端点，完善的错误处理 |
| 单元测试 | ✅ 已实现 | tests/test_plugins.py |

## 模式启用状态

| 模式 | embedding_plugins | 启用的插件 | 更新频率 |
|------|-------------------|-----------|---------|
| minimal | ❌ 禁用 | - | - |
| standard | ✅ 启用 | behavior(3), food_web(5), tile_biome(10) | 低频 |
| full | ✅ 启用 | 全部 6 个 | 标准 |
| debug | ✅ 启用 | 全部 6 个 | 每回合 |

> **注意**: `standard` 模式下仅启用核心插件，且使用较低的更新频率以减少性能开销。

## 配置

### 配置文件

插件配置从以下位置加载（优先级从低到高）：

1. `backend/app/config/embedding_plugins.yaml` - 基础配置
2. `embedding_plugins.yaml` 中的 `mode_presets` - 模式预设
3. `stage_config.yaml` 中的 `embedding_plugins.plugins` - 模式覆盖

### 配置生效机制

`EmbeddingPluginsStage` 和 API 路由会自动：
1. 从 `engine._pipeline_mode` 获取当前模式
2. 传递 `stage_config.yaml` 路径给 `EmbeddingPluginManager`
3. 按模式加载对应的插件配置

### 配置项

```yaml
plugins:
  behavior_strategy:
    enabled: true           # 是否启用
    update_frequency: 2     # 每 N 回合更新索引
    params:                 # 插件特定参数
      similarity_threshold: 0.7
```

### 调整更新频率

重计算成本高的插件（tile_biome, food_web）默认使用较高的 update_frequency：
- `tile_biome`: 默认每 5 回合（full）/ 10 回合（standard）
- `food_web`: 默认每 3 回合（full）/ 5 回合（standard）
- `behavior_strategy`: 默认每 2 回合

### 仅加载配置的插件

默认情况下，管理器会加载所有注册的插件，然后按配置过滤 `enabled`。

如需仅加载配置文件中明确列出的插件，可使用：

```python
manager = EmbeddingPluginManager(
    embedding_service,
    mode="standard",
    only_configured=True  # 仅加载配置中出现的插件
)
```

## 职责

- 提供插件化的向量嵌入扩展架构
- 支持行为策略、生态网络、区域地块的向量化
- 实现 Prompt 优化、演化空间分析、血统压缩等高级功能
- 所有插件共享 `EmbeddingService` 核心能力
- 必需字段缺失时自动降级并记录警告

## 依赖

- `backend/app/services/system/embedding.py` - 核心向量服务
- `backend/app/services/system/vector_store.py` - Faiss 向量存储
- `backend/app/services/embedding_plugins/` - 插件目录
- `backend/app/config/embedding_plugins.yaml` - 配置文件

## 插件数据共享

插件之间可以通过 `SimulationContext.plugin_data` 共享数据：

```python
# 写入数据
self.set_plugin_data(ctx, "my_cache", {...})

# 读取自己的数据
data = self.get_plugin_data(ctx, "my_cache", default={})

# 读取其他插件的数据
other_data = self.get_other_plugin_data(ctx, "food_web", "keystone_species")
```

## 数据契约

### 各插件的数据需求

| 插件 | 必需字段 | 推荐字段 | 降级行为 |
|------|---------|---------|---------|
| `behavior_strategy` | `all_species` | `abstract_traits` | 从 trophic_level 推断行为 |
| `food_web` | `all_species` | `prey_species`, `food_web_analysis` | 仅用 trophic_level 构建网络 |
| `tile_biome` | `all_tiles` | `all_habitats`, `populations` | 跳过索引构建 |

### Species 模型说明

> **注意**: `reproduction_r` 不是 Species 模型的显式字段。
> 插件会从 `abstract_traits["繁殖力"]` 推断繁殖率。

### 数据质量警告

缺少推荐字段时，日志会显示：

```
[behavior_strategy] 数据质量提示: 使用降级模式，输出精度较低
  - 5/10 物种 abstract_traits 内容较少，建议补充 '繁殖力', '攻击性' 等特征
```

### 提升向量质量

为获得最佳向量质量，建议 **abstract_traits** 包含以下特征：

| 特征名 | 影响 | 推荐范围 |
|--------|------|---------|
| 繁殖力 | 繁殖策略推断 | 1-10 |
| 攻击性 | 捕食策略推断 | 1-10 |
| 防御性 | 防御策略推断 | 1-10 |
| 运动能力 | 活动模式推断 | 1-10 |
| 社会性 | 社会行为推断 | 1-10 |

其他建议填充的字段：

- **Species.populations**: 种群分布列表（影响地块匹配）
- **Species.prey_species**: 猎物列表（影响食物网构建）

### Species 模型可用字段

```python
species.lineage_code      # ✅ 唯一标识
species.trophic_level     # ✅ 营养级 (1-5)
species.reproduction_r    # ✅ 繁殖率
species.abstract_traits   # ✅ {"攻击性": 5, "防御性": 7, ...}
species.prey_species      # ⚠️ 可能为空
species.populations       # ⚠️ 可能为空
```

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Router                               │
│  /embedding/behavior/* | /food-web/* | /tiles/* | /evolution/*  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              EmbeddingPluginsStage (order: 166)                 │
│  在 embedding_hooks 之后执行，调用 PluginManager                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EmbeddingPluginManager                       │
│  load_plugins() → on_turn_start() → on_turn_end()               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────┬────────────┬────────────┬────────────┬────────────┐
│ Behavior   │ Food Web   │ Tile/Biome │ Evolution  │ Ancestry   │
│ Strategy   │ Embedding  │ Embedding  │ Space      │ Embedding  │
│ ✅ MVP     │ ✅ MVP     │ ✅ MVP     │ ✅ MVP     │ ✅ MVP     │
└────────────┴────────────┴────────────┴────────────┴────────────┘
          ↘         ↓         ↓         ↓         ↙
┌─────────────────────────────────────────────────────────────────┐
│                 PromptOptimizerPlugin ✅                        │
│  上下文精简 | 相关事件筛选 | Token 估算                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      EmbeddingService                           │
│  embed() | search() | _vector_stores.get_store()                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  MultiVectorStore (Faiss)                       │
│  behavior | food_web | tile_biome | evolution | ancestry        │
└─────────────────────────────────────────────────────────────────┘
```

## 使用示例

### 加载和使用插件

```python
from app.services.embedding_plugins import (
    EmbeddingPluginManager, 
    PluginRegistry,
    load_all_plugins
)

# 1. 加载所有内置插件
load_all_plugins()

# 2. 创建管理器
manager = EmbeddingPluginManager(embedding_service)
manager.load_plugins()  # 加载所有启用的插件

# 3. 在回合中使用
manager.on_turn_start(ctx)
# ... 模拟逻辑 ...
manager.on_turn_end(ctx)  # 触发索引更新
```

### 行为策略分析

```python
# 获取插件实例
behavior = manager.get_plugin("behavior_strategy")

# 推断物种行为
profile = behavior.infer_behavior_profile(species)
print(profile.to_text())
# 捕食策略: 群体协作捕食
# 防御策略: 结群防御
# 繁殖策略: K策略-低繁殖高投资
# ...

# 查找行为相似物种
similar = behavior.find_similar_species(species, top_k=5)

# 检测行为冲突
conflicts = behavior.find_behavior_conflicts(species_a, species_b)
```

### 生态网络分析

```python
food_web = manager.get_plugin("food_web")

# 识别关键物种
keystones = food_web.find_keystone_species(top_k=5)
# [{"lineage_code": "A1", "keystone_score": 0.85, "degree": 12}, ...]

# 计算稳定性
stability = food_web.calculate_ecosystem_stability()
# {"connectance": 0.12, "average_degree": 4.5, "species_count": 50}

# 为灭绝物种找补位
candidates = food_web.find_replacement_candidates("EXTINCT_CODE")
```

## API 端点

### 插件状态

| 端点 | 方法 | 描述 |
|------|------|------|
| `/embedding/plugins/status` | GET | 获取所有插件状态 |

### 行为策略

| 端点 | 方法 | 描述 |
|------|------|------|
| `/embedding/behavior/profile/{code}` | GET | 获取物种行为档案 |
| `/embedding/behavior/similar/{code}` | GET | 查找行为相似物种 |
| `/embedding/behavior/conflicts` | POST | 检测行为冲突 |
| `/embedding/behavior/summary` | GET | 行为分布摘要 |

### 食物网

| 端点 | 方法 | 描述 |
|------|------|------|
| `/embedding/food-web/keystone` | GET | 关键物种 |
| `/embedding/food-web/stability` | GET | 生态稳定性 |
| `/embedding/food-web/replacement` | POST | 补位候选 |
| `/embedding/food-web/summary` | GET | 网络摘要 |

### 地块

| 端点 | 方法 | 描述 |
|------|------|------|
| `/embedding/tiles/hotspots` | GET | 生态热点 |
| `/embedding/tiles/species-match` | POST | 物种地块匹配 |
| `/embedding/tiles/summary` | GET | 地块摘要 |

### 演化空间

| 端点 | 方法 | 描述 |
|------|------|------|
| `/embedding/evolution/trends` | GET | 演化趋势 |
| `/embedding/evolution/convergent` | GET | 收敛演化 |
| `/embedding/evolution/trajectory/{code}` | GET | 演化轨迹预测 |
| `/embedding/evolution/summary` | GET | 演化摘要 |

### 血统

| 端点 | 方法 | 描述 |
|------|------|------|
| `/embedding/ancestry/{code}` | GET | 血统信息 |
| `/embedding/ancestry/inertia/{code}/{trait}` | GET | 遗传惯性 |
| `/embedding/ancestry/speciation/{code}` | GET | 分化评估 |
| `/embedding/ancestry/divergence` | POST | 分化程度 |
| `/embedding/ancestry/summary` | GET | 血统摘要 |

## 相关文档

- [完整设计文档](../../../../EMBEDDING_EXTENSION_DESIGN.md) - 详细设计规格
- [AI 路由](../analytics-ai/ai-routing.md) - ModelRouter 配置
- [生态智能体](../analytics-ai/ecological-intelligence.md) - EcologicalIntelligence 集成

维护人：Data/AI 小组
