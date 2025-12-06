# 基因多样性系统设计文档

> 基于 Embedding 的物种级基因库方案

## 一、设计目标

### 1.1 核心需求

1. **前期加速**：太古宙/元古宙快速积累基因多样性
2. **中后期活跃**：保持像真实地球一样多样化的物种演化
3. **自然瓶颈**：大灾变通过种群动态自然筛选基因，而非条件触发
4. **高效存储**：不为每个物种存储大量数据
5. **利用现有系统**：充分复用 Embedding 模块

### 1.2 核心理念

> **基因库 = 物种在 Embedding 空间中的"可演化范围"**

- **已激活基因** = 当前 `ecological_vector` 的位置
- **休眠基因** = 向量周围的"可达区域"
- **基因多样性** = 可达区域的半径大小

---

## 二、数据结构设计

### 2.1 Species 模型新增字段

| 字段 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `gene_diversity_radius` | float | 0.35 | 基因可达半径（Embedding 空间距离） |
| `explored_directions` | list[int] | [] | 已探索的演化方向索引（稀疏记录） |
| `gene_stability` | float | 0.5 | 基因稳定性（影响丢失概率） |

**存储量**：每物种约 50-100 字节

### 2.2 与现有字段的关系

| 现有字段 | 新方案对应 | 处理方式 |
|---------|-----------|---------|
| `ecological_vector` | 当前基因表达位置 | 保持不变 |
| `hidden_traits.gene_diversity` | `gene_diversity_radius` | 迁移合并 |
| `hidden_traits.evolution_potential` | 保留，与半径独立 | 保持不变 |
| `dormant_genes` | 废弃 | 逐步迁移到新机制 |

---

## 三、核心机制

### 3.1 基因多样性半径

**定义**：物种在 Embedding 空间中可演化的范围

- 半径大 → 演化方向多、适应性强、抗灾能力强
- 半径小 → 演化受限、特化程度高、脆弱

**自然变化规律**：

| 事件 | 半径变化 | 生物学含义 |
|-----|---------|-----------|
| 分化繁殖 | 子代继承父代半径 × 0.85-1.0 | 奠基者效应 |
| 杂交 | 半径增加 20-40% | 基因重组 |
| 高死亡率存活 | 半径减少 5-15% | 瓶颈效应 |
| 低压力稳定期 | 半径增加 1-3%/回合 | 突变积累 |

### 3.2 休眠基因激活

**机制**：向量移动

1. 计算压力的 Embedding 方向
2. 检查该方向是否在物种的"可达半径"内
3. 如果在可达范围内，物种可以向该方向演化（激活休眠基因）
4. 移动后消耗少量半径（可达范围略微缩小）

**判断公式**：
```
可激活 = distance(current_vector, target_direction) < gene_diversity_radius
```

### 3.3 新基因发现

**触发条件**：
- 高环境压力下存活
- 杂交事件
- 特定里程碑达成

**效果**：
- 增加 `gene_diversity_radius`
- 记录新探索的方向

### 3.4 自然瓶颈效应

**核心公式**：
```
每回合半径变化 = 基础增长率 - 瓶颈衰减

瓶颈衰减 = k / sqrt(population) × 压力系数
```

**效果**（连续函数，非阈值判断）：

| 种群规模 | 每回合半径净变化 |
|---------|-----------------|
| >100,000 | +1.5% |
| 10,000-100,000 | +0.5% ~ +1% |
| 1,000-10,000 | -0.5% ~ 0% |
| <1,000 | -2% ~ -1% |

---

## 四、数值参数

### 4.1 时代参数

| 参数 | 太古宙（<50回合） | 元古宙（50-150回合） | 古生代及以后 |
|-----|------------------|---------------------|-------------|
| 初始半径 | 0.5 | 0.4 | 0.35 |
| 半径增长率/回合 | +3% | +2% | +1.5% |
| 分化时半径继承 | 95% | 90% | 85% |
| 突变发现概率 | 15% | 10% | 8% |

### 4.2 激活与发现参数

| 参数 | 值 | 说明 |
|-----|---|------|
| 激活概率/回合 | 5-10% | 每回合有概率激活一个休眠基因 |
| 压力匹配加成 | ×2 | 休眠基因方向与压力匹配时 |
| 新器官发现概率 | 3-5%/分化 | 分化时发现新器官的概率 |
| 杂交多样性加成 | +30% 半径 | 杂交显著增加基因多样性 |
| 激活后半径消耗 | -2% | 每次激活略微缩小可达范围 |

