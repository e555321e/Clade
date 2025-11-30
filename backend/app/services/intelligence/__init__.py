"""
Ecological Intelligence Module - 生态智能体模块

该模块实现了 EvoSimulation 的统一 AI 评估系统，包括：
1. EcologicalIntelligence - 物种打分、分档、筛选
2. LLMOrchestrator - LLM 调用编排（A/B 批次并行）
3. BiologicalAssessment - 统一输出结构
4. ModifierApplicator - 数值修正统一入口

设计原则：
- Embedding 实现"全局广覆盖 + 快速预测"
- LLM 实现"局部深度评估"
- 每回合限定小规模 LLM 调用（5-15 个物种）
- 所有数值修正集中由 ModifierApplicator 完成
"""

from .schemas import (
    BiologicalAssessment,
    SpeciesAssessmentInput,
    EnvironmentSummary,
    SpeciesPriority,
    AssessmentTier,
)
from .ecological_intelligence import EcologicalIntelligence, PartitionResult
from .llm_orchestrator import LLMOrchestrator, OrchestratorResult
from .modifier_applicator import ModifierApplicator, AdjustmentType
from .config import IntelligenceConfig
from .stage import EcologicalIntelligenceStage
from .monitoring import (
    IntelligenceMonitor,
    HealthStatus,
    TurnMetrics,
    StageMetrics,
    get_monitor,
)

__all__ = [
    # Schemas
    "BiologicalAssessment",
    "SpeciesAssessmentInput",
    "EnvironmentSummary",
    "SpeciesPriority",
    "AssessmentTier",
    # Core components
    "EcologicalIntelligence",
    "PartitionResult",
    "LLMOrchestrator",
    "OrchestratorResult",
    "ModifierApplicator",
    "AdjustmentType",
    # Config
    "IntelligenceConfig",
    # Stage
    "EcologicalIntelligenceStage",
    # Monitoring
    "IntelligenceMonitor",
    "HealthStatus",
    "TurnMetrics",
    "StageMetrics",
    "get_monitor",
]

