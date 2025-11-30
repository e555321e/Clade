"""
Ecological Intelligence Schemas - 生态智能体数据结构

定义了系统中使用的所有数据传输对象（DTO）和输出结构。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AssessmentTier(Enum):
    """评估等级
    
    用于将物种分档，决定使用的模型和 prompt 复杂度。
    """
    A = "A"  # 高优先级：高风险 + 高影响
    B = "B"  # 中优先级：高潜力或处于边缘
    C = "C"  # 低优先级：走规则与 embedding 默认路径


@dataclass
class SpeciesPriority:
    """物种优先级评分
    
    包含各维度的评分和最终优先级。
    """
    species_id: int
    lineage_code: str
    
    # 各维度评分（0-1）
    risk: float = 0.0           # 风险评分（基于死亡率/适配度/趋势）
    impact: float = 0.0         # 生态影响评分（基于生物量/营养级/网络中心度）
    potential: float = 0.0      # 潜力评分（基于遗传与生态位分化）
    
    # 加权和
    priority: float = 0.0
    
    # 分档结果
    tier: AssessmentTier = AssessmentTier.C
    
    # 额外元数据
    population: int = 0
    death_rate: float = 0.0
    trophic_level: float = 1.0


@dataclass
class SpeciesAssessmentInput:
    """物种评估输入 DTO
    
    轻量化的物种信息，用于构建 LLM prompt。
    """
    species_id: int
    lineage_code: str
    common_name: str
    latin_name: str
    
    # 基础状态
    population: int
    death_rate: float
    trophic_level: float
    
    # 生态位信息
    climate_tolerance: Dict[str, float] = field(default_factory=dict)
    diet_type: str = ""
    habitat_types: List[str] = field(default_factory=list)
    
    # 遗传信息
    genetic_diversity: float = 0.5
    active_genes: List[str] = field(default_factory=list)
    
    # 历史趋势
    population_trend: float = 0.0  # 正值=增长，负值=下降
    recent_events: List[str] = field(default_factory=list)
    
    # 评分元数据
    tier: AssessmentTier = AssessmentTier.C
    priority_score: float = 0.0


@dataclass
class EnvironmentSummary:
    """环境摘要 DTO
    
    当前回合的环境状态概览，用于 LLM 上下文。
    """
    turn_index: int
    
    # 气候状态
    global_temperature: float = 15.0
    temperature_change: float = 0.0
    sea_level: float = 0.0
    sea_level_change: float = 0.0
    
    # 环境压力
    active_pressures: Dict[str, float] = field(default_factory=dict)
    major_events: List[str] = field(default_factory=list)
    
    # 生态系统状态
    total_species_count: int = 0
    total_biomass: float = 0.0
    ecosystem_health: float = 1.0
    
    # 地质事件
    tectonic_events: List[str] = field(default_factory=list)


@dataclass
class BiologicalAssessment:
    """生物学评估结果 - 统一输出结构
    
    LLM 输出解析后的标准化结构，包含所有可能的修正字段。
    所有数值字段都有默认值和安全范围限制。
    """
    species_id: int
    lineage_code: str
    
    # === 核心修正因子 ===
    mortality_modifier: float = 1.0      # 死亡率乘数 [0.3, 1.8]
    r_adjust: float = 0.0                # 繁殖率加法调整 [-0.3, 0.3]
    k_adjust: float = 0.0                # 承载力比例调整 [-0.5, 0.5]
    
    # === 行为修正 ===
    migration_bias: float = 0.0          # 迁徙倾向 [-1, 1]（负=倾向留守，正=倾向迁徙）
    behavior_adjust: Dict[str, float] = field(default_factory=dict)  # 行为调整
    
    # === 生态位修正 ===
    climate_bandwidth: float = 0.0       # 气候耐受带宽调整
    predation_vulnerability: float = 0.0 # 捕食脆弱性调整
    
    # === 演化信号 ===
    speciation_signal: float = 0.0       # 分化信号强度 [0, 1]
    ecological_fate: str = "stable"      # 生态命运预测
    evolution_direction: List[str] = field(default_factory=list)  # 演化方向提示
    
    # === 叙事（仅 A 档） ===
    narrative: str = ""
    headline: str = ""
    mood: str = "neutral"
    
    # === 元数据 ===
    tier: AssessmentTier = AssessmentTier.C
    confidence: float = 0.5              # 评估置信度 [0, 1]
    reasoning: str = ""                  # 推理过程（调试用）
    
    @classmethod
    def from_llm_output(
        cls,
        species_id: int,
        lineage_code: str,
        raw_output: Dict[str, Any],
        tier: AssessmentTier = AssessmentTier.C,
    ) -> "BiologicalAssessment":
        """从 LLM 原始输出解析并创建实例
        
        自动进行范围限制和类型转换。
        """
        def clamp(value: float, min_val: float, max_val: float) -> float:
            try:
                return max(min_val, min(max_val, float(value)))
            except (TypeError, ValueError):
                return (min_val + max_val) / 2
        
        def safe_float(value: Any, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
        
        def safe_str(value: Any, default: str = "") -> str:
            if value is None:
                return default
            return str(value)
        
        def safe_list(value: Any) -> List[str]:
            if isinstance(value, list):
                return [str(v) for v in value]
            return []
        
        # 解析并限制范围
        return cls(
            species_id=species_id,
            lineage_code=lineage_code,
            mortality_modifier=clamp(
                raw_output.get("mortality_modifier", 1.0), 0.3, 1.8
            ),
            r_adjust=clamp(
                raw_output.get("r_adjust", 0.0), -0.3, 0.3
            ),
            k_adjust=clamp(
                raw_output.get("k_adjust", raw_output.get("K_adjust", 0.0)), -0.5, 0.5
            ),
            migration_bias=clamp(
                raw_output.get("migration_bias", 0.0), -1.0, 1.0
            ),
            behavior_adjust=raw_output.get("behavior_adjust", {}),
            climate_bandwidth=safe_float(raw_output.get("climate_bandwidth", 0.0)),
            predation_vulnerability=clamp(
                raw_output.get("predation_vulnerability", 0.0), -1.0, 1.0
            ),
            speciation_signal=clamp(
                raw_output.get("speciation_signal", 0.0), 0.0, 1.0
            ),
            ecological_fate=safe_str(
                raw_output.get("ecological_fate", "stable")
            ),
            evolution_direction=safe_list(
                raw_output.get("evolution_direction", [])
            ),
            narrative=safe_str(raw_output.get("narrative", "")),
            headline=safe_str(raw_output.get("headline", "")),
            mood=safe_str(raw_output.get("mood", "neutral")),
            tier=tier,
            confidence=clamp(raw_output.get("confidence", 0.5), 0.0, 1.0),
            reasoning=safe_str(raw_output.get("reasoning", "")),
        )
    
    @classmethod
    def create_default(
        cls,
        species_id: int,
        lineage_code: str,
        tier: AssessmentTier = AssessmentTier.C,
    ) -> "BiologicalAssessment":
        """创建默认评估（用于降级策略）"""
        return cls(
            species_id=species_id,
            lineage_code=lineage_code,
            tier=tier,
            ecological_fate="default_fallback",
            reasoning="使用默认值（LLM 调用失败或被跳过）",
        )


@dataclass
class AssessmentBatch:
    """评估批次
    
    用于组织 A/B 批次的物种列表。
    """
    tier: AssessmentTier
    species_inputs: List[SpeciesAssessmentInput]
    environment: EnvironmentSummary
    
    @property
    def count(self) -> int:
        return len(self.species_inputs)
    
    @property
    def lineage_codes(self) -> List[str]:
        return [s.lineage_code for s in self.species_inputs]

