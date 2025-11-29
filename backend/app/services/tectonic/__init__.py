"""板块构造演化系统

独立模块，实现基于板块运动的地形演化。

模块结构：
- models.py: 数据模型（Plate, GeologicalFeature等）
- plate_generator.py: 板块生成器（加权生长算法）
- motion_engine.py: 板块运动引擎
- geological_features.py: 地质特征分布器（火山、海沟等）
- matrix_engine.py: 矩阵计算引擎
- species_tracker.py: 物种-板块追踪器
- config.py: 配置常量

使用方式：
```python
from backend.app.services.tectonic import TectonicSystem

# 初始化系统
system = TectonicSystem(width=128, height=40, seed=12345)

# 执行一个回合
result = system.step(pressure_modifiers={"volcanic": 5})

# 获取板块信息
plates = system.get_plates()
volcanoes = system.get_volcanoes()
```
"""

from .models import (
    Plate,
    PlateType,
    BoundaryType,
    GeologicalFeature,
    FeatureType,
    TectonicEvent,
    IsolationEvent,
    ContactEvent,
    TectonicStepResult,
)
from .plate_generator import PlateGenerator
from .motion_engine import PlateMotionEngine
from .geological_features import GeologicalFeatureDistributor
from .matrix_engine import TectonicMatrixEngine
from .species_tracker import PlateSpeciesTracker
from .mantle_dynamics import MantleDynamicsEngine, WilsonPhase, MantleDynamicsState
from .tectonic_system import TectonicSystem
from .integration import TectonicIntegration, TectonicIntegrationResult, create_tectonic_integration
from .config import TECTONIC_CONFIG

__all__ = [
    # 数据模型
    "Plate",
    "PlateType",
    "BoundaryType",
    "GeologicalFeature",
    "FeatureType",
    "TectonicEvent",
    "IsolationEvent",
    "ContactEvent",
    "TectonicStepResult",
    # 核心组件
    "PlateGenerator",
    "PlateMotionEngine",
    "GeologicalFeatureDistributor",
    "TectonicMatrixEngine",
    "PlateSpeciesTracker",
    "MantleDynamicsEngine",
    "WilsonPhase",
    "MantleDynamicsState",
    "TectonicSystem",
    # 集成
    "TectonicIntegration",
    "TectonicIntegrationResult",
    "create_tectonic_integration",
    # 配置
    "TECTONIC_CONFIG",
]

