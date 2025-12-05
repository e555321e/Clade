from __future__ import annotations

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .config import TradeoffConfig


class TradeoffCalculator:
    """自动计算演化代价（能量守恒原则）。
    
    支持两种初始化方式：
    1. 传入 tradeoff_ratio（向后兼容）
    2. 传入 TradeoffConfig（完整配置）
    
    数值平衡可通过配置调整：
    - energy_costs: 各属性的能量成本权重
    - competition_map: 属性间的竞争关系
    - max_single_penalty: 单属性最大扣减量
    - penalty_parent_ratio: 从父系值扣减的最大比例
    """

    # 默认能量成本（类属性，向后兼容）
    ENERGY_COSTS = DEFAULT_ENERGY_COSTS = {
        "运动能力": 1.5,
        "智力": 2.0,
        "繁殖速度": 1.0,
        "耐寒性": 0.6,
        "耐热性": 0.6,
        "物理防御": 0.7,
        "感知能力": 1.2,
        "社会性": 0.8,
        "体型": 1.0,
    }

    # 默认竞争关系（类属性，向后兼容）
    COMPETITION_MAP = DEFAULT_COMPETITION_MAP = {
        "运动能力": ["物理防御", "体型", "繁殖速度"],
        "物理防御": ["运动能力", "繁殖速度"],
        "耐寒性": ["耐热性", "繁殖速度"],
        "耐热性": ["耐寒性", "繁殖速度"],
        "智力": ["繁殖速度", "体型"],
        "感知能力": ["繁殖速度"],
        "体型": ["运动能力", "繁殖速度"],
    }
    
    # 默认代价候选池
    DEFAULT_PENALTY_POOL = ["繁殖速度", "运动能力", "社会性"]

    def __init__(
        self,
        tradeoff_ratio: float = 0.7,
        config: "TradeoffConfig | None" = None,
    ) -> None:
        """初始化代价计算器。
        
        Args:
            tradeoff_ratio: 代价/增益比例 (0.5-1.0)，0.7 表示增加2点需要减少1.4点
            config: 完整配置（如果提供，覆盖 tradeoff_ratio）
        """
        if config is not None:
            self.tradeoff_ratio = config.tradeoff_ratio
            self.max_single_penalty = config.max_single_penalty
            self.penalty_parent_ratio = config.penalty_parent_ratio
            self.min_penalty_threshold = config.min_penalty_threshold
            self.energy_costs = dict(config.energy_costs)
            self.competition_map = {k: list(v) for k, v in config.competition_map.items()}
            self.default_penalty_pool = list(config.default_penalty_pool)
        else:
            self.tradeoff_ratio = tradeoff_ratio
            self.max_single_penalty = 2.0
            self.penalty_parent_ratio = 0.3
            self.min_penalty_threshold = 0.1
            self.energy_costs = dict(self.DEFAULT_ENERGY_COSTS)
            self.competition_map = {k: list(v) for k, v in self.DEFAULT_COMPETITION_MAP.items()}
            self.default_penalty_pool = list(self.DEFAULT_PENALTY_POOL)

    def calculate_penalties(
        self,
        gains: Dict[str, float],
        parent_traits: Dict[str, float],
    ) -> Dict[str, float]:
        """根据增益自动计算代价。
        
        Args:
            gains: LLM 给出的增益，如 {"耐寒性": +1.5}
            parent_traits: 父系当前属性值
        
        Returns:
            自动计算的代价，如 {"繁殖速度": -0.9}
        """
        exclude = set(gains.keys())
        total_gain_cost = sum(
            delta * self.energy_costs.get(trait, 1.0)
            for trait, delta in gains.items()
        )
        required_penalty = total_gain_cost * self.tradeoff_ratio

        penalty_candidates = self._get_penalty_candidates(gains, exclude)
        penalties: Dict[str, float] = {}
        remaining = required_penalty

        for trait in penalty_candidates:
            if remaining <= 0:
                break
            parent_val = parent_traits.get(trait, 5.0)
            max_reduction = min(
                parent_val * self.penalty_parent_ratio,
                self.max_single_penalty,
                remaining
            )
            if max_reduction > self.min_penalty_threshold:
                penalties[trait] = -round(max_reduction, 2)
                remaining -= max_reduction * self.energy_costs.get(trait, 1.0)

        return penalties

    def _get_penalty_candidates(self, gains: Dict[str, float], exclude: set[str]) -> list[str]:
        """根据增益属性确定代价候选。
        
        优先选择与增益属性有竞争关系的属性，然后是默认池中的属性。
        """
        candidates: list[str] = []

        # 优先：直接竞争的属性
        for gain_trait in gains.keys():
            for comp in self.competition_map.get(gain_trait, []):
                if comp not in exclude and comp not in candidates:
                    candidates.append(comp)

        # 补充：默认代价池
        for trait in self.default_penalty_pool:
            if trait not in exclude and trait not in candidates:
                candidates.append(trait)

        return candidates
    
    def get_config_summary(self) -> dict:
        """获取当前配置摘要（用于调试）"""
        return {
            "tradeoff_ratio": self.tradeoff_ratio,
            "max_single_penalty": self.max_single_penalty,
            "penalty_parent_ratio": self.penalty_parent_ratio,
            "energy_costs_count": len(self.energy_costs),
            "competition_map_count": len(self.competition_map),
        }

