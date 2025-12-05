"""
SpeciationMonitor 单元测试

测试张量分化监控器的核心功能：
- 地理隔离检测 (detect_isolation)
- 环境分歧检测 (detect_divergence)
- 分化触发信号聚合 (get_speciation_triggers)
"""

import numpy as np
import pytest

from ..speciation_monitor import SpeciationMonitor, SpeciationTrigger
from ..state import TensorState


class TestDetectIsolation:
    """地理隔离检测测试"""
    
    @pytest.fixture
    def species_map(self) -> dict[str, int]:
        """两个物种的映射"""
        return {"SP001": 0, "SP002": 1}
    
    @pytest.fixture
    def monitor(self, species_map) -> SpeciationMonitor:
        """创建监控器"""
        return SpeciationMonitor(species_map)
    
    def test_single_connected_region(self, monitor: SpeciationMonitor):
        """测试单一连通区域（无隔离）"""
        # 创建 2x10x10 的种群张量
        pop_tensor = np.zeros((2, 10, 10), dtype=np.float32)
        
        # 物种0: 一个连通区域
        pop_tensor[0, 2:5, 2:5] = 100.0
        
        isolation = monitor.detect_isolation(pop_tensor)
        
        # 单一连通区域不应触发隔离
        assert "SP001" not in isolation
    
    def test_two_isolated_regions(self, monitor: SpeciationMonitor):
        """测试两个隔离区域"""
        pop_tensor = np.zeros((2, 10, 10), dtype=np.float32)
        
        # 物种0: 两个分离的区域
        pop_tensor[0, 1:3, 1:3] = 100.0  # 左上角
        pop_tensor[0, 7:9, 7:9] = 100.0  # 右下角
        
        isolation = monitor.detect_isolation(pop_tensor)
        
        # 应该检测到隔离
        assert "SP001" in isolation
        assert len(isolation["SP001"]) == 2
    
    def test_diagonal_not_connected(self, monitor: SpeciationMonitor):
        """测试对角线不视为连通"""
        pop_tensor = np.zeros((2, 10, 10), dtype=np.float32)
        
        # 物种0: 对角线相邻（但不直接连通）
        pop_tensor[0, 2, 2] = 100.0
        pop_tensor[0, 3, 3] = 100.0
        
        isolation = monitor.detect_isolation(pop_tensor)
        
        # scipy.ndimage.label 默认使用4连通，对角线不连通
        assert "SP001" in isolation
        assert len(isolation["SP001"]) == 2
    
    def test_multiple_species(self, monitor: SpeciationMonitor):
        """测试多物种同时检测"""
        pop_tensor = np.zeros((2, 10, 10), dtype=np.float32)
        
        # 物种0: 两个隔离区域
        pop_tensor[0, 1:3, 1:3] = 100.0
        pop_tensor[0, 7:9, 7:9] = 100.0
        
        # 物种1: 单一连通区域
        pop_tensor[1, 4:7, 4:7] = 50.0
        
        isolation = monitor.detect_isolation(pop_tensor)
        
        # 物种0有隔离，物种1没有
        assert "SP001" in isolation
        assert "SP002" not in isolation
    
    def test_empty_population(self, monitor: SpeciationMonitor):
        """测试空种群"""
        pop_tensor = np.zeros((2, 10, 10), dtype=np.float32)
        
        isolation = monitor.detect_isolation(pop_tensor)
        
        # 空种群不应触发隔离
        assert len(isolation) == 0


class TestDetectDivergence:
    """环境分歧检测测试"""
    
    @pytest.fixture
    def species_map(self) -> dict[str, int]:
        return {"SP001": 0, "SP002": 1}
    
    @pytest.fixture
    def monitor(self, species_map) -> SpeciationMonitor:
        return SpeciationMonitor(species_map)
    
    def test_uniform_environment(self, monitor: SpeciationMonitor):
        """测试均匀环境（低分歧）"""
        # 环境张量: 3通道 (温度、湿度、海拔)
        env_tensor = np.ones((3, 10, 10), dtype=np.float32)
        env_tensor[0] = 25.0  # 温度
        env_tensor[1] = 0.5   # 湿度
        env_tensor[2] = 100.0 # 海拔
        
        # 种群张量
        pop_tensor = np.zeros((2, 10, 10), dtype=np.float32)
        pop_tensor[0, 2:8, 2:8] = 100.0  # 物种0分布
        
        divergence = monitor.detect_divergence(pop_tensor, env_tensor)
        
        # 均匀环境应该有低分歧
        assert "SP001" in divergence
        assert divergence["SP001"] < 0.1
    
    def test_high_environmental_variance(self, monitor: SpeciationMonitor):
        """测试高环境差异（高分歧）"""
        env_tensor = np.zeros((3, 10, 10), dtype=np.float32)
        
        # 创建明显的环境梯度
        for i in range(10):
            env_tensor[0, i, :] = i * 5.0  # 温度从0到45度
            env_tensor[1, i, :] = i * 0.1  # 湿度从0到0.9
            env_tensor[2, i, :] = i * 100  # 海拔从0到900米
        
        # 种群跨越整个环境梯度
        pop_tensor = np.zeros((2, 10, 10), dtype=np.float32)
        pop_tensor[0, :, :] = 100.0  # 物种0分布在整个区域
        
        divergence = monitor.detect_divergence(pop_tensor, env_tensor)
        
        # 高环境差异应该有高分歧
        assert "SP001" in divergence
        assert divergence["SP001"] > 0.1
    
    def test_empty_population_divergence(self, monitor: SpeciationMonitor):
        """测试空种群的分歧"""
        env_tensor = np.ones((3, 10, 10), dtype=np.float32)
        pop_tensor = np.zeros((2, 10, 10), dtype=np.float32)
        
        divergence = monitor.detect_divergence(pop_tensor, env_tensor)
        
        # 空种群不应有分歧得分
        assert "SP001" not in divergence
        assert "SP002" not in divergence


