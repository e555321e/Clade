"""
Extinction Checker Service - 灭绝检测服务

检测并处理物种灭绝事件。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...repositories.species_repository import SpeciesRepository

logger = logging.getLogger(__name__)


class ExtinctionChecker:
    """灭绝检测器
    
    检测种群过低或死亡率过高的物种，并标记为灭绝。
    """
    
    # 灭绝阈值
    EXTINCTION_POPULATION_THRESHOLD = 10
    EXTINCTION_RATE_THRESHOLD = 0.95
    
    def __init__(
        self,
        species_repository: "SpeciesRepository",
        turn_counter: int,
        event_callback: Callable[[str, str, str], None] | None = None,
    ):
        self.species_repository = species_repository
        self.turn_counter = turn_counter
        self.event_callback = event_callback
    
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
        
        for result in mortality_results:
            species = result.species
            if species.status != "alive":
                continue
            
            lineage_code = species.lineage_code
            final_pop = new_populations.get(lineage_code, 0)
            death_rate = result.death_rate
            
            # 检查是否灭绝
            should_extinct = False
            reason = ""
            
            if final_pop <= self.EXTINCTION_POPULATION_THRESHOLD:
                should_extinct = True
                reason = f"种群过低 ({final_pop})"
            elif death_rate >= self.EXTINCTION_RATE_THRESHOLD:
                should_extinct = True
                reason = f"死亡率过高 ({death_rate:.1%})"
            
            if should_extinct:
                # 标记为灭绝
                species.status = "extinct"
                species.morphology_stats["population"] = 0
                species.morphology_stats["extinction_turn"] = self.turn_counter
                species.morphology_stats["extinction_reason"] = reason
                
                self.species_repository.upsert(species)
                extinct_codes.append(lineage_code)
                
                logger.info(f"[灭绝] {species.common_name} ({lineage_code}): {reason}")
                self._emit_event(
                    "extinction",
                    f"💀 灭绝: {species.common_name} - {reason}",
                    "灭绝",
                )
        
        if extinct_codes:
            logger.info(f"[灭绝检测] 本回合 {len(extinct_codes)} 个物种灭绝")
        
        return extinct_codes
    
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

