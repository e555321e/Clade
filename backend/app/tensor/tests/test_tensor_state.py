"""
TensorState 和 TensorConfig 单元测试

测试张量状态容器和配置类的核心功能。
"""

import numpy as np
import pytest

from ..config import TensorConfig
from ..state import TensorState


class TestTensorState:
    """TensorState 测试套件"""
    
    @pytest.fixture
    def basic_state(self) -> TensorState:
        """创建基本的 TensorState"""
        return TensorState(
            env=np.zeros((5, 10, 10), dtype=np.float32),
            pop=np.zeros((3, 10, 10), dtype=np.float32),
            species_params=np.zeros((3, 8), dtype=np.float32),
            masks={"land": np.ones((10, 10), dtype=bool)},
            species_map={"SP001": 0, "SP002": 1, "SP003": 2},
        )
    
    def test_population_slice_existing(self, basic_state: TensorState):
        """测试获取存在的物种切片"""
        # 设置一些数据
        basic_state.pop[0, 2:5, 2:5] = 100.0
        
        slice_ = basic_state.population_slice("SP001")
        
        assert slice_ is not None
        assert slice_.shape == (10, 10)
        assert slice_[3, 3] == 100.0
    
    def test_population_slice_nonexistent(self, basic_state: TensorState):
        """测试获取不存在的物种切片"""
        slice_ = basic_state.population_slice("INVALID")
        
        assert slice_ is None
    
    def test_ensure_shapes_valid(self, basic_state: TensorState):
        """测试有效形状检查"""
        # 不应抛出异常
        basic_state.ensure_shapes()
    
    def test_ensure_shapes_invalid_env(self):
        """测试无效环境张量形状"""
        state = TensorState(
            env=np.zeros((10, 10), dtype=np.float32),  # 2D 而不是 3D
            pop=np.zeros((3, 10, 10), dtype=np.float32),
            species_params=np.zeros((3, 8), dtype=np.float32),
        )
        
        with pytest.raises(ValueError, match="env tensor must be 3D"):
            state.ensure_shapes()
    
    def test_ensure_shapes_invalid_pop(self):
        """测试无效种群张量形状"""
        state = TensorState(
            env=np.zeros((5, 10, 10), dtype=np.float32),
            pop=np.zeros((10, 10), dtype=np.float32),  # 2D 而不是 3D
            species_params=np.zeros((3, 8), dtype=np.float32),
        )
        
        with pytest.raises(ValueError, match="pop tensor must be 3D"):
            state.ensure_shapes()
    
    def test_ensure_shapes_invalid_params(self):
        """测试无效参数矩阵形状"""
        state = TensorState(
            env=np.zeros((5, 10, 10), dtype=np.float32),
            pop=np.zeros((3, 10, 10), dtype=np.float32),
            species_params=np.zeros((3,), dtype=np.float32),  # 1D 而不是 2D
        )
        
        with pytest.raises(ValueError, match="species_params must be 2D"):
            state.ensure_shapes()
    
    def test_species_map_indexing(self, basic_state: TensorState):
        """测试物种映射索引"""
        assert basic_state.species_map["SP001"] == 0
        assert basic_state.species_map["SP002"] == 1
        assert basic_state.species_map["SP003"] == 2


class TestTensorConfig:
    """TensorConfig 测试套件"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = TensorConfig.default()
        
        assert config.use_tensor_mortality is True
        assert config.use_tensor_speciation is True
        assert config.use_auto_tradeoff is True
        assert config.tradeoff_ratio == 0.7
        assert config.divergence_threshold == 0.5
    
    def test_disabled_config(self):
        """测试禁用配置"""
        config = TensorConfig.disabled()
        
        assert config.use_tensor_mortality is False
        assert config.use_tensor_speciation is False
        assert config.use_auto_tradeoff is False
    
    def test_is_any_enabled_true(self):
        """测试至少一项启用"""
        config = TensorConfig(
            use_tensor_mortality=True,
            use_tensor_speciation=False,
            use_auto_tradeoff=False,
        )
        
        assert config.is_any_enabled() is True
    
    def test_is_any_enabled_false(self):
        """测试全部禁用"""
        config = TensorConfig.disabled()
        
        assert config.is_any_enabled() is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        from ..config import TensorBalanceConfig, TradeoffConfig
        
        balance = TensorBalanceConfig(divergence_threshold=0.6)
        tradeoff = TradeoffConfig(tradeoff_ratio=0.8)
        config = TensorConfig(
            use_tensor_mortality=True,
            use_tensor_speciation=False,
            use_auto_tradeoff=True,
            balance=balance,
            tradeoff=tradeoff,
        )
        
        d = config.to_dict()
        
        assert d["use_tensor_mortality"] is True
        assert d["use_tensor_speciation"] is False
        assert d["use_auto_tradeoff"] is True
        assert d["tradeoff"]["tradeoff_ratio"] == 0.8
        assert d["balance"]["divergence_threshold"] == 0.6
    
    def test_custom_tradeoff_ratio(self):
        """测试自定义代价比例"""
        from ..config import TradeoffConfig
        
        tradeoff = TradeoffConfig(tradeoff_ratio=0.5)
        config = TensorConfig(tradeoff=tradeoff)
        
        assert config.tradeoff_ratio == 0.5
    
    def test_custom_divergence_threshold(self):
        """测试自定义分歧阈值"""
        from ..config import TensorBalanceConfig
        
        balance = TensorBalanceConfig(divergence_threshold=0.8)
        config = TensorConfig(balance=balance)
        
        assert config.divergence_threshold == 0.8

