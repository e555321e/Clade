"""
张量阶段单元测试

测试张量计算阶段的功能和与管线的集成。
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch

# 标记整个模块使用 asyncio
pytestmark = pytest.mark.asyncio

from ..tensor_stages import (
    PressureTensorStage,
    TensorMortalityStage,
    TensorDiffusionStage,
    TensorReproductionStage,
    TensorCompetitionStage,
    TensorStateSyncStage,
    TensorMetricsStage,
    get_tensor_stages,
    get_minimal_tensor_stages,
)
from ..context import SimulationContext
from ...tensor import TensorState, TensorMetrics, TensorConfig, TensorBalanceConfig


@pytest.fixture
def mock_tensor_state():
    """创建测试用的 TensorState"""
    env = np.random.rand(5, 1, 10).astype(np.float32)  # (C, H, W)
    env[1] = 20.0  # 温度通道
    
    pop = np.random.rand(3, 1, 10).astype(np.float32) * 1000  # (S, H, W)
    species_params = np.zeros((3, 10), dtype=np.float32)  # 扩展到 10 列
    species_params[:, :5] = 0.5  # 默认值
    
    return TensorState(
        env=env,
        pop=pop,
        species_params=species_params,
        species_map={"SP001": 0, "SP002": 1, "SP003": 2},
    )


@pytest.fixture
def mock_context(mock_tensor_state):
    """创建测试用的 SimulationContext"""
    ctx = SimulationContext()
    ctx.turn_index = 1
    ctx.tensor_state = mock_tensor_state
    ctx.combined_results = []
    ctx.new_populations = {}
    ctx.species_batch = []
    ctx.tensor_trigger_codes = set()
    ctx.modifiers = {}
    ctx.pressures = []
    ctx.pressure_overlay = None
    return ctx


@pytest.fixture
def mock_engine():
    """创建测试用的 SimulationEngine"""
    engine = MagicMock()
    engine._use_tensor_mortality = True
    engine._use_tensor_speciation = True
    
    # 创建真实的 TensorConfig 和 TensorBalanceConfig
    balance = TensorBalanceConfig(
        temp_optimal=20.0,
        temp_tolerance=15.0,
        temp_channel_idx=1,
        diffusion_rate=0.1,
        birth_rate=0.1,
        competition_strength=0.01,
        capacity_multiplier=10000.0,
    )
    tensor_config = TensorConfig(balance=balance)
    engine.tensor_config = tensor_config
    
    return engine


class TestPressureTensorStage:
    """PressureTensorStage 测试"""
    
    def test_stage_name(self):
        """测试阶段名称"""
        stage = PressureTensorStage()
        assert "压力" in stage.name
    
    async def test_execute_creates_overlay(self, mock_context, mock_engine):
        """测试执行后创建压力叠加层"""
        mock_context.modifiers = {"temperature": -1.5, "drought": 2.0}
        
        stage = PressureTensorStage()
        await stage.execute(mock_context, mock_engine)
        
        assert mock_context.pressure_overlay is not None
        assert len(mock_context.pressure_overlay.active_pressures) > 0


class TestTensorMortalityStage:
    """TensorMortalityStage 测试"""
    
    def test_stage_order(self):
        """测试阶段顺序正确"""
        stage = TensorMortalityStage()
        assert "张量死亡率" in stage.name
    
    async def test_execute_raises_when_disabled(self, mock_context, mock_engine):
        """测试禁用时抛出异常"""
        mock_engine._use_tensor_mortality = False
        stage = TensorMortalityStage()
        
        with pytest.raises(RuntimeError, match="张量死亡率被禁用"):
            await stage.execute(mock_context, mock_engine)
    
    async def test_execute_raises_when_no_tensor_state(self, mock_context, mock_engine):
        """测试没有 tensor_state 时抛出异常"""
        mock_context.tensor_state = None
        stage = TensorMortalityStage()
        
        with pytest.raises(RuntimeError, match="缺少 tensor_state"):
            await stage.execute(mock_context, mock_engine)
    
    async def test_execute_updates_population(self, mock_context, mock_engine):
        """测试执行后更新种群"""
        stage = TensorMortalityStage()
        
        original_pop = mock_context.tensor_state.pop.sum()
        await stage.execute(mock_context, mock_engine)
        
        # 应用死亡率后种群应该减少
        new_pop = mock_context.tensor_state.pop.sum()
        assert new_pop < original_pop
    
    async def test_execute_updates_metrics(self, mock_context, mock_engine):
        """测试执行后更新监控指标"""
        stage = TensorMortalityStage()
        
        await stage.execute(mock_context, mock_engine)
        
        assert mock_context.tensor_metrics is not None
        assert mock_context.tensor_metrics.mortality_time_ms > 0


class TestTensorDiffusionStage:
    """TensorDiffusionStage 测试"""
    
    def test_stage_name(self):
        """测试阶段名称"""
        stage = TensorDiffusionStage()
        assert "扩散" in stage.name
    
    async def test_execute_diffuses_population(self, mock_context, mock_engine):
        """测试扩散后种群分布变化"""
        # 设置集中的初始分布
        mock_context.tensor_state.pop = np.zeros((3, 1, 10), dtype=np.float32)
        mock_context.tensor_state.pop[0, 0, 5] = 1000  # 只在中间位置有种群
        
        stage = TensorDiffusionStage()
        await stage.execute(mock_context, mock_engine)
        
        # 扩散后应该分布到邻近位置
        pop = mock_context.tensor_state.pop[0, 0]
        assert pop[4] > 0 or pop[6] > 0  # 邻近位置应该有种群


class TestTensorReproductionStage:
    """TensorReproductionStage 测试"""
    
    def test_stage_name(self):
        """测试阶段名称"""
        stage = TensorReproductionStage()
        assert "繁殖" in stage.name
    
    async def test_execute_increases_population(self, mock_context, mock_engine):
        """测试繁殖增加种群"""
        initial_pop = mock_context.tensor_state.pop.sum()
        
        stage = TensorReproductionStage()
        await stage.execute(mock_context, mock_engine)
        
        # 繁殖后种群应该增加
        new_pop = mock_context.tensor_state.pop.sum()
        assert new_pop >= initial_pop


class TestTensorCompetitionStage:
    """TensorCompetitionStage 测试"""
    
    def test_stage_name(self):
        """测试阶段名称"""
        stage = TensorCompetitionStage()
        assert "竞争" in stage.name
    
    async def test_execute_reduces_population(self, mock_context, mock_engine):
        """测试竞争减少种群"""
        initial_pop = mock_context.tensor_state.pop.sum()
        
        stage = TensorCompetitionStage()
        await stage.execute(mock_context, mock_engine)
        
        # 竞争后种群应该减少
        new_pop = mock_context.tensor_state.pop.sum()
        assert new_pop <= initial_pop


class TestTensorMetricsStage:
    """TensorMetricsStage 测试"""
    
    def test_stage_name(self):
        """测试阶段名称"""
        stage = TensorMetricsStage()
        assert "监控" in stage.name or "指标" in stage.name
    
    async def test_execute_collects_metrics(self, mock_context, mock_engine):
        """测试收集监控指标"""
        mock_context.tensor_trigger_codes = {"SP001", "SP002"}
        
        stage = TensorMetricsStage()
        await stage.execute(mock_context, mock_engine)
        
        assert mock_context.tensor_metrics is not None


class TestTensorStateSyncStage:
    """TensorStateSyncStage 测试"""
    
    def test_stage_name(self):
        """测试阶段名称"""
        stage = TensorStateSyncStage()
        assert "同步" in stage.name
    
    async def test_execute_syncs_populations(self, mock_context, mock_engine):
        """测试同步种群数据"""
        mock_context.new_populations = {"SP001": 100, "SP002": 200}
        
        stage = TensorStateSyncStage()
        await stage.execute(mock_context, mock_engine)
        
        # 应该更新 new_populations
        assert "SP001" in mock_context.new_populations
        assert mock_context.new_populations["SP001"] >= 0


class TestGetTensorStages:
    """测试获取张量阶段函数"""
    
    def test_get_tensor_stages_returns_list(self):
        """测试返回阶段列表"""
        stages = get_tensor_stages()
        assert isinstance(stages, list)
        assert len(stages) > 0
    
    def test_get_tensor_stages_contains_mortality(self):
        """测试包含死亡率阶段"""
        stages = get_tensor_stages()
        names = [s.name for s in stages]
        assert any("死亡率" in name for name in names)
    
    def test_get_tensor_stages_contains_metrics(self):
        """测试包含监控阶段"""
        stages = get_tensor_stages()
        names = [s.name for s in stages]
        assert any("监控" in name or "指标" in name for name in names)
    
    def test_get_minimal_tensor_stages(self):
        """测试获取最小阶段集"""
        stages = get_minimal_tensor_stages()
        assert len(stages) == 3  # 包含 PressureTensorStage
        
        names = [s.name for s in stages]
        assert any("压力" in name for name in names)
        assert any("死亡率" in name for name in names)
        assert any("监控" in name or "指标" in name for name in names)
    
    def test_stages_have_correct_order(self):
        """测试阶段顺序正确"""
        stages = get_tensor_stages()
        orders = [s.order for s in stages]
        
        # 所有阶段都应该有正整数 order
        assert all(o > 0 for o in orders)


class TestStageIntegration:
    """阶段集成测试"""
    
    async def test_full_tensor_pipeline(self, mock_context, mock_engine):
        """测试完整张量管线执行"""
        stages = get_tensor_stages()
        
        initial_pop = mock_context.tensor_state.pop.sum()
        
        for stage in sorted(stages, key=lambda s: s.order):
            await stage.execute(mock_context, mock_engine)
        
        # 管线执行完成后应该有监控指标
        assert mock_context.tensor_metrics is not None
    
    async def test_stages_raise_on_invalid_state(self, mock_context, mock_engine):
        """测试阶段在无效状态时抛出异常"""
        # 设置无效的 tensor_state（空数组）
        mock_context.tensor_state.pop = np.array([])
        
        stage = TensorMortalityStage()
        
        # 应该抛出异常
        with pytest.raises((ValueError, RuntimeError)):
            await stage.execute(mock_context, mock_engine)
    
    async def test_pressure_stage_first(self, mock_context, mock_engine):
        """测试压力阶段在死亡率阶段之前执行"""
        stages = get_tensor_stages()
        sorted_stages = sorted(stages, key=lambda s: s.order)
        
        pressure_idx = next(i for i, s in enumerate(sorted_stages) if "压力" in s.name)
        mortality_idx = next(i for i, s in enumerate(sorted_stages) if "死亡率" in s.name)
        
        assert pressure_idx < mortality_idx

