# EvoSimulation 生态智能体与 LLM 统一评估系统  
## Ecological Intelligence & LLM Unified Assessment — Design Specification (v2.0)

适用范围：后端核心模拟系统（simulation engine）  
目标用户：引擎维护者、AI 模块开发者、数值系统开发者  
使用方式：  
- 快速落地：阅读第 2 / 3 / 7 / 8 节  
- 调参：阅读第 9 节  
- 扩展架构：阅读第 10 节  
- 测试：阅读第 11 节  


---

# 1. 背景与核心问题

旧系统存在如下问题：

1. LLM 逻辑分散在多个 Stage（status_eval、adaptation、speciation 等）。
2. 大部分逻辑被禁用，LLM 输出无法进入数值系统。
3. Embedding 仅用于 niche 相似度，没有用于预测与筛选。
4. LLM 输出格式不统一，不利于写回 Context。
5. 数值修正散布在多个 Stage，新字段需要修改多处业务逻辑（侵入性高）。
6. 大规模物种调用 LLM 会导致 token 爆炸和延迟高。

解决方案需要同时兼顾性能、可维护性与数值连贯性。

---

# 2. 系统目标

系统目标可概括如下：

1. 在规则引擎基础上，通过 AI（Embedding + LLM）提升物种行为、生存和进化的真实性。
2. 通过 Embedding 实现“全局广覆盖 + 快速预测”，通过 LLM 实现“局部深度评估”。
3. 每回合限定小规模 LLM 调用（5–15 个物种）。
4. LLM 统一输出 BiologicalAssessment 结构体。
5. 所有数值修正集中由 ModifierApplicator 完成，业务 Stage 不再直接读取 assessment。
6. 模块间边界清晰、可扩展、可替换（Embedding/模型服务可替换）。
7. 需支持未来进化方向预测、竞争仲裁、承载力调节等扩展能力。

---

# 3. 整体架构

```

+----------------------+     +---------------------------+
|   Rule Engine        |     |  Embedding Service        |
| (Mortality, K, etc.) |     | (OpenAI/Self-hosted)      |
+----------+-----------+     +--------------+-------------+
|                                   |
v                                   v
+----------------------+     +---------------------------+
| EcologicalIntelligence |<--| Species/Env Vectors       |
| (打分、分档、筛选)       |   | 风险/潜力/适配度评分           |
+-----------+----------+     +---------------------------+
|
v
+----------------------+     +---------------------------+
|   LLM Orchestrator   |---->|   Model Router            |
| (构建 prompt/并行调用) |   | (小模型/大模型)             |
+-----------+----------+     +---------------------------+
|
v
+-----------------------------+
| BiologicalAssessment 输出     |
+-----------+-----------------+
|
v
+-----------------------------+
|   ModifierApplicator        |
|   （统一数值修正入口）       |
+-----------+-----------------+
|
v
+-----------------------------+
| 各业务 Stage 仅调用 apply() |
+-----------------------------+

```

---

# 4. 回合执行流程（整合三方案）

## Step 0：规则阶段运行（既有逻辑）
- 规则死亡率  
- 迁徙与扩散  
- 生态位评估  
- 遗传漂变  
此阶段不调用 LLM，不使用 AI 修正。

## Step 1：生态智能体打分（Embedding + 规则）
为每个物种计算：
- risk：基于死亡率/适配度/趋势  
- impact：基于生物量/营养级/生态网络中心度  
- potential：基于遗传与生态位分化  
- priority：risk/impact/potential 加权和  

按 priority 排序后按以下标准分档：
- A 档（Top 5）：高风险 + 高影响  
- B 档（10–20）：高潜力或处于边缘  
- C 档：不调用 LLM，走规则与 embedding 默认路径

## Step 2：构建 DTO
从 Context 提取必要信息，生成轻量化 DTO：
- SpeciesAssessmentInput：每物种  
- EnvironmentSummary：当前环境摘要  

## Step 3：LLM 并行评估
两个批次：

### 批次 A（Top 5）
- 使用中/大模型  
- 使用丰富上下文  
- 输出 narrative + 全字段  

### 批次 B（10–20）
- 使用小模型  
- 精简 prompt  
- 仅输出数值和标志位字段  

两个批次通过 asyncio 并行执行，延迟取决于耗时最长的一批。

## Step 4：写回 Context
LLM 输出统一解析为：

```

ctx.biological_assessment_results = {
sid: BiologicalAssessment(...)
}

```

## Step 5：业务 Stage 使用 ModifierApplicator 获取修正值
业务层不读取 assessment，仅调用：

```

final = modifier.apply(species_id, base_value, "mortality")

```

---

# 5. 核心模块说明

## 5.1 EcologicalIntelligence
负责：
- 物种/环境向量构建与缓存  
- fitness、competition、potential 计算  
- 打分与分档  
- 输出 LLM 所需 DTO  

不负责：LLM 调用、数值修正。

## 5.2 LLMOrchestrator
负责：
- 构建 prompt  
- 选择模型（大模型用于 A，小模型用于 B）  
- 并行运行 A/B 两批请求  
- 解析 JSON 输出  

