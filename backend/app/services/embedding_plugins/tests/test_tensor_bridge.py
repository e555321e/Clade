"""张量桥接器测试"""
import pytest
import numpy as np
from unittest.mock import MagicMock

from ..tensor_bridge import (
    TensorEmbeddingBridge,
    TensorSpeciesDistribution,
    TensorEnvironmentProfile,
    TensorSpeciationSignal,
    get_tensor_bridge,
    reset_tensor_bridge,
)


@pytest.fixture
def mock_tensor_state():
    """创建模拟的TensorState"""
    from dataclasses import dataclass, field
    from typing import Dict
    
    @dataclass
    class MockTensorState:
        env: np.ndarray
        pop: np.ndarray
        species_params: np.ndarray
        masks: Dict[str, np.ndarray] = field(default_factory=dict)
        species_map: Dict[str, int] = field(default_factory=dict)
    
    # 创建 (3, 1, 5) 的张量 - 3个物种，1行（线性化），5个地块
    pop = np.array([
        [[100, 50, 0, 200, 0]],    # 物种0: 在地块0,1,3有分布
        [[0, 80, 120, 0, 0]],      # 物种1: 在地块1,2有分布
        [[30, 0, 0, 0, 60]],       # 物种2: 在地块0,4有分布（分离种群）
    ], dtype=np.float32)
    
    # 环境张量 (5通道, 1, 5地块)
    env = np.array([
        [[100, 200, 500, 300, 150]],    # 海拔
        [[20, 25, 15, 30, 10]],          # 温度
        [[500, 800, 1200, 400, 600]],    # 降水
        [[45, 45, 45, 45, 45]],          # 纬度
        [[0.5, 0.7, 0.9, 0.3, 0.6]],     # 植被
    ], dtype=np.float32)
    
    species_map = {
        "SP001": 0,
        "SP002": 1,
        "SP003": 2,
    }
    
    return MockTensorState(
        env=env,
        pop=pop,
        species_params=np.zeros((3, 5), dtype=np.float32),
        species_map=species_map,
    )


@pytest.fixture
def mock_context(mock_tensor_state):
    """创建模拟的SimulationContext"""
    ctx = MagicMock()
    ctx.tensor_state = mock_tensor_state
    ctx.tensor_trigger_codes = {"SP003"}  # SP003有分化信号
    ctx.all_tiles = [
        {"id": "0", "x": 0, "y": 0},
        {"id": "1", "x": 1, "y": 0},
        {"id": "2", "x": 2, "y": 0},
        {"id": "3", "x": 3, "y": 0},
        {"id": "4", "x": 4, "y": 0},
    ]
    return ctx


class TestTensorEmbeddingBridge:
    """张量桥接器测试"""
    
    def test_sync_from_context(self, mock_context):
        """测试从上下文同步"""
        bridge = TensorEmbeddingBridge()
        
        success = bridge.sync_from_context(mock_context)
        
        assert success is True
        assert bridge.is_synced is True
    
    def test_sync_without_tensor_state(self):
        """测试无张量数据时的同步"""
        ctx = MagicMock()
        ctx.tensor_state = None
        ctx.all_tiles = []
        
        bridge = TensorEmbeddingBridge()
        success = bridge.sync_from_context(ctx)
        
        assert success is False
        assert bridge.is_synced is False
    
    def test_get_species_distribution(self, mock_context):
        """测试获取物种分布"""
        bridge = TensorEmbeddingBridge()
        bridge.sync_from_context(mock_context)
        
        dist = bridge.get_species_distribution("SP001")
        
        assert dist is not None
        assert dist.lineage_code == "SP001"
        assert dist.total_population == 350  # 100+50+200
        assert len(dist.occupied_tiles) == 3  # 地块0,1,3
        assert "0" in dist.tile_populations
        assert dist.tile_populations["0"] == 100
    
    def test_get_tile_species_codes(self, mock_context):
        """测试获取地块物种列表"""
        bridge = TensorEmbeddingBridge()
        bridge.sync_from_context(mock_context)
        
        # 地块1有SP001和SP002
        codes = bridge.get_tile_species_codes("1")
        assert "SP001" in codes
        assert "SP002" in codes
        assert len(codes) == 2
        
        # 地块3只有SP001
        codes = bridge.get_tile_species_codes("3")
        assert codes == ["SP001"]
    
    def test_has_speciation_signal(self, mock_context):
        """测试分化信号检测"""
        bridge = TensorEmbeddingBridge()
        bridge.sync_from_context(mock_context)
        
        # SP003有分化信号（在mock_context.tensor_trigger_codes中）
        assert bridge.has_speciation_signal("SP003") is True
        
        # 获取所有分化信号
        signals = bridge.get_speciation_signals()
        # 至少应该有SP003的信号
        signal_codes = [s.lineage_code for s in signals]
        assert "SP003" in signal_codes
    
    def test_to_legacy_species_distribution(self, mock_context):
        """测试转换为旧格式"""
        bridge = TensorEmbeddingBridge()
        bridge.sync_from_context(mock_context)
        
        legacy = bridge.to_legacy_species_distribution()
        
        # 地块0有SP001和SP003
        assert "0" in legacy
        assert "SP001" in legacy["0"]
        assert "SP003" in legacy["0"]
        
        # 地块4只有SP003
        assert "4" in legacy
        assert legacy["4"] == ["SP003"]
    
    def test_get_summary(self, mock_context):
        """测试获取摘要"""
        bridge = TensorEmbeddingBridge()
        bridge.sync_from_context(mock_context)
        
        summary = bridge.get_summary()
        
        assert summary["synced"] is True
        assert summary["species_count"] == 3
        assert summary["tile_count"] == 5
        assert summary["speciation_signals"] >= 1
        assert summary["total_population"] == 640  # 350+200+90


class TestGlobalBridge:
    """全局桥接器测试"""
    
    def test_global_bridge_singleton(self):
        """测试全局桥接器单例"""
        reset_tensor_bridge()
        
        bridge1 = get_tensor_bridge()
        bridge2 = get_tensor_bridge()
        
        assert bridge1 is bridge2
    
    def test_reset_bridge(self):
        """测试重置桥接器"""
        bridge1 = get_tensor_bridge()
        reset_tensor_bridge()
        bridge2 = get_tensor_bridge()
        
        assert bridge1 is not bridge2


class TestDistributionEntropy:
    """分布熵计算测试"""
    
    def test_entropy_calculation(self, mock_context):
        """测试分布均匀度计算"""
        bridge = TensorEmbeddingBridge()
        bridge.sync_from_context(mock_context)
        
        # SP002只在两个地块有分布，熵应该较高（均匀）
        dist_sp002 = bridge.get_species_distribution("SP002")
        assert dist_sp002 is not None
        
        # SP001在三个地块有分布，但不均匀（200在地块3）
        dist_sp001 = bridge.get_species_distribution("SP001")
        assert dist_sp001 is not None
        
        # 两者都有有效的熵值
        assert 0 <= dist_sp001.distribution_entropy <= 1
        assert 0 <= dist_sp002.distribution_entropy <= 1

