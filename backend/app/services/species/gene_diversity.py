from __future__ import annotations

"""
GeneDiversityService
--------------------
负责基于 Embedding 的基因多样性半径更新与可达性判断。

核心功能：
- 初始化/迁移旧数据（hidden_traits.gene_diversity -> gene_diversity_radius）
- 回合自然增长 + 瓶颈衰减
- 分化继承、杂交加成、激活消耗
- Embedding 距离可达性判断（休眠基因激活前置检查）
"""

import logging
import math
import random
from typing import TYPE_CHECKING, Iterable

import numpy as np

try:
    from ...services.system.embedding import EmbeddingService
except Exception:  # pragma: no cover - 延迟导入失败时兜底
    EmbeddingService = None  # type: ignore

if TYPE_CHECKING:
    from ...models.config import GeneDiversityConfig

logger = logging.getLogger(__name__)


def _load_gene_diversity_config() -> "GeneDiversityConfig | None":
    """从 settings.json 加载基因多样性配置"""
    try:
        from ...core.config import PROJECT_ROOT
        from ...repositories.environment_repository import environment_repository
        ui_cfg = environment_repository.load_ui_config(PROJECT_ROOT / "data/settings.json")
        return ui_cfg.gene_diversity
    except Exception:
        return None


class GeneDiversityService:
    """基因多样性服务
    
    所有参数从 GeneDiversityConfig 配置读取，支持前端调整。
    """
    
    def __init__(self, embedding_service: "EmbeddingService | None" = None) -> None:
        self.embedding = embedding_service
        self._config: "GeneDiversityConfig | None" = None
    
    @property
    def config(self) -> "GeneDiversityConfig":
        """懒加载配置"""
        if self._config is None:
            self._config = _load_gene_diversity_config()
        if self._config is None:
            # 返回默认配置
            from ...models.config import GeneDiversityConfig
            self._config = GeneDiversityConfig()
        return self._config
    
    def reload_config(self) -> None:
        """重新加载配置（用于热更新）"""
        self._config = _load_gene_diversity_config()
    
    # 属性代理：从配置读取
    @property
    def MIN_RADIUS(self) -> float:
        return self.config.min_radius
    
    @property
    def MAX_DECAY(self) -> float:
        return self.config.max_decay_per_turn
    
    @property
    def ACTIVATION_COST(self) -> float:
        return self.config.activation_cost
    
    @property
    def BOTTLENECK_COEFF(self) -> float:
        return self.config.bottleneck_coefficient
    
    @property
    def HYBRID_BONUS_RANGE(self) -> tuple[float, float]:
        return (self.config.hybrid_bonus_min, self.config.hybrid_bonus_max)
    
    @property
    def DISCOVERY_BONUS_RANGE(self) -> tuple[float, float]:
        return (self.config.discovery_bonus_min, self.config.discovery_bonus_max)

    # ------------------------------------------------------------------ #
    # 初始化与迁移
    # ------------------------------------------------------------------ #
    def ensure_initialized(self, species, turn_index: int = 0) -> None:
        """为旧存档补齐新字段，并同步 hidden_traits 方便兼容。"""
        if getattr(species, "gene_diversity_radius", None) is None or species.gene_diversity_radius <= 0:
            species.gene_diversity_radius = self._initial_radius(turn_index, species)

        if getattr(species, "explored_directions", None) is None:
            species.explored_directions = []

        if getattr(species, "gene_stability", None) is None:
            species.gene_stability = 0.5

        # 将半径写回 hidden_traits 以兼容旧逻辑
        if not species.hidden_traits:
            species.hidden_traits = {}
        species.hidden_traits["gene_diversity"] = float(species.gene_diversity_radius)

    def _initial_radius(self, turn_index: int, species) -> float:
        """按时代设置初始半径，同时尊重旧的 gene_diversity 值。"""
        legacy = None
        try:
            legacy = species.hidden_traits.get("gene_diversity")
        except Exception:
            legacy = None

        if isinstance(legacy, (int, float)) and legacy > 0:
            return float(self._clamp_radius(legacy))

        # 从配置读取时代参数
        params = self._epoch_params(turn_index)
        return params.get("initial_radius", 0.35)

    # ------------------------------------------------------------------ #
    # 每回合更新
    # ------------------------------------------------------------------ #
    def update_per_turn(
        self,
        species,
        population: int,
        death_rate: float,
        turn_index: int,
    ) -> dict:
        """
        应用自然增长 + 瓶颈衰减 + 自发突变发现。

        返回 dict 便于日志/报告：
        {"old": float, "new": float, "delta": float, "reason": str, "mutation_discovered": bool}
        """
        self.ensure_initialized(species, turn_index)

        pop = max(population or 0, 1)
        death = max(0.0, min(1.0, death_rate or 0.0))

        params = self._epoch_params(turn_index)
        growth = params["growth_rate"]  # 比例
        mutation_chance = params.get("mutation_chance", 0.0)

        # 瓶颈衰减 = k / sqrt(pop) × 压力系数（缩放 0.01 以得到百分比）
        pressure_factor = 1.0 + death * 1.5  # 高死亡率 → 更强压力
        decay = min(
            self.MAX_DECAY,
            (self.BOTTLENECK_COEFF / math.sqrt(pop)) * pressure_factor * 0.01,
        )

        net_change = growth - decay
        old_radius = float(species.gene_diversity_radius or self.MIN_RADIUS)
        new_radius = self._clamp_radius(old_radius * (1.0 + net_change))
        
        # 【新增】自发突变发现：按概率扩展演化范围
        mutation_discovered = False
        if mutation_chance > 0 and random.random() < mutation_chance:
            # 高死亡率环境下突变发现更容易（压力驱动演化）
            pressure_bonus = min(0.5, death * 0.5)  # 最高+50%概率
            if random.random() < (1.0 + pressure_bonus):
                mutation_discovered = True
                # 应用发现加成
                discovery_bonus = random.uniform(*self.DISCOVERY_BONUS_RANGE)
                new_radius = self._clamp_radius(new_radius * (1.0 + discovery_bonus))
                logger.info(
                    f"[突变发现] {getattr(species, 'common_name', species.lineage_code)} "
                    f"自发发现新基因，演化范围扩展 +{discovery_bonus:.1%}"
                )

        species.gene_diversity_radius = new_radius
        species.hidden_traits["gene_diversity"] = new_radius

        if mutation_discovered:
            reason = "突变发现"
        elif net_change >= 0:
            reason = "自然增长"
        else:
            reason = "瓶颈衰减"
        
        return {
            "old": old_radius, 
            "new": new_radius, 
            "delta": new_radius - old_radius, 
            "reason": reason,
            "mutation_discovered": mutation_discovered,
        }

    # ------------------------------------------------------------------ #
    # 分化/杂交/激活
    # ------------------------------------------------------------------ #
    def inherit_radius(self, parent_radius: float, turn_index: int) -> float:
        params = self._epoch_params(turn_index)
        low, high = params["inherit_range"]
        factor = random.uniform(low, high)
        return self._clamp_radius(parent_radius * factor)

    def apply_hybrid_bonus(self, parent_radii: Iterable[float]) -> float:
        base = max(self.MIN_RADIUS, max(parent_radii, default=0.35))
        bonus = random.uniform(*self.HYBRID_BONUS_RANGE)
        return self._clamp_radius(base * (1.0 + bonus))

    def consume_on_activation(self, species) -> None:
        """激活休眠基因后轻微缩小半径。"""
        self.ensure_initialized(species)
        species.gene_diversity_radius = self._clamp_radius(
            species.gene_diversity_radius * (1.0 - self.ACTIVATION_COST)
        )
        species.hidden_traits["gene_diversity"] = species.gene_diversity_radius

    def expand_on_discovery(self, species, bonus: float | None = None) -> None:
        """发现新基因/器官时扩大半径。"""
        self.ensure_initialized(species)
        bonus_factor = bonus if bonus is not None else random.uniform(*self.DISCOVERY_BONUS_RANGE)
        species.gene_diversity_radius = self._clamp_radius(
            species.gene_diversity_radius * (1.0 + bonus_factor)
        )
        species.hidden_traits["gene_diversity"] = species.gene_diversity_radius

    # ------------------------------------------------------------------ #
    # 张量批量计算优化
    # ------------------------------------------------------------------ #
    def batch_update_per_turn(
        self,
        species_list: list,
        population_map: dict[str, int],
        death_rate_map: dict[str, float],
        turn_index: int,
    ) -> list[dict]:
        """批量更新物种的基因多样性半径（张量优化）
        
        使用 numpy 向量化操作，一次性计算所有物种的半径变化，
        避免循环中的重复配置加载和对象访问。
        
        Args:
            species_list: 物种列表
            population_map: {lineage_code: population} 映射
            death_rate_map: {lineage_code: death_rate} 映射
            turn_index: 当前回合
            
        Returns:
            [{"lineage_code": str, "name": str, "old": float, "new": float, "delta": float, "reason": str, "mutation_discovered": bool}, ...]
        """
        if not species_list:
            return []
        
        # 确保所有物种初始化
        for sp in species_list:
            self.ensure_initialized(sp, turn_index)
        
        # 获取时代参数（所有物种共享）
        params = self._epoch_params(turn_index)
        growth = params["growth_rate"]
        mutation_chance = params.get("mutation_chance", 0.0)
        
        # 构建张量
        n = len(species_list)
        codes = [sp.lineage_code for sp in species_list]
        names = [getattr(sp, "common_name", sp.lineage_code) for sp in species_list]
        
        # 当前半径数组
        radii = np.array([
            sp.gene_diversity_radius or self.MIN_RADIUS 
            for sp in species_list
        ], dtype=float)
        
        # 种群和死亡率数组
        pops = np.array([
            max(population_map.get(code, 1), 1) 
            for code in codes
        ], dtype=float)
        
        deaths = np.array([
            max(0.0, min(1.0, death_rate_map.get(code, 0.0)))
            for code in codes
        ], dtype=float)
        
        # 向量化计算瓶颈衰减
        pressure_factors = 1.0 + deaths * 1.5
        decays = np.minimum(
            self.MAX_DECAY,
            (self.BOTTLENECK_COEFF / np.sqrt(pops)) * pressure_factors * 0.01
        )
        
        # 向量化计算净变化和新半径
        net_changes = growth - decays
        new_radii = np.clip(radii * (1.0 + net_changes), self.MIN_RADIUS, 1.0)
        
        # 【新增】自发突变发现（向量化概率判定）
        mutation_discovered = np.zeros(n, dtype=bool)
        if mutation_chance > 0:
            # 基础突变概率
            base_rolls = np.random.random(n)
            # 压力驱动加成（高死亡率环境更易突变）
            pressure_bonus = np.minimum(0.5, deaths * 0.5)
            mutation_discovered = base_rolls < (mutation_chance * (1.0 + pressure_bonus))
            
            # 为突变发现的物种应用额外加成
            if np.any(mutation_discovered):
                discovery_bonuses = np.random.uniform(
                    self.DISCOVERY_BONUS_RANGE[0],
                    self.DISCOVERY_BONUS_RANGE[1],
                    n
                )
                new_radii = np.where(
                    mutation_discovered,
                    np.clip(new_radii * (1.0 + discovery_bonuses), self.MIN_RADIUS, 1.0),
                    new_radii
                )
        
        # 批量更新物种对象
        results = []
        mutation_count = 0
        for i, sp in enumerate(species_list):
            old_r = float(radii[i])
            new_r = float(new_radii[i])
            sp.gene_diversity_radius = new_r
            if sp.hidden_traits is None:
                sp.hidden_traits = {}
            sp.hidden_traits["gene_diversity"] = new_r
            
            is_mutation = bool(mutation_discovered[i])
            if is_mutation:
                reason = "突变发现"
                mutation_count += 1
            elif net_changes[i] >= 0:
                reason = "自然增长"
            else:
                reason = "瓶颈衰减"
            
            results.append({
                "lineage_code": codes[i],
                "name": names[i],
                "old": old_r,
                "new": new_r,
                "delta": new_r - old_r,
                "reason": reason,
                "mutation_discovered": is_mutation,
            })
        
        if mutation_count > 0:
            logger.info(f"[突变发现] 本回合有 {mutation_count} 个物种自发发现新基因")
        
        return results

    def batch_is_reachable(
        self,
        species_vectors: list[list[float] | None],
        target_vec: list[float] | None,
        radii: list[float],
    ) -> list[bool]:
        """批量判断多个物种向量是否在可达半径内（张量优化）
        
        Args:
            species_vectors: 物种向量列表
            target_vec: 目标压力向量
            radii: 对应的基因多样性半径列表
            
        Returns:
            布尔列表，表示每个物种是否可达
        """
        if not species_vectors:
            return []
        
        n = len(species_vectors)
        results = [True] * n  # 默认可达
        
        if target_vec is None:
            return results
        
        try:
            target = np.array(target_vec, dtype=float)
            target_norm = np.linalg.norm(target)
            if target_norm == 0:
                return results
            target_normalized = target / target_norm
            
            # 筛选有效向量
            valid_indices = []
            valid_vectors = []
            valid_radii = []
            
            for i, (vec, r) in enumerate(zip(species_vectors, radii)):
                if vec is not None and len(vec) == len(target):
                    valid_indices.append(i)
                    valid_vectors.append(vec)
                    valid_radii.append(r)
            
            if not valid_vectors:
                return results
            
            # 构建矩阵进行批量计算
            mat = np.array(valid_vectors, dtype=float)  # (m, dim)
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            
            # 避免除零
            norms = np.where(norms == 0, 1, norms)
            mat_normalized = mat / norms
            
            # 批量计算余弦相似度
            cos_sims = mat_normalized @ target_normalized  # (m,)
            distances = 1.0 - cos_sims  # 余弦距离
            
            # 判断可达性
            radii_arr = np.array(valid_radii, dtype=float)
            reachable = distances < radii_arr
            
            # 写回结果
            for i, idx in enumerate(valid_indices):
                results[idx] = bool(reachable[i])
            
            return results
            
        except Exception as e:
            logger.warning(f"[GeneDiversity] 批量可达性计算失败: {e}")
            return results

    # ------------------------------------------------------------------ #
    # Embedding 可达性（单物种版本，保持兼容）
    # ------------------------------------------------------------------ #
    def is_reachable(self, species_vec: list[float] | None, target_vec: list[float] | None, radius: float) -> bool:
        """以余弦距离判定是否在可达半径内。"""
        if not species_vec or not target_vec:
            # 没有向量时默认可达，避免阻塞激活
            return radius >= self.MIN_RADIUS

        try:
            a = np.array(species_vec, dtype=float)
            b = np.array(target_vec, dtype=float)
            if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
                return radius >= self.MIN_RADIUS
            cos_sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
            distance = 1.0 - cos_sim  # 将相似度转为距离 (0~2)
            return distance < radius
        except Exception:
            return radius >= self.MIN_RADIUS

    def get_pressure_vector(self, pressure_type: str) -> list[float] | None:
        """从 Embedding 服务获取压力向量。"""
        if not self.embedding:
            return None
        try:
            return self.embedding.embed_single(pressure_type)
        except Exception:
            return None

    def record_direction(self, species, direction: int) -> None:
        """记录已探索方向（稀疏整数索引）。"""
        try:
            if direction not in species.explored_directions:
                species.explored_directions.append(direction)
        except Exception:
            species.explored_directions = [direction]

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _clamp_radius(self, value: float) -> float:
        return max(self.MIN_RADIUS, min(1.0, float(value)))

    def _epoch_params(self, turn_index: int) -> dict:
        """根据时代返回数值参数（从配置读取）。"""
        cfg = self.config
        if turn_index < 50:
            # 太古宙
            return {
                "growth_rate": cfg.archean_growth_rate,
                "inherit_range": (cfg.archean_inherit_min, cfg.archean_inherit_max),
                "initial_radius": cfg.archean_initial_radius,
                "mutation_chance": cfg.archean_mutation_chance,
            }
        if turn_index < 150:
            # 元古宙
            return {
                "growth_rate": cfg.proterozoic_growth_rate,
                "inherit_range": (cfg.proterozoic_inherit_min, cfg.proterozoic_inherit_max),
                "initial_radius": cfg.proterozoic_initial_radius,
                "mutation_chance": cfg.proterozoic_mutation_chance,
            }
        # 古生代及以后
        return {
            "growth_rate": cfg.phanerozoic_growth_rate,
            "inherit_range": (cfg.phanerozoic_inherit_min, cfg.phanerozoic_inherit_max),
            "initial_radius": cfg.phanerozoic_initial_radius,
            "mutation_chance": cfg.phanerozoic_mutation_chance,
        }