### 4.3 瓶颈效应参数

| 参数 | 值 | 说明 |
|-----|---|------|
| 瓶颈系数 k | 50 | `衰减 = k / sqrt(pop)` |
| 最大衰减率 | 5%/回合 | 防止半径瞬间归零 |
| 最小半径 | 0.05 | 保底演化能力 |
| 恢复阈值 | 种群 > 50,000 | 超过此值开始正向增长 |

---

## 五、Embedding 集成

### 5.1 利用现有服务

| 现有模块 | 用途 |
|---------|------|
| `EmbeddingService.get_embedding()` | 获取压力类型的向量方向 |
| `EmbeddingService.similarity()` | 判断休眠基因是否与压力匹配 |
| `EvolutionPredictor` | 预测可能的演化方向 |
| `PlantEvolutionPredictor` | 植物演化方向预测 |

### 5.2 新增计算

1. **压力方向计算**：`pressure_direction = embed(pressure_type)`
2. **可达性判断**：`distance(current_vector, target) < gene_diversity_radius`
3. **演化移动**：`new_vector = current + step × direction`

### 5.3 张量批量计算

利用现有张量模块进行批量计算：
- 所有物种的 `ecological_vector` 组成张量
- 批量计算距离和可达性掩码

**已实现的批量优化方法**（`GeneDiversityService`）：

```python
# 批量更新所有物种的基因多样性半径（一次回合）
results = gene_diversity_service.batch_update_per_turn(
    species_list=all_species,
    population_map={"A1": 10000, "B1": 5000, ...},
    death_rate_map={"A1": 0.05, "B1": 0.12, ...},
    turn_index=current_turn
)
# -> [{"lineage_code": "A1", "name": "...", "old": 0.35, "new": 0.36, "delta": 0.01, "reason": "自然增长"}, ...]

# 批量判断多个物种向量是否在各自可达半径内
reachable_flags = gene_diversity_service.batch_is_reachable(
    species_vectors=[sp.ecological_vector for sp in species_list],
    target_vec=pressure_vector,
    radii=[sp.gene_diversity_radius for sp in species_list]
)
# -> [True, False, True, ...]
```

**性能优势**：
- `batch_update_per_turn`: 使用 numpy 向量化计算，避免 Python 循环开销
- `batch_is_reachable`: 矩阵乘法一次性计算所有余弦相似度，减少重复计算

---

## 六、Prompt 调整

### 6.1 分化 Prompt 新增内容

```
=== 基因多样性状态 ===
当前演化范围：{diversity_radius:.2f}（0-1，越大演化方向越多）
可达的演化方向：{reachable_directions}
与当前压力匹配的潜在适应：{pressure_matched_adaptations}

=== 演化建议 ===
- 基因多样性高（>0.4）：可尝试较大幅度的适应性变化
- 基因多样性低（<0.2）：建议保守演化，避免过度特化
- 当前最优演化方向：{suggested_direction}（基于 Embedding 预测）
```

### 6.2 基因库规则说明

```
=== 基因库规则 ===
1. 优先利用已有潜力：物种当前演化范围内已有潜在适应方向
2. 激活 vs 创造：可达范围内的变化是"激活休眠基因"，超出范围才是"新突变"
3. 多样性守恒：每次大幅演化会略微缩小未来的演化范围
4. 压力驱动发现：高压力环境可能扩展演化范围（发现新基因）
```

### 6.3 回合报告展示

```
【基因多样性变动】
- 演化范围：{old_radius:.2f} → {new_radius:.2f}
- 变化原因：{change_reason}
- 激活的潜在适应：{activated_adaptations}
```

---

## 七、迁移策略

### 7.1 兼容性处理

| 现有机制 | 处理方式 |
|---------|---------|
| `dormant_genes` 字段 | 保留但不再新增，逐步废弃 |
| `hidden_traits.gene_diversity` | 迁移到 `gene_diversity_radius` |
| 属级基因库 (`GeneLibraryService`) | 废弃，改为物种级 |
| `GeneActivationService` | 重构为基于 Embedding 距离判断 |

### 7.2 数据迁移

对现有物种：
1. 根据 `hidden_traits.gene_diversity` 计算初始 `gene_diversity_radius`
2. 根据 `dormant_genes` 数量估算 `explored_directions`
3. 新分化物种直接使用新机制

---

## 八、TODO List

### Phase 1: 数据结构（优先级：高）✅ 已完成

