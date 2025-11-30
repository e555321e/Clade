"""
Population Snapshot Service - 种群快照服务

保存和管理种群历史数据快照。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...repositories.species_repository import SpeciesRepository
    from ...models.species import Species

logger = logging.getLogger(__name__)


# 全局缓存：存储种群历史 {lineage_code: [population_history]}
_population_history_cache: Dict[str, List[int]] = {}


def get_population_history_cache() -> Dict[str, List[int]]:
    """获取种群历史缓存"""
    return _population_history_cache


def clear_population_history_cache() -> None:
    """清空种群历史缓存"""
    _population_history_cache.clear()


class PopulationSnapshotService:
    """种群快照服务
    
    保存每回合的种群数据快照。
    使用内部缓存存储种群历史，避免修改 Species 模型。
    """
    
    def __init__(
        self,
        species_repository: "SpeciesRepository",
    ):
        self.species_repository = species_repository
    
    def save_snapshots(
        self,
        species_list: List["Species"],
        turn_index: int,
    ) -> None:
        """保存种群快照
        
        Args:
            species_list: 物种列表
            turn_index: 回合索引
        """
        for species in species_list:
            lineage_code = species.lineage_code
            
            # 使用缓存存储种群历史
            if lineage_code not in _population_history_cache:
                _population_history_cache[lineage_code] = []
            
            history = _population_history_cache[lineage_code]
            current_pop = species.morphology_stats.get("population", 0) or 0
            history.append(current_pop)
            
            # 只保留最近 100 回合的历史
            if len(history) > 100:
                _population_history_cache[lineage_code] = history[-100:]
        
        logger.debug(f"[快照] 回合 {turn_index}: 保存了 {len(species_list)} 个物种的快照")
    
    def get_population_history(self, lineage_code: str) -> List[int]:
        """获取物种的种群历史
        
        Args:
            lineage_code: 物种谱系代码
            
        Returns:
            种群历史列表
        """
        return _population_history_cache.get(lineage_code, [])
    
    def get_population_trend(
        self,
        species: "Species",
        window: int = 10,
    ) -> float:
        """获取种群趋势
        
        Args:
            species: 物种
            window: 观察窗口（回合数）
            
        Returns:
            趋势值（正=增长，负=下降）
        """
        history = _population_history_cache.get(species.lineage_code, [])
        if not history or len(history) < 2:
            return 0.0
        
        recent = history[-window:]
        if len(recent) < 2:
            return 0.0
        
        # 计算平均增长率
        growth_rate = (recent[-1] - recent[0]) / max(recent[0], 1)
        return growth_rate
    
    def get_species_snapshots(
        self,
        species_list: List["Species"],
    ) -> List[Dict[str, Any]]:
        """获取物种快照列表
        
        Args:
            species_list: 物种列表
            
        Returns:
            快照数据列表
        """
        snapshots = []
        
        for species in species_list:
            snapshot = {
                "lineage_code": species.lineage_code,
                "common_name": species.common_name,
                "status": species.status,
                "population": species.morphology_stats.get("population", 0) or 0,
                "trophic_level": getattr(species, 'trophic_level', 1.0) or 1.0,
            }
            snapshots.append(snapshot)
        
        return snapshots


def create_population_snapshot_service(
    species_repository: "SpeciesRepository",
) -> PopulationSnapshotService:
    """工厂函数：创建种群快照服务实例"""
    return PopulationSnapshotService(species_repository)