class TestGetSpeciationTriggers:
    """分化触发信号聚合测试"""
    
    @pytest.fixture
    def tensor_state(self) -> TensorState:
        """创建测试用 TensorState"""
        env = np.zeros((3, 10, 10), dtype=np.float32)
        # 创建环境梯度
        for i in range(10):
            env[0, i, :] = i * 3.0
        
        pop = np.zeros((2, 10, 10), dtype=np.float32)
        # 物种0: 两个隔离区域
        pop[0, 1:3, 1:3] = 100.0
        pop[0, 7:9, 7:9] = 100.0
        
        # 物种1: 单一区域但跨越环境梯度
        pop[1, :, 4:6] = 50.0
        
        species_params = np.zeros((2, 5), dtype=np.float32)
        
        return TensorState(
            env=env,
            pop=pop,
            species_params=species_params,
            masks={},
            species_map={"SP001": 0, "SP002": 1},
        )
    
    def test_get_all_triggers(self, tensor_state: TensorState):
        """测试获取所有触发信号"""
        monitor = SpeciationMonitor(tensor_state.species_map)
        
        triggers = monitor.get_speciation_triggers(tensor_state, threshold=0.1)
        
        # 应该有触发信号
        assert len(triggers) > 0
        
        # 检查触发类型
        trigger_types = {t.type for t in triggers}
        assert "geographic_isolation" in trigger_types
    
    def test_high_threshold_filters_divergence(self):
        """测试高阈值过滤分歧触发"""
        # 创建环境差异较小的测试数据
        env = np.ones((3, 10, 10), dtype=np.float32) * 5.0  # 均匀环境
        # 只在边缘有微小差异
        env[0, 0, :] = 4.5
        env[0, 9, :] = 5.5
        
        pop = np.zeros((2, 10, 10), dtype=np.float32)
        pop[0, 2:8, 2:8] = 100.0  # 物种0分布在中心区域（环境均匀）
        
        species_params = np.zeros((2, 5), dtype=np.float32)
        
        tensor_state = TensorState(
            env=env,
            pop=pop,
            species_params=species_params,
            masks={},
            species_map={"SP001": 0, "SP002": 1},
        )
        
        monitor = SpeciationMonitor(tensor_state.species_map)
        
        # 使用很高的阈值
        triggers = monitor.get_speciation_triggers(tensor_state, threshold=0.99)
        
        # 不应该有生态分歧触发（环境差异太小，阈值太高）
        eco_triggers = [t for t in triggers if t.type == "ecological_divergence"]
        assert len(eco_triggers) == 0
    
    def test_trigger_contains_required_fields(self, tensor_state: TensorState):
        """测试触发信号包含必要字段"""
        monitor = SpeciationMonitor(tensor_state.species_map)
        triggers = monitor.get_speciation_triggers(tensor_state)
        
        for trigger in triggers:
            assert trigger.lineage_code is not None
            assert trigger.type is not None
            
            if trigger.type == "geographic_isolation":
                assert trigger.num_regions is not None
                assert trigger.num_regions >= 2
            
            if trigger.type == "ecological_divergence":
                assert trigger.divergence_score is not None
                assert 0 <= trigger.divergence_score <= 1.0


class TestSpeciationTriggerDataclass:
    """SpeciationTrigger 数据类测试"""
    
    def test_create_isolation_trigger(self):
        """测试创建隔离触发"""
        trigger = SpeciationTrigger(
            lineage_code="SP001",
            type="geographic_isolation",
            num_regions=3,
            regions=[np.array([[True, False], [False, True]])] * 3,
        )
        
        assert trigger.lineage_code == "SP001"
        assert trigger.type == "geographic_isolation"
        assert trigger.num_regions == 3
    
    def test_create_divergence_trigger(self):
        """测试创建分歧触发"""
        trigger = SpeciationTrigger(
            lineage_code="SP002",
            type="ecological_divergence",
            divergence_score=0.75,
        )
        
        assert trigger.lineage_code == "SP002"
        assert trigger.type == "ecological_divergence"
        assert trigger.divergence_score == 0.75