- [x] 在 `Species` 模型中添加 `gene_diversity_radius` 字段
- [x] 在 `Species` 模型中添加 `explored_directions` 字段
- [x] 在 `Species` 模型中添加 `gene_stability` 字段
- [x] 旧存档自动迁移（通过 `ensure_initialized` 实现）
- [x] 为现有物种生成初始基因多样性数据

### Phase 2: 核心机制（优先级：高）✅ 已完成

- [x] 创建 `GeneDiversityService` 服务类
- [x] 实现半径自然增长逻辑（每回合）
- [x] 实现瓶颈衰减公式（基于种群规模）
- [x] 实现分化时的半径继承逻辑
- [x] 实现杂交时的半径增加逻辑

### Phase 3: Embedding 集成（优先级：高）✅ 已完成

- [x] 实现基于 Embedding 的可达性判断
- [x] 实现压力方向与基因库匹配计算
- [x] 在 `GeneActivationService` 中集成 Embedding 距离判断
- [x] 添加张量批量计算优化（`batch_update_per_turn`、`batch_is_reachable`）

### Phase 4: 激活机制（优先级：中）✅ 已完成

- [x] 重构 `GeneActivationService` 为基于 Embedding 距离
- [x] 实现休眠基因激活时的半径消耗
- [x] 实现新基因发现的半径扩展
- [x] 添加时代相关的参数调整
- [x] 使用配置参数控制激活概率和压力匹配加成

### Phase 5: Prompt 调整（优先级：中）✅ 已完成

- [x] 修改分化 Prompt 添加基因多样性信息（`gene_diversity_radius`、`gene_stability`、`explored_directions`）
- [x] 添加演化建议基于基因多样性半径
- [x] 修改回合报告展示基因多样性变动（`gene_diversity_events` 支持）
- [x] AI 引导使用休眠基因优先于创造新特征（半径>0.4 允许新器官，<0.2 禁止）

### Phase 6: 迁移与清理（优先级：低）✅ 已完成

- [x] 迁移 `hidden_traits.gene_diversity` 到新字段（`ensure_initialized` 自动处理）
- [x] 标记 `dormant_genes` 为废弃（Species 模型添加 DEPRECATED 注释）
- [x] 标记 `stress_exposure` 为废弃（改用 Embedding 距离计算压力匹配）
- [x] 重构 `GeneLibraryService` 为废弃状态（惰性加载+废弃警告，保留兼容）
- [x] `GeneActivationService` 和 `SpeciationService` 改为惰性加载 `GeneLibraryService`
- [ ] 更新相关测试用例（待后续完善）
- [ ] 更新 API 文档（待后续完善）

### Phase 7: 前端设置与展示 ✅ 已完成

- [x] 在 `UIConfig` 中添加 `GeneDiversityConfig` 配置
- [x] 创建基因多样性设置面板（`GeneDiversitySection`）
- [x] 所有参数可通过前端设置界面调整
- [x] 在物种详情中展示基因多样性半径
- [x] 添加基因多样性的可视化进度条指示器（带颜色编码）
- [x] 在回合报告中展示基因库变动

---

## 九、风险与注意事项

### 9.1 性能考虑

- Embedding 计算可能增加 API 调用，需评估成本
- 张量批量计算应尽量复用现有计算结果
- 避免每回合为所有物种重复计算 Embedding

### 9.2 平衡性考虑

- 初始半径值需要测试调整，避免早期过于强大或过于受限
- 瓶颈系数 k 需要根据实际种群规模范围调整
- 激活概率需要平衡"演化活跃度"和"特征稳定性"

### 9.3 向后兼容

- 旧存档加载时需要为缺失字段生成默认值
- `dormant_genes` 仍需保留读取能力（一段时间内）

---

## 十、预期效果

| 游戏阶段 | 预期表现 |
|---------|---------|
| 太古宙（0-50回合） | 基因多样性快速积累，物种简单但潜力大 |
| 元古宙（50-150回合） | 多样性继续增长，开始出现分化 |
| 古生代早期（150-250回合） | 多样性稳定，演化方向多样化 |
| 中后期 | 保持活跃演化，大灭绝自然筛选基因库 |
| 大灭绝后 | 幸存者基因多样性下降，但可逐渐恢复 |

---

*文档版本：v2.1*
*创建日期：2024-12*
*最后更新：2024-12-06*
*状态：**开发完成** - 核心功能已实现，张量优化和清理工作已完成，可投入使用*

