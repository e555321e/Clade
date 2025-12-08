"""GPU-only tile mortality - 数据结构占位

TileBasedMortalityEngine 已被 TensorEcologyStage 替代。
本模块仅保留数据结构定义，供类型兼容。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from ..models.species import Species

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TileMortalityResult:
    """单个地块上单个物种的死亡率结果（数据结构保留）"""
    species: Species
    tile_id: int = 0
    tile_population: float = 0.0
    tile_death_rate: float = 0.0
    tile_deaths: int = 0
    tile_survivors: int = 0
    pressure_factor: float = 0.0
    competition_factor: float = 0.0
    trophic_factor: float = 0.0
    resource_factor: float = 0.0


@dataclass(slots=True)
class AggregatedMortalityResult:
    """汇总后的物种死亡率结果（数据结构保留）"""
    species: Species
    initial_population: int = 0
    deaths: int = 0
    survivors: int = 0
    death_rate: float = 0.0
    notes: list[str] | None = None
    niche_overlap: float = 0.0
    resource_pressure: float = 0.0
    is_background: bool = False
    tier: str = ""
    grazing_pressure: float = 0.0
    predation_pressure: float = 0.0
    tile_details: list[TileMortalityResult] | None = None
    ai_status_eval: object | None = None
    ai_narrative: str = ""
    ai_headline: str = ""
    ai_mood: str = ""
    death_causes: str = ""
    plant_competition_pressure: float = 0.0
    light_competition: float = 0.0
    nutrient_competition: float = 0.0
    herbivory_pressure: float = 0.0
    total_tiles: int = 0
    healthy_tiles: int = 0
    warning_tiles: int = 0
    critical_tiles: int = 0
    best_tile_rate: float = 0.0
    worst_tile_rate: float = 1.0
    has_refuge: bool = True
    births: int = 0
    final_population: int = 0
    adjusted_death_rate: float = 0.0
    adjusted_k: float = 0.0

    def get_distribution_status(self) -> str:
        if self.total_tiles == 0:
            return "无分布"
        if self.critical_tiles == self.total_tiles:
            return "全域危机"
        elif self.critical_tiles > self.total_tiles * 0.5:
            return "部分危机"
        elif self.healthy_tiles >= self.total_tiles * 0.5:
            return "稳定"
        return "警告"

    def get_distribution_summary(self) -> str:
        if self.total_tiles == 0:
            return "无分布数据"
        return f"分布{self.total_tiles}块"


class TileBasedMortalityEngine:
    """GPU-only 架构占位 - 计算已迁移到 TensorEcologyStage
    
    本类保留用于兼容性，核心方法返回空结果。
    实际死亡率计算由 TensorEcologyStage 完成。
    """

    def __init__(
        self,
        batch_limit: int = 0,
        ecology_config=None,
        mortality_config=None,
        speciation_config=None,
    ) -> None:
        self.batch_limit = batch_limit
        self._ecology_config = ecology_config
        self._mortality_config = mortality_config
        self._speciation_config = speciation_config
        self._embedding_service = None
        self._ecological_realism_data = None

    def set_embedding_service(self, service) -> None:
        self._embedding_service = service

    def reload_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self, f"_{key}"):
                setattr(self, f"_{key}", value)

    def build_matrices(self, species_list, tiles, habitats) -> None:
        """空操作 - 实际计算由 TensorEcologyStage 完成"""
        logger.debug("[TileBasedMortalityEngine] GPU-only: build_matrices 空操作")

    def evaluate(
        self,
        species_batch: Sequence[Species],
        pressure_modifiers: dict | None = None,
        niche_metrics: dict | None = None,
        tier: str | None = None,
        trophic_interactions: dict | None = None,
        extinct_codes: set | None = None,
        turn_index: int = 0,
    ) -> list[AggregatedMortalityResult]:
        """返回空结果 - 实际计算由 TensorEcologyStage 完成"""
        logger.debug("[TileBasedMortalityEngine] GPU-only: 返回空结果，实际计算由 TensorEcologyStage 完成")
        return []

    def get_speciation_candidates(self) -> dict:
        return {}

    def export_tensor_state(self):
        return None

    def get_all_species_tile_mortality(self) -> dict:
        return {}

    def get_species_tile_mortality(self, lineage_code: str) -> dict:
        return {}

    def get_tile_adjacency(self) -> dict:
        return {}
    
    def clear_accumulated_data(self) -> None:
        """清理累积数据 - 空操作"""
        pass
    
    def get_all_species_tile_survivors(self) -> dict:
        """返回空结果 - 实际计算由 TensorEcologyStage 完成"""
        return {}
    
    def get_species_tile_survivors(self, lineage_code: str) -> dict:
        """返回空结果 - 实际计算由 TensorEcologyStage 完成"""
        return {}


__all__ = [
    "TileBasedMortalityEngine",
    "TileMortalityResult",
    "AggregatedMortalityResult",
]
