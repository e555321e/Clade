"""休眠基因激活服务

基于 Embedding 的基因激活机制：
- 使用 GeneDiversityService 判断压力方向是否在可达半径内
- 压力匹配时激活概率加成
- 所有参数从 GeneDiversityConfig 读取

【重构说明】
- GeneLibraryService 已废弃，保留仅用于旧数据兼容
- 新激活逻辑完全基于 GeneDiversityService.is_reachable()
- dormant_genes 字段逐步废弃，激活判断改用 Embedding 距离
"""
from __future__ import annotations

import logging
import random
import warnings
from typing import TYPE_CHECKING

from ...models.species import Species
from .gene_diversity import GeneDiversityService
from .trait_config import TraitConfig

if TYPE_CHECKING:
    from ...models.config import GeneDiversityConfig
    from .gene_library import GeneLibraryService

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


class GeneActivationService:
    """处理物种休眠基因的激活
    
    【Embedding 集成】
    - 使用 GeneDiversityService 的 is_reachable() 判断压力方向是否在可达范围内
    - 压力匹配时应用 pressure_match_bonus 加成（默认 ×2）
    - 激活后消耗半径（通过 consume_on_activation）
    """
    
    def __init__(self, embedding_service=None, gene_diversity_service: GeneDiversityService | None = None):
        # [DEPRECATED] GeneLibraryService 惰性初始化，仅用于旧存档兼容
        self._gene_library_service: "GeneLibraryService | None" = None
        # 可选的 Embedding 服务用于距离判断
        self.embedding = embedding_service
        self.gene_diversity = gene_diversity_service or GeneDiversityService(embedding_service)
        self._config: "GeneDiversityConfig | None" = None
    
    @property
    def gene_library_service(self) -> "GeneLibraryService":
        """[DEPRECATED] 惰性加载 GeneLibraryService，仅用于旧存档兼容"""
        if self._gene_library_service is None:
            warnings.warn(
                "GeneLibraryService 已废弃，请迁移到 GeneDiversityService",
                DeprecationWarning,
                stacklevel=2
            )
            from .gene_library import GeneLibraryService
            self._gene_library_service = GeneLibraryService()
        return self._gene_library_service
    
    @property
    def config(self) -> "GeneDiversityConfig":
        """懒加载配置"""
        if self._config is None:
            self._config = _load_gene_diversity_config()
        if self._config is None:
            from ...models.config import GeneDiversityConfig
            self._config = GeneDiversityConfig()
        return self._config
    
    def check_and_activate(
        self,
        species: Species,
        death_rate: float,
        pressure_type: str,
        turn: int
    ) -> dict:
        """检查并激活休眠基因
        
        Returns:
            激活结果字典 {"traits": [...], "organs": [...]}
        """
        # 确保新字段初始化
        try:
            self.gene_diversity.ensure_initialized(species)
        except Exception:
            pass

        if not species.dormant_genes:
            return {"traits": [], "organs": []}
        
        activated = {"traits": [], "organs": []}
        
        if not species.stress_exposure:
            species.stress_exposure = {}
        
        species.stress_exposure.setdefault(pressure_type, {"count": 0, "max_death_rate": 0.0})
        species.stress_exposure[pressure_type]["count"] += 1
        species.stress_exposure[pressure_type]["max_death_rate"] = max(
            species.stress_exposure[pressure_type]["max_death_rate"],
            death_rate
        )
        
        activated_traits = self._check_trait_activation(species, death_rate, pressure_type, turn)
        activated_organs = self._check_organ_activation(species, death_rate, pressure_type, turn)
        
        activated["traits"] = activated_traits
        activated["organs"] = activated_organs
        
        return activated
    
    def _check_trait_activation(
        self,
        species: Species,
        death_rate: float,
        pressure_type: str,
        turn: int
    ) -> list[str]:
        """检查特质激活
        
        【大幅降低门槛版本】
        - 死亡率阈值从配置读取（默认25%）
        - 暴露次数从配置读取（默认1次）
        - 激活概率大幅提升（默认30%）
        """
        activated = []
        
        if "traits" not in species.dormant_genes:
            return activated
        
        # 获取配置参数
        cfg = self.config
        base_activation_chance = cfg.activation_chance_per_turn  # 30%
        pressure_match_bonus = cfg.pressure_match_bonus  # ×2.5
        death_rate_threshold = getattr(cfg, 'activation_death_rate_threshold', 0.25)  # 25%
        min_exposure = getattr(cfg, 'activation_min_exposure', 1)  # 1次
        
        reachable = self._is_reachable(species, pressure_type)

        for trait_name, gene_data in species.dormant_genes["traits"].items():
            if gene_data.get("activated", False):
                continue
            
            # 压力匹配检查 - 任何压力都增加暴露计数
            gene_data["exposure_count"] = gene_data.get("exposure_count", 0) + 1
            pressure_matched = pressure_type in gene_data.get("pressure_types", [])
            
            exposure_count = gene_data.get("exposure_count", 0)
            evolution_potential = species.hidden_traits.get("evolution_potential", 0.5)
            
            # 计算激活概率：基础概率 × (1 + 演化潜力) × 压力匹配加成
            # 演化潜力作为加成而非乘数，确保基础概率不会过低
            activation_prob = base_activation_chance * (1.0 + evolution_potential)
            if pressure_matched:
                activation_prob *= pressure_match_bonus
            
            # 降低门槛：死亡率25%+，暴露1次+
            if (death_rate > death_rate_threshold and
                exposure_count >= min_exposure and
                reachable and
                random.random() < activation_prob):
                
                potential_value = gene_data.get("potential_value", 8.0)
                test_traits = dict(species.abstract_traits)
                test_traits[trait_name] = TraitConfig.clamp_trait(potential_value)
                
                valid, error_msg = TraitConfig.validate_traits_with_trophic(
                    test_traits, species.trophic_level
                )
                
                if valid:
                    species.abstract_traits[trait_name] = TraitConfig.clamp_trait(potential_value)
                    gene_data["activated"] = True
                    gene_data["activation_turn"] = turn
                    activated.append(trait_name)
                    try:
                        self.gene_diversity.consume_on_activation(species)
                        self.gene_diversity.record_direction(species, self._direction_id(pressure_type))
                    except Exception:
                        pass
                    
                    logger.info(f"[基因激活] {species.common_name} 激活特质: {trait_name} = {potential_value:.1f}")
                    
                    if species.genus_code:
                        self.gene_library_service.update_activation_count(
                            species.genus_code, trait_name, "traits"
                        )
                else:
                    logger.warning(f"[基因激活] {species.common_name} 激活{trait_name}失败: {error_msg}")
        
        return activated
    
    def _check_organ_activation(
        self,
        species: Species,
        death_rate: float,
        pressure_type: str,
        turn: int
    ) -> list[str]:
        """检查器官激活
        
        【大幅降低门槛版本】
        - 器官激活门槛与特质相近
        - 新器官发现概率大幅提升（默认20%）
        """
        activated = []
        
        if "organs" not in species.dormant_genes:
            return activated
        
        # 获取配置参数
        cfg = self.config
        organ_discovery_chance = cfg.organ_discovery_chance  # 20%
        pressure_match_bonus = cfg.pressure_match_bonus  # ×2.5
        death_rate_threshold = getattr(cfg, 'activation_death_rate_threshold', 0.25) + 0.05  # 器官略高30%
        min_exposure = getattr(cfg, 'activation_min_exposure', 1)  # 1次
        
        reachable = self._is_reachable(species, pressure_type)

        for organ_name, gene_data in species.dormant_genes["organs"].items():
            if gene_data.get("activated", False):
                continue
            
            # 任何压力都增加暴露计数
            gene_data["exposure_count"] = gene_data.get("exposure_count", 0) + 1
            pressure_matched = pressure_type in gene_data.get("pressure_types", [])
            
            exposure_count = gene_data.get("exposure_count", 0)
            evolution_potential = species.hidden_traits.get("evolution_potential", 0.5)
            
            # 计算激活概率：器官发现概率 × (1 + 演化潜力 × 2) × 压力匹配加成
            activation_prob = organ_discovery_chance * (1.0 + evolution_potential * 2)
            if pressure_matched:
                activation_prob *= pressure_match_bonus
            
            # 降低门槛：死亡率30%+，暴露1次+
            if (death_rate > death_rate_threshold and
                exposure_count >= min_exposure and
                reachable and
                random.random() < activation_prob):
                
                organ_data = gene_data.get("organ_data", {})
                organ_category = organ_data.get("category", "sensory")
                
                species.organs[organ_category] = {
                    "type": organ_data.get("type", organ_name),
                    "parameters": organ_data.get("parameters", {}),
                    "acquired_turn": turn,
                    "is_active": True
                }
                gene_data["activated"] = True
                gene_data["activation_turn"] = turn
                activated.append(organ_name)
                try:
                    self.gene_diversity.consume_on_activation(species)
                    self.gene_diversity.record_direction(species, self._direction_id(pressure_type))
                except Exception:
                    pass
                
                logger.info(f"[基因激活] {species.common_name} 激活器官: {organ_name} ({organ_category})")
                
                if species.genus_code:
                    self.gene_library_service.update_activation_count(
                        species.genus_code, organ_name, "organs"
                    )
        
        return activated
    
    def batch_check(self, species_list: list[Species], mortality_results: list, turn: int):
        """批量检查物种的基因激活"""
        activation_events = []
        
        mortality_map = {}
        for r in mortality_results:
            if isinstance(r, dict):
                code = r.get("lineage_code")
            else:
                code = r.species.lineage_code
            if code:
                mortality_map[code] = r
        
        for species in species_list:
            if species.lineage_code not in mortality_map:
                continue
            
            result = mortality_map[species.lineage_code]
            
            if isinstance(result, dict):
                death_rate = result.get("death_rate", 0.0)
            else:
                death_rate = result.death_rate
            
            # 降低门槛：只要有死亡就检查激活（之前是50%）
            if death_rate < 0.1:
                continue
            
            pressure_type = self._infer_pressure_type(result)
            
            activated = self.check_and_activate(species, death_rate, pressure_type, turn)
            
            if activated["traits"] or activated["organs"]:
                activation_events.append({
                    "lineage_code": species.lineage_code,
                    "common_name": species.common_name,
                    "activated_traits": activated["traits"],
                    "activated_organs": activated["organs"],
                    "death_rate": death_rate
                })
        
        return activation_events
    
    def _infer_pressure_type(self, mortality_result) -> str:
        """从死亡率结果推断压力类型"""
        # 处理 dataclass 对象
        if not isinstance(mortality_result, dict):
            # 如果是 MortalityResult 对象，它可能没有 pressure_breakdown 字段
            # 这里的逻辑需要检查 MortalityResult 定义
            return "adaptive"

        if "pressure_breakdown" in mortality_result:
            breakdown = mortality_result["pressure_breakdown"]
            if breakdown.get("temperature", 0) > 0.3:
                return "temperature"
            if breakdown.get("humidity", 0) > 0.3:
                return "drought"
            if breakdown.get("resource_competition", 0) > 0.3:
                return "competition"
        
        return "adaptive"

    # ------------------------------------------------------------------ #
    # Embedding/可达性辅助
    # ------------------------------------------------------------------ #
    def _is_reachable(self, species: Species, pressure_type: str) -> bool:
        """基于 Embedding 判断该压力方向是否在可达半径内。"""
        try:
            radius = getattr(species, "gene_diversity_radius", None)
            if radius is None:
                self.gene_diversity.ensure_initialized(species)
                radius = species.gene_diversity_radius

            target_vec = self.gene_diversity.get_pressure_vector(pressure_type)
            return self.gene_diversity.is_reachable(
                species.ecological_vector, target_vec, radius
            )
        except Exception:
            return True

    def _direction_id(self, pressure_type: str) -> int:
        """使用稳定哈希把压力类型映射为方向索引。"""
        return abs(hash(pressure_type)) % 10_000

