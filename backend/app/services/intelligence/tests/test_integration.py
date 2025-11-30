"""
Test Integration - 生态智能体集成测试

测试完整的评估流程：
1. 物种评分与分档
2. LLM 调用（mock）
3. 评估结果解析
4. ModifierApplicator 应用
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ..ecological_intelligence import EcologicalIntelligence, PartitionResult
from ..llm_orchestrator import LLMOrchestrator, OrchestratorResult
from ..modifier_applicator import ModifierApplicator
from ..schemas import (
    AssessmentBatch,
    AssessmentTier,
    BiologicalAssessment,
    EnvironmentSummary,
    SpeciesAssessmentInput,
)
from ..config import IntelligenceConfig


class MockSpecies:
    """模拟物种对象"""
    
    def __init__(
        self,
        lineage_code: str,
        population: int = 10000,
        trophic_level: float = 2.0,
        death_rate: float = 0.2,
    ):
        self.id = hash(lineage_code) % 10000
        self.lineage_code = lineage_code
        self.common_name = f"Species {lineage_code}"
        self.latin_name = f"Testus {lineage_code.lower()}"
        self.status = "alive"
        self.trophic_level = trophic_level
        self.morphology_stats = {"population": population}
        self.hidden_traits = {"trait1": 0.5}
        self.climate_niche = None
        self.diet = None
        self.habitats = []
        self.active_genes = []
        self.parent_code = None
        self.genus_code = None


class MockMortalityResult:
    """模拟死亡率结果"""
    
    def __init__(self, species: MockSpecies, death_rate: float):
        self.species = species
        self.death_rate = death_rate
        self.initial_population = species.morphology_stats.get("population", 0)
        self.tier = "focus"


class TestFullIntegration:
    """完整流程集成测试"""
    
    @pytest.fixture
    def species_list(self):
        """创建测试物种列表"""
        return [
            MockSpecies("CRIT-001", population=500, death_rate=0.6),  # 高风险
            MockSpecies("CRIT-002", population=1000, death_rate=0.5),
            MockSpecies("FOCUS-001", population=5000, death_rate=0.3),
            MockSpecies("FOCUS-002", population=8000, death_rate=0.25),
            MockSpecies("FOCUS-003", population=10000, death_rate=0.2),
            MockSpecies("BG-001", population=50000, death_rate=0.1),
            MockSpecies("BG-002", population=100000, death_rate=0.05),
        ]
    
    @pytest.fixture
    def mortality_results(self, species_list):
        """创建死亡率结果"""
        return [
            MockMortalityResult(sp, getattr(sp, '_death_rate', 0.2))
            for sp in species_list
        ]
    
    @pytest.fixture
    def mock_router(self):
        """创建 mock ModelRouter"""
        router = MagicMock()
        
        # Mock acall_capability 返回 JSON 格式的评估结果
        async def mock_acall(capability, messages, response_format=None):
            return """[
                {"lineage_code": "CRIT-001", "mortality_modifier": 0.7, "r_adjust": 0.1, "ecological_fate": "endangered"},
                {"lineage_code": "CRIT-002", "mortality_modifier": 0.8, "r_adjust": 0.05, "ecological_fate": "declining"}
            ]"""
        
        router.acall_capability = AsyncMock(side_effect=mock_acall)
        return router
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, species_list, mortality_results, mock_router):
        """测试完整的评估流程"""
        config = IntelligenceConfig(
            top_a_count=2,
            top_b_count=3,
            enable_llm_calls=True,
        )
        
        # Step 1: 初始化组件
        intelligence = EcologicalIntelligence(config=config)
        orchestrator = LLMOrchestrator(router=mock_router, config=config)
        modifier = ModifierApplicator(config=config)
        
        # Step 2: 分档
        partition = intelligence.partition_species(
            species_list,
            mortality_results,
        )
        
        assert len(partition.tier_a) <= config.top_a_count
        assert len(partition.tier_b) <= config.top_b_count
        assert partition.total_count == len(species_list)
        
        # Step 3: 构建环境摘要
        environment = intelligence.build_environment_summary(
            turn_index=10,
            modifiers={"temperature": 0.5, "humidity": -0.2},
            major_events=[],
            map_state=None,
            species_count=len(species_list),
        )
        
        assert environment.turn_index == 10
        assert environment.active_pressures["temperature"] == 0.5
        
        # Step 4: 构建批次
        species_map = {sp.lineage_code: sp for sp in species_list}
        batch_a, batch_b = intelligence.build_assessment_batches(
            partition, species_map, environment
        )
        
        assert batch_a.tier == AssessmentTier.A
        assert batch_b.tier == AssessmentTier.B
        
        # Step 5: 执行 LLM 评估（mock）
        species_id_map = {sp.lineage_code: sp.id for sp in species_list}
        result = await orchestrator.execute(
            batch_a, batch_b, species_id_map
        )
        
        assert isinstance(result, OrchestratorResult)
        # 注意：由于 mock 返回的是固定数据，需要检查解析是否正确
        
        # Step 6: 设置 ModifierApplicator
        modifier.set_assessments(result.assessments)
        
        # Step 7: 应用修正
        for species in species_list:
            code = species.lineage_code
            base_mortality = 0.3
            
            adjusted = modifier.apply(code, base_mortality, "mortality")
            
            # 如果有评估，应该被修正
            if code in result.assessments:
                assert adjusted != base_mortality or result.assessments[code].mortality_modifier == 1.0
    
    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self, species_list, mortality_results):
        """测试 LLM 超时时的降级策略"""
        config = IntelligenceConfig(
            top_a_count=2,
            top_b_count=3,
            enable_llm_calls=True,
            llm_timeout_seconds=0.001,  # 非常短的超时
        )
        
        # 创建一个会超时的 mock router
        router = MagicMock()
        
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(1)  # 超时
            return "[]"
        
        router.acall_capability = AsyncMock(side_effect=slow_call)
        
        intelligence = EcologicalIntelligence(config=config)
        orchestrator = LLMOrchestrator(router=router, config=config)
        modifier = ModifierApplicator(config=config)
        
        # 分档
        partition = intelligence.partition_species(species_list, mortality_results)
        
        # 构建批次
        environment = intelligence.build_environment_summary(10, {}, [], None, 7)
        species_map = {sp.lineage_code: sp for sp in species_list}
        batch_a, batch_b = intelligence.build_assessment_batches(partition, species_map, environment)
        
        # 执行评估（预期超时）
        result = await orchestrator.execute(batch_a, batch_b)
        
        # 应该返回空结果而不是崩溃
        assert isinstance(result, OrchestratorResult)
        
        # 使用默认评估
        all_codes = [p.lineage_code for p in partition.tier_a + partition.tier_b + partition.tier_c]
        defaults = orchestrator.create_default_assessments(all_codes)
        modifier.set_assessments(defaults)
        
        # 默认评估应该是中性的
        for code in all_codes:
            adjusted = modifier.apply(code, 0.5, "mortality")
            # 默认 mortality_modifier = 1.0，所以结果应该等于基础值
            assert adjusted == pytest.approx(0.5, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_llm_disabled(self, species_list, mortality_results):
        """测试 LLM 禁用时的行为"""
        config = IntelligenceConfig(
            enable_llm_calls=False,
        )
        
        router = MagicMock()
        intelligence = EcologicalIntelligence(config=config)
        orchestrator = LLMOrchestrator(router=router, config=config)
        
        partition = intelligence.partition_species(species_list, mortality_results)
        environment = intelligence.build_environment_summary(10, {}, [], None, 7)
        species_map = {sp.lineage_code: sp for sp in species_list}
        batch_a, batch_b = intelligence.build_assessment_batches(partition, species_map, environment)
        
        result = await orchestrator.execute(batch_a, batch_b)
        
        # 应该返回空结果
        assert len(result.assessments) == 0
        assert "禁用" in result.errors[0]


class TestPartitioningEdgeCases:
    """分档边界情况测试"""
    
    def test_empty_species_list(self):
        """空物种列表"""
        config = IntelligenceConfig()
        intelligence = EcologicalIntelligence(config=config)
        
        partition = intelligence.partition_species([], [])
        
        assert partition.total_count == 0
        assert len(partition.tier_a) == 0
        assert len(partition.tier_b) == 0
        assert len(partition.tier_c) == 0
    
    def test_single_species(self):
        """单个物种"""
        config = IntelligenceConfig(top_a_count=2, top_b_count=3)
        intelligence = EcologicalIntelligence(config=config)
        
        species = MockSpecies("ONLY-001")
        mortality = MockMortalityResult(species, 0.5)
        
        partition = intelligence.partition_species([species], [mortality])
        
        assert partition.total_count == 1
        assert len(partition.tier_a) == 1  # 唯一物种进入 A 档
    
    def test_all_extinct_species(self):
        """全部灭绝物种"""
        config = IntelligenceConfig()
        intelligence = EcologicalIntelligence(config=config)
        
        species = MockSpecies("DEAD-001")
        species.status = "extinct"
        mortality = MockMortalityResult(species, 1.0)
        
        partition = intelligence.partition_species([species], [mortality])
        
        # 灭绝物种不应该被分档
        assert partition.total_count == 0


class TestModifierApplicatorWithRealAssessments:
    """使用真实评估数据测试 ModifierApplicator"""
    
    def test_apply_multiple_modifications(self):
        """测试多种修正的组合应用"""
        config = IntelligenceConfig()
        modifier = ModifierApplicator(config=config)
        
        # 创建一个综合的评估
        assessment = BiologicalAssessment(
            species_id=1,
            lineage_code="TEST-001",
            mortality_modifier=0.8,
            r_adjust=0.1,
            k_adjust=0.2,
            migration_bias=0.3,
            speciation_signal=0.7,
            ecological_fate="thriving",
        )
        modifier.set_assessments({"TEST-001": assessment})
        
        # 应用各种修正
        mortality = modifier.apply("TEST-001", 0.5, "mortality")
        r = modifier.apply("TEST-001", 1.0, "reproduction_r")
        k = modifier.apply("TEST-001", 10000, "carrying_capacity")
        migration = modifier.apply("TEST-001", 0.2, "migration")
        
        assert mortality < 0.5  # 死亡率降低
        assert r > 1.0  # 繁殖率提高
        assert k > 10000  # 承载力提高
        assert migration > 0.2  # 迁徙概率提高
        
        # 检查生态命运和分化信号
        assert modifier.get_ecological_fate("TEST-001") == "thriving"
        assert modifier.should_speciate("TEST-001") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

