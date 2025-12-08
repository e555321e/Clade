"""GPU-only species mortality - 数据结构占位

MortalityEngine 已被 TensorEcologyStage 替代。
本模块仅保留数据结构定义，供类型兼容。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from ..models.species import Species

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MortalityResult:
    """死亡率计算结果（数据结构保留）"""
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
    ai_status_eval: object | None = None
    ai_narrative: str = ""
    ai_headline: str = ""
    ai_mood: str = ""
    death_causes: str = ""
    
    # 额外字段供张量系统回写
    births: int = 0
    final_population: int = 0
    adjusted_death_rate: float = 0.0
    adjusted_k: float = 0.0


class MortalityEngine:
    """GPU-only 架构占位 - 计算已迁移到 TensorEcologyStage
    
    本类保留用于兼容性，evaluate() 返回空结果。
    实际死亡率计算由 TensorEcologyStage 完成。
    """

    def __init__(self, batch_limit: int = 0, ecology_config=None) -> None:
        self.batch_limit = batch_limit
        self._ecology_config = ecology_config

    def evaluate(
        self,
        species_batch: Sequence[Species],
        pressure_modifiers: dict | None = None,
        niche_metrics: dict | None = None,
        tier: str | None = None,
        trophic_interactions: dict | None = None,
        extinct_codes: set | None = None,
    ) -> list[MortalityResult]:
        """返回空结果 - 实际计算由 TensorEcologyStage 完成"""
        logger.debug("[MortalityEngine] GPU-only: 返回空结果，实际计算由 TensorEcologyStage 完成")
        return []

    def reload_config(self, ecology_config=None) -> None:
        self._ecology_config = ecology_config


__all__ = ["MortalityEngine", "MortalityResult"]
