from __future__ import annotations

"""
Intelligence Config - ecological intelligence module configuration.

Defines tunable ranges for AI-generated modifiers and provides a small
loader that can read overrides from a YAML file.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceConfig:
    """Configuration for the ecological intelligence module."""

    # Ranking buckets
    top_a_count: int = 5
    top_b_count: int = 15

    # Priority thresholds
    priority_threshold: float = 0.3
    death_rate_critical_threshold: float = 0.5
    death_rate_warning_threshold: float = 0.3
    population_critical_threshold: int = 100

    # Impact thresholds
    biomass_high_impact_threshold: float = 0.2

    # Weights
    risk_weight: float = 0.4
    impact_weight: float = 0.3
    potential_weight: float = 0.3

    # LLM invocation settings
    enable_llm_calls: bool = True
    use_parallel_batches: bool = True
    llm_timeout_seconds: float = 60.0

    # Modifier ranges
    mortality_mod_range: tuple[float, float] = (0.3, 1.8)
    r_adjust_range: tuple[float, float] = (-0.3, 0.3)
    k_adjust_range: tuple[float, float] = (-0.5, 0.5)
    migration_bias_range: tuple[float, float] = (-1.0, 1.0)

    # Fallback defaults when no AI assessment is available
    fallback_mortality_modifier: float = 1.0
    fallback_r_adjust: float = 0.0
    fallback_k_adjust: float = 0.0


# Default configuration instance
DEFAULT_CONFIG = IntelligenceConfig()


def load_config_from_yaml(config_path: Optional[Path] = None) -> IntelligenceConfig:
    """Load intelligence configuration from a YAML file."""
    if config_path is None:
        return DEFAULT_CONFIG

    try:
        import yaml

        if not config_path.exists():
            logger.debug(f"Config file not found: {config_path}; using defaults")
            return DEFAULT_CONFIG

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        intel_config = data.get("intelligence", data) or {}

        def _tuple(key: str, default: tuple[float, float]) -> tuple[float, float]:
            value = intel_config.get(key, default)
            try:
                left, right = value
                return float(left), float(right)
            except Exception:
                return tuple(default)

        return IntelligenceConfig(
            top_a_count=intel_config.get("top_a_count", DEFAULT_CONFIG.top_a_count),
            top_b_count=intel_config.get("top_b_count", DEFAULT_CONFIG.top_b_count),
            priority_threshold=float(intel_config.get("priority_threshold", DEFAULT_CONFIG.priority_threshold)),
            death_rate_critical_threshold=float(
                intel_config.get("death_rate_critical_threshold", DEFAULT_CONFIG.death_rate_critical_threshold)
            ),
            death_rate_warning_threshold=float(
                intel_config.get("death_rate_warning_threshold", DEFAULT_CONFIG.death_rate_warning_threshold)
            ),
            population_critical_threshold=int(
                intel_config.get("population_critical_threshold", DEFAULT_CONFIG.population_critical_threshold)
            ),
            biomass_high_impact_threshold=float(
                intel_config.get("biomass_high_impact_threshold", DEFAULT_CONFIG.biomass_high_impact_threshold)
            ),
            risk_weight=float(intel_config.get("risk_weight", DEFAULT_CONFIG.risk_weight)),
            impact_weight=float(intel_config.get("impact_weight", DEFAULT_CONFIG.impact_weight)),
            potential_weight=float(intel_config.get("potential_weight", DEFAULT_CONFIG.potential_weight)),
            enable_llm_calls=bool(intel_config.get("enable_llm_calls", DEFAULT_CONFIG.enable_llm_calls)),
            use_parallel_batches=bool(intel_config.get("use_parallel_batches", DEFAULT_CONFIG.use_parallel_batches)),
            llm_timeout_seconds=float(intel_config.get("llm_timeout_seconds", DEFAULT_CONFIG.llm_timeout_seconds)),
            mortality_mod_range=_tuple("mortality_mod_range", DEFAULT_CONFIG.mortality_mod_range),
            r_adjust_range=_tuple("r_adjust_range", DEFAULT_CONFIG.r_adjust_range),
            k_adjust_range=_tuple("k_adjust_range", DEFAULT_CONFIG.k_adjust_range),
            migration_bias_range=_tuple("migration_bias_range", DEFAULT_CONFIG.migration_bias_range),
            fallback_mortality_modifier=float(
                intel_config.get("fallback_mortality_modifier", DEFAULT_CONFIG.fallback_mortality_modifier)
            ),
            fallback_r_adjust=float(intel_config.get("fallback_r_adjust", DEFAULT_CONFIG.fallback_r_adjust)),
            fallback_k_adjust=float(intel_config.get("fallback_k_adjust", DEFAULT_CONFIG.fallback_k_adjust)),
        )
    except Exception as e:
        logger.warning(f"Failed to load intelligence config: {e}; using defaults")
        return DEFAULT_CONFIG
