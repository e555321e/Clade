# API 接口指南（2025-11 更新）
面向需要与 Clade 后端交互的前后端工程师。API 前缀统一为 `/api/*`，管理接口在 `/api/admin/*`，健康探活为根路径 `/health`。

> **Schema 位置**：请求/响应模型定义在 `backend/app/schemas/requests.py` 与 `backend/app/schemas/responses.py`。修改后请同步前端的 `frontend/src/services/api.types.ts`。

## 0. 全局约定
- 返回格式：除 `DELETE` 外均返回 JSON；错误时优先查看 `detail` 字段。
- 认证：当前未启用，公网部署请在 API Gateway 层加鉴权。
- 事件流：`GET /api/events/stream` 为 SSE，推送队列、能量、神迹等实时事件。

## 1. 模拟核心（Simulation）
- `POST /api/turns/run`：执行 1~100 回合，Body 为 `TurnCommand { rounds, pressures?, auto_reports? }`，返回 `TurnReport[]`。
- 行动队列：
  - `GET /api/queue` 返回 `ActionQueueStatus`（含预览）。
  - `POST /api/queue/add` 追加批次 `QueueRequest { rounds, pressures[] }`。
  - `POST /api/queue/clear` 清空队列。
- 历史与导出：`GET /api/history?limit=10`，`GET /api/exports`。
- 游戏状态：`GET /api/game/state` 返回当前回合计数、排队信息和最近报告指针。

## 2. 压力与模板
- `GET /api/pressures/templates`：静态 Pressure 模板。
- `POST /api/config/test-api`：第三方模型连通性测试（chat/embedding）。
- `POST /api/config/fetch-models`：从 Provider 拉取模型列表（OpenAI/Claude/Gemini 兼容）。

## 3. 物种系统（Species）
- 基础：
  - `GET /api/species/list` → `SpeciesList`（含推断的 `ecological_role`）。
  - `GET /api/species/{lineage_code}` → `SpeciesDetail`。
  - `POST /api/species/edit` → `SpeciesDetail`，支持 trait/abstract 覆盖与 `open_new_lineage`。
  - `POST /api/species/generate` / `POST /api/species/generate/advanced`：AI 生成新物种，返回 `{ success, species, energy_spent?... }`。
  - `GET /api/lineage` → `LineageTree`。
  - `GET /api/species/{code1}/can_hybridize/{code2}`：杂交可行性检测。
  - `GET /api/genus/{code}/relationships`：属级关系与杂交配对。
- Watchlist：`GET/POST /api/watchlist`。

## 4. 地图与环境（Environment）
- `GET /api/map`：返回 `MapOverview`（地块/栖息地/河流/全球气候），支持 `limit_tiles`、`limit_habitats`、`view_mode`、`species_code`。
- UI/模型配置：`GET/POST /api/config/ui` 读取/写入 `UIConfig`，会同时配置 `ModelRouter` 与 `EmbeddingService`。

## 5. 存档与导出（Saves & Ops）
- `GET /api/saves/list`
- `POST /api/saves/create`：`CreateSaveRequest { save_name, scenario, species_prompts?, map_seed? }`，自动初始化世界。
- `POST /api/saves/save`：序列化当前世界。
- `POST /api/saves/load`：加载存档并重建状态。
- `DELETE /api/saves/{save_name}`：删除存档目录。

## 6. 分析、生态与干预
- 生态健康：`GET /api/ecosystem/health` → `EcosystemHealthResponse`（Shannon/Simpson/基因多样性/崩溃信号）。
- 食物网：`GET /api/ecosystem/food-web`（完整网络），`/analysis`（得分与缺口），`/repair`（自动填补），`/ {lineage_code}`（单物种链路），`/api/ecosystem/extinction-impact/{lineage_code}`（灭绝影响评估）。
- 干预：
  - `POST /api/intervention/protect` / `/suppress`：保护/压制指定物种。
  - `POST /api/intervention/cancel/{lineage_code}`：取消干预。
  - `POST /api/intervention/introduce`：AI 生成并引入新物种。
  - `POST /api/intervention/symbiosis`：指定共生/寄生关系。
  - `GET /api/intervention/status`：当前所有干预。
