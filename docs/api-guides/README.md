# API 指南索引（backend）
本目录为后端 API 的索引与术语说明，配合根目录的 `API_GUIDE.md` 一起使用。所有业务接口前缀为 `/api/*`，Embedding 扩展前缀为 `/api/embedding/*`。

## 快速导航
- **总览**：根目录 `API_GUIDE.md`（端点列表与分组说明）
- **术语表**：`glossary.md`
- **规范**：`conventions.md`
- **模块档案**（按领域）
  - `modules/simulation/`：回合执行、压力编排、行动队列、历史与导出
  - `modules/species/`：物种列表/详情/编辑/生成、谱系树、杂交
  - `modules/environment/`：地图概览、压力模板、UI 配置
  - `modules/analytics-ai/`：生态位对比、AI/Embedding 配置与自检
  - `modules/embedding-extensions/`：Embedding 扩展插件（行为策略、生态网络、区域向量、演化空间、血统压缩）
  - `modules/saves-ops/`：存档、导出、健康检查、重置
  - `modules/hybridization/`（新增占位，可在此补充强制杂交/预览细节）
  - `modules/energy-divine/`（新增占位，记录能量、神迹、信仰、预言下注）
  - `modules/ecosystem/`（新增占位，记录食物网、生态健康、干预操作）
  - `modules/frontend-integration/`：前端调用示例与类型同步

> 目前部分模块子文件仍待补充（hybridization / energy-divine / ecosystem），请在迭代中补齐。其他旧文档若与代码不符，以最新 `API_GUIDE.md` 和 `backend/app/api/routes.py` 为准。

## 交互基线
- **事件流**：`GET /api/events/stream` 以 SSE 推送队列消费、能量扣除、神迹等实时事件。
- **能量限制**：`DivineEnergyService` 会为压力、物种生成、杂交、干预等操作计费；能量不足时返回 400/422 并包含提示。
- **Schema 约定**：后端使用 Pydantic/SQLModel，前端类型位于 `frontend/src/services/api.types.ts`。

## 术语速查
- **Turn / Round**：一次回合模拟（约 50 万年），可批量执行。
- **Pressure**：环境或事件压力，驱动地图/物种变化。
- **Tiering**：物种分级，决定是否触发昂贵的 AI 叙事。
- **Watchlist**：被关注的物种，报告会优先展示。
- **Divine Energy**：行动消耗的“神力”资源，可通过技能/信仰恢复。
