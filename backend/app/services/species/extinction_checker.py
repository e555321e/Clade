"""
Extinction Checker Service - 灭绝检测服务

检测并处理物种灭绝事件。

【增强 v2】多维度灭绝检测：
1. 绝对阈值：种群低于阈值直接灭绝
2. 死亡率阈值：单回合死亡率过高灭绝
3. 最小可存活种群 (MVP)：种群长期过低灭绝
4. 竞争劣势：种群相对其他物种太小灭绝
5. 近交衰退：种群过小导致遗传问题
6. 连续衰退：种群持续下降灭绝
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...repositories.species_repository import SpeciesRepository
    from ...models.config import SpeciationConfig

logger = logging.getLogger(__name__)


class ExtinctionChecker:
    """灭绝检测器
    
    检测种群过低或死亡率过高的物种，并标记为灭绝。
    
    【多维度灭绝机制】
    1. 绝对灭绝：种群低于阈值
    2. 死亡率灭绝：单回合死亡率过高
    3. MVP 灭绝：最小可存活种群检测
    4. 竞争灭绝：相对种群太小
    5. 近交衰退：遗传多样性丧失
    6. 衰退灭绝：连续衰退
    """
    
    # 默认灭绝阈值（可被配置覆盖）
    DEFAULT_EXTINCTION_POPULATION_THRESHOLD = 100
    DEFAULT_EXTINCTION_RATE_THRESHOLD = 0.95
    DEFAULT_MVP = 1000
    DEFAULT_MVP_EXTINCTION_TURNS = 5
    DEFAULT_COMPETITION_EXTINCTION_RATIO = 0.01
    DEFAULT_INBREEDING_THRESHOLD = 5000
    DEFAULT_CONSECUTIVE_DECLINE_TURNS = 8
    
    def __init__(
        self,
        species_repository: "SpeciesRepository",
        turn_counter: int,
        event_callback: Callable[[str, str, str], None] | None = None,
        config: "SpeciationConfig | None" = None,
    ):
        self.species_repository = species_repository
        self.turn_counter = turn_counter
        self.event_callback = event_callback
        self.config = config
        
        # 追踪 MVP 和衰退状态 {lineage_code: count}
        self._mvp_warning_counts: Dict[str, int] = {}
        self._decline_streak_counts: Dict[str, int] = {}
        self._previous_populations: Dict[str, int] = {}
    
    def _get_threshold(self, attr: str, default: Any) -> Any:
        """从配置获取阈值，如果没有配置则使用默认值"""
        if self.config:
            return getattr(self.config, attr, default)
        return default
    
    def _emit_event(self, event_type: str, message: str, category: str = "灭绝"):
        """发送事件"""
        if self.event_callback:
            try:
                self.event_callback(event_type, message, category)
            except Exception:
                pass
    
    def check_and_apply(
        self,
        mortality_results: List[Any],
        new_populations: Dict[str, int],
    ) -> List[str]:
        """检测并应用灭绝
        
        Args:
            mortality_results: 死亡率评估结果列表
            new_populations: 更新后的种群数量 {lineage_code: population}
            
        Returns:
            灭绝物种的 lineage_code 列表
        """
        extinct_codes = []
        
        # 获取配置阈值
        pop_threshold = self._get_threshold(
            'extinction_population_threshold', 
            self.DEFAULT_EXTINCTION_POPULATION_THRESHOLD
        )
        rate_threshold = self._get_threshold(
            'extinction_death_rate_threshold', 
            self.DEFAULT_EXTINCTION_RATE_THRESHOLD
        )
        mvp = self._get_threshold('minimum_viable_population', self.DEFAULT_MVP)
        mvp_extinction_turns = self._get_threshold(
            'mvp_extinction_turns', 
            self.DEFAULT_MVP_EXTINCTION_TURNS
        )
        competition_ratio = self._get_threshold(
            'competition_extinction_ratio', 
            self.DEFAULT_COMPETITION_EXTINCTION_RATIO
        )
        inbreeding_threshold = self._get_threshold(
            'inbreeding_depression_threshold', 
            self.DEFAULT_INBREEDING_THRESHOLD
        )
        decline_turns = self._get_threshold(
            'consecutive_decline_extinction_turns', 
            self.DEFAULT_CONSECUTIVE_DECLINE_TURNS
        )
        decline_threshold = self._get_threshold('decline_detection_threshold', 0.1)
        
        # 计算生态系统平均种群（用于竞争灭绝判断）
        alive_populations = [
            new_populations.get(r.species.lineage_code, 0)
            for r in mortality_results
            if r.species.status == "alive" and new_populations.get(r.species.lineage_code, 0) > 0
        ]
        avg_population = sum(alive_populations) / len(alive_populations) if alive_populations else 0
        competition_threshold = avg_population * competition_ratio
        
        for result in mortality_results:
            species = result.species
            if species.status != "alive":
                continue
            
            lineage_code = species.lineage_code
            final_pop = new_populations.get(lineage_code, 0)
            death_rate = result.death_rate
            initial_pop = result.initial_population
            
            # 检查是否灭绝
            should_extinct = False
            reason = ""
            warning_message = ""
            
            # ========== 规则1: 绝对灭绝阈值 ==========
            if final_pop <= pop_threshold:
                should_extinct = True
                reason = f"种群过低 ({final_pop:,} kg)"
            
            # ========== 规则2: 死亡率灭绝 ==========
            elif death_rate >= rate_threshold:
                should_extinct = True
                reason = f"死亡率过高 ({death_rate:.1%})"
            
            # ========== 规则3: 最小可存活种群 (MVP) ==========
            elif final_pop < mvp:
                # 更新 MVP 警告计数
                self._mvp_warning_counts[lineage_code] = \
                    self._mvp_warning_counts.get(lineage_code, 0) + 1
                mvp_count = self._mvp_warning_counts[lineage_code]
                
                if mvp_count >= mvp_extinction_turns:
                    should_extinct = True
                    reason = f"种群长期低于最小可存活值 ({final_pop:,} kg，连续 {mvp_count} 回合)"
                else:
                    warning_message = f"⚠️ {species.common_name} 种群低于 MVP ({final_pop:,}/{mvp:,} kg)，已持续 {mvp_count} 回合"
            else:
                # 种群恢复，重置 MVP 警告
                self._mvp_warning_counts[lineage_code] = 0
            
            # ========== 规则4: 竞争灭绝 ==========
            if not should_extinct and avg_population > 0:
                if final_pop < competition_threshold and final_pop < mvp:
                    # 种群太小，在竞争中完全劣势
                    should_extinct = True
                    reason = f"竞争劣势灭绝 (种群 {final_pop:,} kg，仅占平均值的 {final_pop/avg_population*100:.2f}%)"
            
            # ========== 规则5: 连续衰退灭绝 ==========
            if not should_extinct and lineage_code in self._previous_populations:
                prev_pop = self._previous_populations[lineage_code]
                if prev_pop > 0:
                    decline_rate = (prev_pop - final_pop) / prev_pop
                    if decline_rate > decline_threshold:
                        # 种群在衰退
                        self._decline_streak_counts[lineage_code] = \
                            self._decline_streak_counts.get(lineage_code, 0) + 1
                    else:
                        # 种群稳定或增长，重置计数
                        self._decline_streak_counts[lineage_code] = 0
                    
                    streak = self._decline_streak_counts.get(lineage_code, 0)
                    if streak >= decline_turns:
                        should_extinct = True
                        reason = f"连续衰退灭绝 (连续 {streak} 回合下降)"
                    elif streak >= decline_turns - 2:
                        warning_message = f"⚠️ {species.common_name} 种群持续下降 ({streak} 回合)"
            
            # 更新历史种群记录
            self._previous_populations[lineage_code] = final_pop
            
            # ========== 应用灭绝 ==========
            if should_extinct:
                # 标记为灭绝
                species.status = "extinct"
                species.morphology_stats["population"] = 0
                species.morphology_stats["extinction_turn"] = self.turn_counter
                species.morphology_stats["extinction_reason"] = reason
                
                self.species_repository.upsert(species)
                extinct_codes.append(lineage_code)
                
                # 清理追踪数据
                self._mvp_warning_counts.pop(lineage_code, None)
                self._decline_streak_counts.pop(lineage_code, None)
                self._previous_populations.pop(lineage_code, None)
                
                logger.info(f"[灭绝] {species.common_name} ({lineage_code}): {reason}")
                self._emit_event(
                    "extinction",
                    f"💀 灭绝: {species.common_name} - {reason}",
                    "灭绝",
                )
            elif warning_message:
                # 发送警告但不灭绝
                logger.warning(warning_message)
                self._emit_event("warn", warning_message, "濒危")
        
        if extinct_codes:
            logger.info(f"[灭绝检测] 本回合 {len(extinct_codes)} 个物种灭绝")
        
        return extinct_codes
    
    def calculate_inbreeding_penalty(self, population: int) -> float:
        """计算近交衰退惩罚（额外死亡率）
        
        Args:
            population: 当前种群数量
            
        Returns:
            额外死亡率 (0-1)
        """
        threshold = self._get_threshold(
            'inbreeding_depression_threshold', 
            self.DEFAULT_INBREEDING_THRESHOLD
        )
        coefficient = self._get_threshold('inbreeding_depression_coefficient', 0.15)
        
        if population >= threshold:
            return 0.0
        
        # 种群越低，近交衰退越严重
        ratio = population / threshold
        penalty = (1 - ratio) * coefficient
        return min(0.5, penalty)  # 最高 50% 额外死亡率
    
    def check_population_trend(
        self,
        species: Any,
        history_window: int = 5,
    ) -> bool:
        """检查物种是否处于持续下降趋势
        
        Args:
            species: 物种对象
            history_window: 检查的历史窗口大小
            
        Returns:
            是否处于下降趋势
        """
        # 使用种群历史缓存
        from ..analytics.population_snapshot import get_population_history_cache
        history_cache = get_population_history_cache()
        
        lineage_code = getattr(species, 'lineage_code', None)
        if not lineage_code or lineage_code not in history_cache:
            return False
        
        history = history_cache[lineage_code]
        if len(history) < 2:
            return False
        
        # 检查最近几回合是否持续下降
        recent = history[-history_window:]
        for i in range(1, len(recent)):
            if recent[i] >= recent[i - 1]:
                return False
        
        return True
    
    def get_extinction_risk(self, species: Any, population: int) -> dict:
        """获取物种的灭绝风险评估
        
        Args:
            species: 物种对象
            population: 当前种群
            
        Returns:
            风险评估字典
        """
        pop_threshold = self._get_threshold(
            'extinction_population_threshold', 
            self.DEFAULT_EXTINCTION_POPULATION_THRESHOLD
        )
        mvp = self._get_threshold('minimum_viable_population', self.DEFAULT_MVP)
        inbreeding_threshold = self._get_threshold(
            'inbreeding_depression_threshold', 
            self.DEFAULT_INBREEDING_THRESHOLD
        )
        
        lineage_code = getattr(species, 'lineage_code', '')
        
        risks = []
        risk_level = "safe"
        risk_score = 0.0
        
        # 检查各种风险
        if population <= pop_threshold:
            risks.append("种群极低，即将灭绝")
            risk_level = "critical"
            risk_score = 1.0
        elif population < mvp:
            mvp_count = self._mvp_warning_counts.get(lineage_code, 0)
            risks.append(f"低于最小可存活种群 (MVP)，已持续 {mvp_count} 回合")
            risk_level = "endangered" if mvp_count >= 2 else "vulnerable"
            risk_score = 0.7 + mvp_count * 0.1
        elif population < inbreeding_threshold:
            risks.append("种群较小，可能受近交衰退影响")
            risk_level = "vulnerable"
            risk_score = 0.3
        
        # 检查衰退趋势
        decline_streak = self._decline_streak_counts.get(lineage_code, 0)
        if decline_streak >= 3:
            risks.append(f"种群持续下降 ({decline_streak} 回合)")
            if risk_level == "safe":
                risk_level = "vulnerable"
            risk_score = max(risk_score, 0.4 + decline_streak * 0.1)
        
        return {
            "lineage_code": lineage_code,
            "population": population,
            "risk_level": risk_level,
            "risk_score": min(1.0, risk_score),
            "risks": risks,
            "inbreeding_penalty": self.calculate_inbreeding_penalty(population),
        }

