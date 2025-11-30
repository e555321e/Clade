# Analytics & AI 模块指南

聚焦生态位分析、遗传距离计算、AI 路由配置、生态智能体与诊断工具。

## 职责

- 暴露 `/niche/compare` 供物种生态位对比/竞争分析。
- 提供 `/config/test-api` 用于验证 LLM / Embedding 服务连通性。
- 维护 `ModelRouter`、`EmbeddingService`、`NicheAnalyzer` 等跨模块能力。
- **生态智能体**：统一 AI 评估系统，物种分档、LLM 评估、数值修正应用。

## 依赖

- `backend/app/services/niche.py`, `embedding.py`, `genetic_distance.py`
- `backend/app/services/intelligence/` — 生态智能体模块
- `backend/app/ai/model_router.py`
- `frontend/src/services/api.ts`：`compareNiche`, `testApiConnection`

## 接口

| Endpoint | 描述 | Schema | 前端 |
| --- | --- | --- | --- |
| `POST /niche/compare` | 生态位向量对比、竞争度计算 | `NicheCompareRequest` → `NicheCompareResult` | `compareNiche` |
| `POST /config/test-api` | 测试 chat / embedding API | `{ type, base_url, api_key, model }` → `{ success, message, details }` | `testApiConnection`（Settings Drawer） |

## 子文档

| 文档 | 内容 |
| --- | --- |
| [niche-compare.md](niche-compare.md) | `/niche/compare` 细节 |
| [genetic-distance.md](genetic-distance.md) | 遗传距离算法、混种依赖 |
| [ai-routing.md](ai-routing.md) | ModelRouter、UI 配置、诊断端点 |
| [ecological-intelligence.md](ecological-intelligence.md) | **生态智能体**：分档策略、BiologicalAssessment、ModifierApplicator |

## 生态智能体概览

新架构将 AI 评估统一到 `EcologicalIntelligenceStage`：

```
物种列表 → EcologicalIntelligence.partition_species()
         → A/B/C 分档
         → LLMOrchestrator.execute() (并行)
         → BiologicalAssessment
         → ModifierApplicator
         → 供业务 Stage 使用
```

核心组件：
- **EcologicalIntelligence**：评分（risk/impact/potential）与分档
- **LLMOrchestrator**：A/B 批次并行 LLM 调用
- **ModifierApplicator**：`apply(code, base, "mortality")` 统一入口
- **IntelligenceMonitor**：监控与降级策略

详见 [ecological-intelligence.md](ecological-intelligence.md)。

维护人：Data/AI 小组。
