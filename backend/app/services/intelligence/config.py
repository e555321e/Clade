"""
Intelligence Config - 生态智能配置

定义智能体的配置参数。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceConfig:
    """生态智能配置类
    
    控制物种评分、分档和优先级计算的参数。
    """
    
    # 分档数量配置
    top_a_count: int = 5  # A档（高优先级）物种数量
    top_b_count: int = 15  # B档（中优先级）物种数量
    
    # 优先级阈值
    priority_threshold: float = 0.3  # 进入 B 档的最低优先级阈值
    
    # 风险评分阈值
    death_rate_critical_threshold: float = 0.5  # 死亡率临界阈值
    death_rate_warning_threshold: float = 0.3  # 死亡率警告阈值
    population_critical_threshold: int = 100  # 种群数量临界阈值
    
    # 影响评分阈值
    biomass_high_impact_threshold: float = 0.2  # 高影响生物量占比阈值
    
    # 加权参数
    risk_weight: float = 0.4  # 风险权重
    impact_weight: float = 0.3  # 影响权重
    potential_weight: float = 0.3  # 潜力权重
    
    # LLM 调用配置
    enable_llm_calls: bool = True  # 是否启用 LLM 调用
    use_parallel_batches: bool = True  # 是否并行执行 A/B 批次
    llm_timeout_seconds: float = 60.0  # LLM 调用超时时间（秒）


# 默认配置实例
DEFAULT_CONFIG = IntelligenceConfig()


def load_config_from_yaml(config_path: Optional[Path] = None) -> IntelligenceConfig:
    """从 YAML 文件加载配置
    
    Args:
        config_path: 配置文件路径，如果为 None 则返回默认配置
        
    Returns:
        IntelligenceConfig 实例
    """
    if config_path is None:
        return DEFAULT_CONFIG
    
    try:
        import yaml
        
        if not config_path.exists():
            logger.debug(f"配置文件不存在: {config_path}，使用默认配置")
            return DEFAULT_CONFIG
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        # 提取 intelligence 配置部分
        intel_config = data.get('intelligence', data)
        
        return IntelligenceConfig(
            top_a_count=intel_config.get('top_a_count', DEFAULT_CONFIG.top_a_count),
            top_b_count=intel_config.get('top_b_count', DEFAULT_CONFIG.top_b_count),
            priority_threshold=intel_config.get('priority_threshold', DEFAULT_CONFIG.priority_threshold),
            death_rate_critical_threshold=intel_config.get('death_rate_critical_threshold', DEFAULT_CONFIG.death_rate_critical_threshold),
            death_rate_warning_threshold=intel_config.get('death_rate_warning_threshold', DEFAULT_CONFIG.death_rate_warning_threshold),
            population_critical_threshold=intel_config.get('population_critical_threshold', DEFAULT_CONFIG.population_critical_threshold),
            biomass_high_impact_threshold=intel_config.get('biomass_high_impact_threshold', DEFAULT_CONFIG.biomass_high_impact_threshold),
            risk_weight=intel_config.get('risk_weight', DEFAULT_CONFIG.risk_weight),
            impact_weight=intel_config.get('impact_weight', DEFAULT_CONFIG.impact_weight),
            potential_weight=intel_config.get('potential_weight', DEFAULT_CONFIG.potential_weight),
            enable_llm_calls=intel_config.get('enable_llm_calls', DEFAULT_CONFIG.enable_llm_calls),
            use_parallel_batches=intel_config.get('use_parallel_batches', DEFAULT_CONFIG.use_parallel_batches),
            llm_timeout_seconds=intel_config.get('llm_timeout_seconds', DEFAULT_CONFIG.llm_timeout_seconds),
        )
    except Exception as e:
        logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        return DEFAULT_CONFIG