不负责：打分、分档、规则集成。

## 5.3 BiologicalAssessment
统一输出结构，包含：
- mortality_modifier  
- r_adjust  
- K_adjust  
- migration_bias  
- climate_bandwidth  
- predation_vulnerability  
- behavior_adjust  
- speciation_signal  
- ecological_fate  
- narrative（仅 A 档）

字段全部在解析时 clamp 到安全范围。

## 5.4 ModifierApplicator（重点）
负责将 BiologicalAssessment 应用到数值系统。

业务 Stage 不再直接读取 assessment，而是：

```

final_value = modifier.apply(
species_id,
base_value,
"mortality" | "reproduction_r" | "carrying_capacity" | "migration"
)

````

新增修正类型时，仅需在 Applicator 中新增一个 `_apply_xxx()` 方法。

---

# 6. LLM 调度策略：A/B 并行批次

1. 按 priority 选出 Top 5 → 批次 A  
2. 再选 10–20 → 批次 B  
3. 两批次并行调用，减少延迟  
4. 两批次使用不同模型与不同 prompt  
5. 全部输出转为统一 BiologicalAssessment  

限制每回合最大调用量与最大 token 数。

---

# 7. 数值修正：ModifierApplicator（统一入口）

示例接口：

```python
class ModifierApplicator:
    def __init__(self, assessment_lookup):
        self.lookup = assessment_lookup

    def apply(self, species_id, base_value, adjustment_type):
        assessment = self.lookup.get(species_id)
        if not assessment:
            return base_value

        if adjustment_type == "mortality":
            return base_value * assessment.mortality_modifier
        elif adjustment_type == "reproduction_r":
            return base_value + assessment.r_adjust
        elif adjustment_type == "carrying_capacity":
            return base_value * (1 + assessment.K_adjust)
        elif adjustment_type == "migration":
            return self._apply_migration(base_value, assessment)

        return base_value
````

所有业务模块只依赖此入口。

---

# 8. 文件结构与目录布局

## MVP（最小可行版本）

```
services/intelligence/
    ecological_intelligence.py
    llm_orchestrator.py
    schemas.py
    modifier_applicator.py
```

## 完整版本（推荐，可渐进升级）

```
services/intelligence/
    protocols.py
    dto.py

    vectors.py
    scoring.py
    partitioner.py

    ecological_intelligence.py
    llm_orchestrator.py
    modifier_applicator.py

    schemas.py
    config.py
```

---

# 9. 参数与调优

建议所有调参集中到 `services/intelligence/config.py`：

| 参数                  | 默认值        | 描述          |
| ------------------- | ---------- | ----------- |
| TOP_A_COUNT         | 5          | A 档数量       |
| TOP_B_COUNT         | 15         | B 档数量       |
| RISK_WEIGHT         | 0.5        | 风险权重        |
| IMPACT_WEIGHT       | 0.3        | 生态影响权重      |
| POTENTIAL_WEIGHT    | 0.2        | 潜力权重        |
| PRIORITY_THRESHOLD  | 0.4        | 进入 LLM 最低权重 |
| MORTALITY_MOD_RANGE | (0.3, 1.8) | 死亡率调节范围     |

全部可由 stage_config.yaml 覆盖。

---

# 10. 扩展架构（向量、评分、分档解耦）

推荐进一步拆分 EcologicalIntelligence：

* VectorService：向量构建与缓存
* ScoringService：risk/impact/potential
* Partitioner：A/B/C 档划分
* DTO：Orchestrator 输入，不依赖 Context
* Protocols：Embedding/ModelRouter 抽象接口

此结构更适合规模增长或多人协作。

---

# 11. 测试策略与降级策略

## 11.1 单元测试

* scoring：risk/impact/potential
* partition：排序、阈值行为
* assessment.parse：容错与 clamp
* modifier.apply：不同 adjustment_type
* dto 构建正确性

## 11.2 集成测试

* 构造 3–5 个物种和环境
* mock LLM 输出
* 跑完整回合
* 验证 population_update / migration 的结果

## 11.3 降级策略

* LLM 超时 → 使用默认 assessment
* JSON 解析失败 → 忽略该物种并记录 warn
* Embedding 不可用 → 使用固定 fitness=0.5
* 每回合强制最大评估数量，防止资源耗尽

---

# 12. 实施路线图

## 阶段 1：MVP（1–2 天）

* 简单版智能体（单文件）
* 单批次或双批次同步 LLM
* 仅 mortality 修正

## 阶段 2：A/B 并行调用（2–3 天）

* 并行调度
* DTO 与 Prompt 拆分
* 完整返回 BiologicalAssessment

## 阶段 3：扩展修正类型（2 天）

* r_adjust
* K_adjust
* migration_bias

## 阶段 4：完整模块拆分（3–4 天）

* vectors/scoring/partitioner 拆分
* protocols/dto 完整化

## 阶段 5：观测与调参（持续）

* 记录每回合统计
* 调整权重与阈值
* 加强鲁棒性与降级策略

---

**本设计文档可直接作为团队开发规范、项目内技术设计说明或模块级开发蓝图使用。**

```

---