- 灾变/能量限制：以上操作均会校验 `DivineEnergyService` 的能量余额。

## 7. 杂交（Hybridization）
- `GET /api/hybridization/candidates`：可杂交物种对。
- `POST /api/hybridization/execute`：常规杂交并生成新物种（消耗能量）。
- `GET /api/hybridization/preview`：常规杂交预览。
- `GET /api/hybridization/force/preview` & `POST /api/hybridization/force/execute`：强制杂交（高成本，允许跨营养级）。

## 8. AI/Embedding 分析
- 生态位：`POST /api/niche/compare` → `NicheCompareResult`（需要真实 Embedding）。
- 嵌入扩展（独立路由 `backend/app/api/embedding_routes.py`，前缀 `/api/embedding`）：
  - `POST /taxonomy/build`，`GET /taxonomy/species/{code}`：自动分类树。
  - `GET /evolution/pressures`，`POST /evolution/predict`：演化预测。
  - `POST /search` / `GET /search/quick`：多模搜索。
  - `POST /qa`：问答。
  - `POST /explain/species`，`POST /compare/species`。
  - `POST /hints`：根据嵌入给出提示。
  - `GET /stats`：Embedding 统计。
  - `GET /narrative/turn/{n}`，`/narrative/eras`，`/narrative/species/{code}/biography`：叙事访问。

### 8.1 生态智能体（Ecological Intelligence）
新架构将 AI 评估统一到 `EcologicalIntelligenceStage`，核心组件：
- **EcologicalIntelligence**：物种评分（risk/impact/potential）与分档（A/B/C）
- **LLMOrchestrator**：并行调用 A/B 档 LLM，解析 `BiologicalAssessment`
- **ModifierApplicator**：统一数值修正入口，业务 Stage 通过 `ctx.modifier_applicator.apply(code, base, "mortality")` 获取修正值
- **IntelligenceMonitor**：监控与降级策略

详见 `docs/api-guides/modules/analytics-ai/ecological-intelligence.md`。

## 9. 能量、神职与成就
- 能量系统（DivineEnergy）：`GET /api/energy`、`/costs`、`/history`、`POST /energy/calculate`、`/toggle`、`/set`。
- 神职与信仰：
  - 进阶：`GET /api/divine/status`、`/paths`，`POST /divine/path/choose`。
  - 技能：`GET /api/divine/skills`，`POST /divine/skill/use`。
  - 信仰：`GET /api/divine/faith`，`POST /divine/faith/add`、`/bless`、`/sanctify`。
  - 神迹：`GET /api/divine/miracles`，`POST /divine/miracle/charge`、`/cancel`、`/execute`。
  - 预言下注：`GET /api/divine/wagers`，`POST /divine/wager/place`、`/check`。
- 成就与提示：`GET /api/achievements`、`/unlocked`、`/pending`、`POST /achievements/exploration/{feature}`、`/reset`；`GET /api/hints`、`POST /api/hints/clear`。

## 10. 系统任务与诊断
- AI 任务控制：`POST /api/tasks/abort`（中断当前 AI 调用）、`POST /api/tasks/skip-ai-step`（跳过卡住的阶段）、`GET /api/tasks/diagnostics`（当前并发与排队）。
- 日志与模型状态：`GET /api/system/logs`，`GET/POST /api/system/ai-diagnostics`。

## 11. 管理接口（Admin）
- `GET /api/admin/health`：数据库、目录、初始物种自检。
- `POST /api/admin/reset`：重置数据库并清理导出/存档目录（可配置保留项）。
- `POST /api/admin/drop-database`：直接删除数据库文件（需重启后端重新建表）。

## 12. 前端集成提示
- Service 封装：业务接口在 `frontend/src/services/api.ts`，Admin 在 `api_admin.ts`。组件层勿直接 `fetch`。
- 类型同步：`api.types.ts` 需跟随 schema 更新；`MapPanel`、`QueuePanel`、`OrganismBlueprint`、`GlobalTrendsPanel`、`FoodWebGraph` 等组件依赖这些类型。
- 错误处理：优先展示 `detail`；LLM 阻塞时可调用 `/tasks/skip-ai-step`。
