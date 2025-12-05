"""
Tensor utilities and state containers.

张量计算系统的核心模块，提供：
- TensorState: 统一的张量状态容器
- SpeciationMonitor: 张量分化信号检测器
- SpeciationTrigger: 分化触发信号数据结构
- TradeoffCalculator: 自动代价计算器
- TensorConfig: 张量系统配置
- TensorMetrics: 性能监控指标
- TensorMetricsCollector: 指标收集器
- HybridCompute: NumPy + Taichi 混合计算引擎
- PressureToTensorBridge: 压力→张量桥接器
- MultiFactorMortality: 多因子死亡率计算器

分工策略：
- Taichi: 大规模并行计算（死亡率、扩散、繁殖、竞争）
- NumPy: 简单操作（聚合、筛选、掩码）
"""

from .config import TensorConfig, TensorBalanceConfig, TradeoffConfig
from .metrics import (
    TensorMetrics,
    TensorMetricsCollector,
    get_global_collector,
    reset_global_collector,
)
from .speciation_monitor import SpeciationMonitor, SpeciationTrigger
from .state import TensorState
from .tradeoff import TradeoffCalculator

# 混合计算引擎（NumPy + Taichi）
from .hybrid import HybridCompute, get_compute, reset_compute

# 压力-张量桥接
from .pressure_bridge import (
    PressureChannel,
    PressureTensorOverlay,
    PressureToTensorBridge,
    SpeciesParamsExtractor,
    MultiFactorMortality,
    PressureBridgeConfig,
    get_pressure_bridge,
    get_params_extractor,
    get_multifactor_mortality,
    reset_pressure_bridge,
)

__all__ = [
    # 核心数据结构
    "TensorState",
    "TensorConfig",
    "TensorBalanceConfig",
    "TradeoffConfig",
    # 物种形成监测
    "SpeciationMonitor",
    "SpeciationTrigger",
    # 权衡计算
    "TradeoffCalculator",
    # 性能监控
    "TensorMetrics",
    "TensorMetricsCollector",
    "get_global_collector",
    "reset_global_collector",
    # 混合计算引擎（推荐使用）
    "HybridCompute",
    "get_compute",
    "reset_compute",
    # 压力-张量桥接
    "PressureChannel",
    "PressureTensorOverlay",
    "PressureToTensorBridge",
    "SpeciesParamsExtractor",
    "MultiFactorMortality",
    "PressureBridgeConfig",
    "get_pressure_bridge",
    "get_params_extractor",
    "get_multifactor_mortality",
    "reset_pressure_bridge",
]
