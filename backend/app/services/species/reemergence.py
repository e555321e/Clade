"""
Reemergence Service - 物种重现服务

处理灭绝物种的重新出现（通过残存种群或近缘物种）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...repositories.species_repository import SpeciesRepository
    from ...models.species import Species

logger = logging.getLogger(__name__)


class ReemergenceEvent:
    """重现事件"""
    
    def __init__(
        self,
        species_code: str,
        species_name: str,
        reason: str,
    ):
        self.species_code = species_code
        self.species_name = species_name
        self.reason = reason


class ReemergenceService:
    """物种重现服务
    
    在大灭绝等事件后，评估是否有物种可以重新出现。
    """
    
    def __init__(
        self,
        species_repository: "SpeciesRepository",
    ):
        self.species_repository = species_repository
    
    def evaluate_reemergence(
        self,
        candidates: List["Species"],
        modifiers: Dict[str, float] | None = None,
    ) -> List[ReemergenceEvent]:
        """评估物种重现
        
        Args:
            candidates: 候选物种列表
            modifiers: 环境修正系数
            
        Returns:
            重现事件列表
        """
        events = []
        
        for species in candidates:
            # 评估该物种是否可以重现
            # 基于遗传多样性、适应性等因素
            can_reemerge = self._check_reemergence_conditions(species, modifiers)
            
            if can_reemerge:
                event = ReemergenceEvent(
                    species_code=species.lineage_code,
                    species_name=species.common_name,
                    reason="残存种群恢复",
                )
                events.append(event)
                
                # 更新物种状态
                species.status = "alive"
                species.morphology_stats["population"] = 100  # 初始恢复种群
                self.species_repository.upsert(species)
                
                logger.info(f"[重现] {species.common_name} 重新出现")
        
        return events
    
    def _check_reemergence_conditions(
        self,
        species: "Species",
        modifiers: Dict[str, float] | None,
    ) -> bool:
        """检查重现条件
        
        Args:
            species: 物种
            modifiers: 环境修正
            
        Returns:
            是否可以重现
        """
        # 检查遗传多样性
        hidden_traits = getattr(species, 'hidden_traits', {}) or {}
        genetic_diversity = len(hidden_traits)
        
        # 检查环境是否适合
        if modifiers:
            # 如果环境压力太大，不适合重现
            total_pressure = sum(abs(v) for v in modifiers.values())
            if total_pressure > 2.0:
                return False
        
        # 需要一定的遗传多样性
        return genetic_diversity >= 3


def create_reemergence_service(species_repository: "SpeciesRepository") -> ReemergenceService:
    """工厂函数：创建重现服务实例"""
    return ReemergenceService(species_repository)

