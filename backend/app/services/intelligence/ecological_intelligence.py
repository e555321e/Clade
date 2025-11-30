"""
Ecological Intelligence - 生态智能体

负责物种评分、分档和 DTO 构建，为 LLM 调用提供输入。
不负责 LLM 调用和数值修正。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from .config import IntelligenceConfig, DEFAULT_CONFIG
from .schemas import (
    AssessmentTier,
    BiologicalAssessment,
    EnvironmentSummary,
    SpeciesAssessmentInput,
    SpeciesPriority,
    AssessmentBatch,
)

if TYPE_CHECKING:
    from ...models.species import Species
    from ..system.embedding import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class PartitionResult:
    """分档结果"""
    tier_a: List[SpeciesPriority]  # 高优先级（Top 5）
    tier_b: List[SpeciesPriority]  # 中优先级（10-20）
    tier_c: List[SpeciesPriority]  # 低优先级（其余）
    
    @property
    def total_count(self) -> int:
        return len(self.tier_a) + len(self.tier_b) + len(self.tier_c)


class EcologicalIntelligence:
    """生态智能体 - 物种评分与分档
    
    核心职责：
    1. 为每个物种计算 risk/impact/potential 评分
    2. 计算加权优先级并分档（A/B/C）
    3. 构建 LLM 输入 DTO
    4. 管理向量缓存（可选）
    
    不负责：
    - LLM 调用
    - 数值修正应用
    """
    
    def __init__(
        self,
        config: IntelligenceConfig | None = None,
        embedding_service: Optional["EmbeddingService"] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        self.embedding_service = embedding_service
        
        # 缓存
        self._fitness_cache: Dict[str, float] = {}
        self._priority_cache: Dict[str, SpeciesPriority] = {}
        
        logger.info(
            f"[EcologicalIntelligence] 初始化完成 "
            f"(A档={self.config.top_a_count}, B档={self.config.top_b_count})"
        )
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._fitness_cache.clear()
        self._priority_cache.clear()
    
    # =========================================================================
    # 评分计算
    # =========================================================================
    
    def calculate_risk(
        self,
        species: "Species",
        death_rate: float,
        niche_metrics: Dict[str, Any] | None = None,
    ) -> float:
        """计算风险评分
        
        基于：
        - 死亡率
        - 种群规模
        - 适配度趋势
        
        Returns:
            风险评分 [0, 1]，越高越危险
        """
        score = 0.0
        
        # 1. 死亡率评分（权重 0.5）
        if death_rate >= self.config.death_rate_critical_threshold:
            death_score = 1.0
        elif death_rate >= self.config.death_rate_warning_threshold:
            # 线性插值
            death_score = (death_rate - self.config.death_rate_warning_threshold) / \
                         (self.config.death_rate_critical_threshold - self.config.death_rate_warning_threshold)
        else:
            death_score = death_rate / self.config.death_rate_warning_threshold * 0.5
        score += death_score * 0.5
        
        # 2. 种群规模评分（权重 0.3）
        population = species.morphology_stats.get("population", 0) or 0
        if population <= 0:
            pop_score = 1.0
        elif population < self.config.population_critical_threshold:
            pop_score = 1.0 - (population / self.config.population_critical_threshold)
        elif population < 1000:
            pop_score = 0.5 * (1.0 - (population - self.config.population_critical_threshold) / 900)
        else:
            pop_score = 0.0
        score += pop_score * 0.3
        
        # 3. 生态位适配度评分（权重 0.2）
        if niche_metrics and species.lineage_code in niche_metrics:
            metrics = niche_metrics[species.lineage_code]
            saturation = getattr(metrics, 'saturation', 0.5)
            # 高饱和度 = 高竞争压力 = 高风险
            saturation_score = saturation
            score += saturation_score * 0.2
        else:
            score += 0.1  # 默认中等风险
        
        return min(1.0, max(0.0, score))
    
    def calculate_impact(
        self,
        species: "Species",
        all_species: List["Species"],
        food_web_analysis: Any | None = None,
    ) -> float:
        """计算生态影响评分
        
        基于：
        - 生物量占比
        - 营养级
        - 食物网中心度
        
        Returns:
            生态影响评分 [0, 1]，越高影响越大
        """
        score = 0.0
        
        # 1. 生物量占比（权重 0.4）
        total_biomass = sum(
            s.morphology_stats.get("population", 0) or 0
            for s in all_species
            if s.status == "alive"
        )
        species_biomass = species.morphology_stats.get("population", 0) or 0
        
        if total_biomass > 0:
            biomass_ratio = species_biomass / total_biomass
            if biomass_ratio >= self.config.biomass_high_impact_threshold:
                biomass_score = 1.0
            else:
                biomass_score = biomass_ratio / self.config.biomass_high_impact_threshold
            score += biomass_score * 0.4
        
        # 2. 营养级（权重 0.3）
        trophic_level = getattr(species, 'trophic_level', 1.0) or 1.0
        # 顶级捕食者和关键中间物种影响更大
        if trophic_level >= 4.0:
            trophic_score = 1.0
        elif trophic_level >= 3.0:
            trophic_score = 0.8
        elif trophic_level >= 2.0:
            trophic_score = 0.5
        else:
            # 初级生产者基础重要
            trophic_score = 0.6
        score += trophic_score * 0.3
        
        # 3. 食物网中心度（权重 0.3）
        if food_web_analysis:
            # 检查是否为瓶颈物种
            bottleneck_species = getattr(food_web_analysis, 'bottleneck_species', [])
            if species.lineage_code in bottleneck_species:
                centrality_score = 1.0
            else:
                # 检查链接数
                total_links = getattr(food_web_analysis, 'total_links', 0)
                if total_links > 0:
                    centrality_score = 0.3
                else:
                    centrality_score = 0.1
            score += centrality_score * 0.3
        else:
            score += 0.2 * 0.3  # 默认中等中心度
        
        return min(1.0, max(0.0, score))
    
    def calculate_potential(
        self,
        species: "Species",
        niche_metrics: Dict[str, Any] | None = None,
    ) -> float:
        """计算潜力评分
        
        基于：
        - 遗传多样性
        - 生态位分化程度
        - 隐藏特征
        
        Returns:
            潜力评分 [0, 1]，越高演化潜力越大
        """
        score = 0.0
        
        # 1. 遗传多样性（权重 0.4）
        hidden_traits = getattr(species, 'hidden_traits', {}) or {}
        genetic_diversity = len(hidden_traits) / 10.0  # 假设最多10个隐藏特征
        score += min(1.0, genetic_diversity) * 0.4
        
        # 2. 生态位分化（权重 0.3）
        if niche_metrics and species.lineage_code in niche_metrics:
            metrics = niche_metrics[species.lineage_code]
            overlap = getattr(metrics, 'overlap', 0.5)
            # 低重叠 = 独特生态位 = 高潜力
            niche_score = 1.0 - overlap
            score += niche_score * 0.3
        else:
            score += 0.3 * 0.3  # 默认
        
        # 3. 种群规模适中（权重 0.3）
        # 太小没有演化基础，太大缺乏选择压力
        population = species.morphology_stats.get("population", 0) or 0
        if 1000 <= population <= 100000:
            pop_score = 1.0
        elif 500 <= population < 1000:
            pop_score = 0.7
        elif 100000 < population <= 500000:
            pop_score = 0.6
        elif population > 0:
            pop_score = 0.3
        else:
            pop_score = 0.0
        score += pop_score * 0.3
        
        return min(1.0, max(0.0, score))
    
    def calculate_priority(
        self,
        species: "Species",
        death_rate: float,
        all_species: List["Species"],
        niche_metrics: Dict[str, Any] | None = None,
        food_web_analysis: Any | None = None,
    ) -> SpeciesPriority:
        """计算物种优先级
        
        综合 risk、impact、potential 计算加权优先级。
        """
        # 使用缓存
        cache_key = f"{species.lineage_code}_{death_rate:.3f}"
        if cache_key in self._priority_cache:
            return self._priority_cache[cache_key]
        
        risk = self.calculate_risk(species, death_rate, niche_metrics)
        impact = self.calculate_impact(species, all_species, food_web_analysis)
        potential = self.calculate_potential(species, niche_metrics)
        
        # 加权计算
        priority = (
            risk * self.config.risk_weight +
            impact * self.config.impact_weight +
            potential * self.config.potential_weight
        )
        
        result = SpeciesPriority(
            species_id=species.id or 0,
            lineage_code=species.lineage_code,
            risk=risk,
            impact=impact,
            potential=potential,
            priority=priority,
            population=species.morphology_stats.get("population", 0) or 0,
            death_rate=death_rate,
            trophic_level=getattr(species, 'trophic_level', 1.0) or 1.0,
        )
        
        self._priority_cache[cache_key] = result
        return result
    
    # =========================================================================
    # 分档
    # =========================================================================
    
    def partition_species(
        self,
        species_list: List["Species"],
        mortality_results: List[Any],
        niche_metrics: Dict[str, Any] | None = None,
        food_web_analysis: Any | None = None,
    ) -> PartitionResult:
        """将物种分档
        
        Args:
            species_list: 所有存活物种
            mortality_results: 死亡率评估结果
            niche_metrics: 生态位指标
            food_web_analysis: 食物网分析结果
            
        Returns:
            PartitionResult 包含三个档次的物种列表
        """
        # 构建死亡率映射
        death_rate_map = {
            r.species.lineage_code: r.death_rate
            for r in mortality_results
            if hasattr(r, 'species') and hasattr(r, 'death_rate')
        }
        
        # 计算所有物种的优先级
        priorities: List[SpeciesPriority] = []
        for species in species_list:
            if species.status != "alive":
                continue
            
            death_rate = death_rate_map.get(species.lineage_code, 0.1)
            priority = self.calculate_priority(
                species, death_rate, species_list,
                niche_metrics, food_web_analysis
            )
            priorities.append(priority)
        
        # 按优先级排序
        priorities.sort(key=lambda p: p.priority, reverse=True)
        
        # 分档
        tier_a = []
        tier_b = []
        tier_c = []
        
        for i, priority in enumerate(priorities):
            if i < self.config.top_a_count:
                priority.tier = AssessmentTier.A
                tier_a.append(priority)
            elif i < self.config.top_a_count + self.config.top_b_count:
                if priority.priority >= self.config.priority_threshold:
                    priority.tier = AssessmentTier.B
                    tier_b.append(priority)
                else:
                    priority.tier = AssessmentTier.C
                    tier_c.append(priority)
            else:
                priority.tier = AssessmentTier.C
                tier_c.append(priority)
        
        logger.info(
            f"[EcologicalIntelligence] 分档完成: "
            f"A={len(tier_a)}, B={len(tier_b)}, C={len(tier_c)}"
        )
        
        return PartitionResult(tier_a=tier_a, tier_b=tier_b, tier_c=tier_c)
    
    # =========================================================================
    # DTO 构建
    # =========================================================================
    
    def build_species_input(
        self,
        species: "Species",
        priority: SpeciesPriority,
        recent_events: List[str] | None = None,
    ) -> SpeciesAssessmentInput:
        """构建单个物种的评估输入 DTO"""
        # 提取气候耐受度
        climate_tolerance = {}
        climate_niche = getattr(species, 'climate_niche', None)
        if climate_niche:
            if hasattr(climate_niche, 'optimal_temp'):
                climate_tolerance['optimal_temp'] = climate_niche.optimal_temp
            if hasattr(climate_niche, 'temp_tolerance'):
                climate_tolerance['temp_tolerance'] = climate_niche.temp_tolerance
        
        # 提取饮食类型
        diet_type = ""
        if hasattr(species, 'diet'):
            diet = species.diet
            if hasattr(diet, 'type'):
                diet_type = diet.type
            elif isinstance(diet, str):
                diet_type = diet
        
        # 提取栖息地类型
        habitat_types = []
        if hasattr(species, 'habitats'):
            for h in species.habitats[:5]:  # 只取前5个
                if hasattr(h, 'biome'):
                    habitat_types.append(h.biome)
        
        # 提取活跃基因
        active_genes = []
        if hasattr(species, 'active_genes'):
            active_genes = list(species.active_genes)[:10]  # 只取前10个
        
        # 计算种群趋势（使用种群历史缓存）
        population_trend = 0.0
        from ..analytics.population_snapshot import get_population_history_cache
        history_cache = get_population_history_cache()
        if species.lineage_code in history_cache:
            history = history_cache[species.lineage_code][-5:]  # 最近5回合
            if len(history) >= 2:
                population_trend = (history[-1] - history[0]) / max(history[0], 1)
        
        return SpeciesAssessmentInput(
            species_id=species.id or 0,
            lineage_code=species.lineage_code,
            common_name=species.common_name or species.lineage_code,
            latin_name=species.latin_name or "",
            population=priority.population,
            death_rate=priority.death_rate,
            trophic_level=priority.trophic_level,
            climate_tolerance=climate_tolerance,
            diet_type=diet_type,
            habitat_types=habitat_types,
            genetic_diversity=len(getattr(species, 'hidden_traits', {}) or {}) / 10.0,
            active_genes=active_genes,
            population_trend=population_trend,
            recent_events=recent_events or [],
            tier=priority.tier,
            priority_score=priority.priority,
        )
    
    def build_environment_summary(
        self,
        turn_index: int,
        modifiers: Dict[str, float] | None,
        major_events: List[Any] | None,
        map_state: Any | None,
        species_count: int,
    ) -> EnvironmentSummary:
        """构建环境摘要 DTO"""
        # 提取气候信息
        global_temp = 15.0
        temp_change = 0.0
        sea_level = 0.0
        sea_level_change = 0.0
        
        if map_state:
            global_temp = getattr(map_state, 'global_avg_temperature', 15.0)
            sea_level = getattr(map_state, 'sea_level', 0.0)
        
        if modifiers:
            temp_change = modifiers.get('temperature', 0.0)
            sea_level_change = modifiers.get('sea_level', 0.0)
        
        # 提取重大事件
        event_names = []
        if major_events:
            for event in major_events:
                if hasattr(event, 'kind'):
                    event_names.append(event.kind)
                elif isinstance(event, str):
                    event_names.append(event)
        
        return EnvironmentSummary(
            turn_index=turn_index,
            global_temperature=global_temp,
            temperature_change=temp_change,
            sea_level=sea_level,
            sea_level_change=sea_level_change,
            active_pressures=modifiers or {},
            major_events=event_names,
            total_species_count=species_count,
        )
    
    def build_assessment_batches(
        self,
        partition: PartitionResult,
        species_map: Dict[str, "Species"],
        environment: EnvironmentSummary,
    ) -> Tuple[AssessmentBatch, AssessmentBatch]:
        """构建 A/B 两个评估批次
        
        Args:
            partition: 分档结果
            species_map: lineage_code -> Species 映射
            environment: 环境摘要
            
        Returns:
            (batch_a, batch_b) 两个批次
        """
        # 构建 A 批次
        a_inputs = []
        for priority in partition.tier_a:
            species = species_map.get(priority.lineage_code)
            if species:
                input_dto = self.build_species_input(species, priority)
                a_inputs.append(input_dto)
        
        batch_a = AssessmentBatch(
            tier=AssessmentTier.A,
            species_inputs=a_inputs,
            environment=environment,
        )
        
        # 构建 B 批次
        b_inputs = []
        for priority in partition.tier_b:
            species = species_map.get(priority.lineage_code)
            if species:
                input_dto = self.build_species_input(species, priority)
                b_inputs.append(input_dto)
        
        batch_b = AssessmentBatch(
            tier=AssessmentTier.B,
            species_inputs=b_inputs,
            environment=environment,
        )
        
        logger.info(
            f"[EcologicalIntelligence] 批次构建完成: "
            f"A批={batch_a.count}, B批={batch_b.count}"
        )
        
        return batch_a, batch_b

