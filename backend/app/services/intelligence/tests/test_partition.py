"""
Test Partition - 物种分档测试

测试 EcologicalIntelligence 的分档逻辑。
"""

import pytest
from ..ecological_intelligence import EcologicalIntelligence, PartitionResult
from ..schemas import AssessmentTier
from ..config import IntelligenceConfig


class MockSpecies:
    """模拟物种对象"""
    
    def __init__(
        self,
        lineage_code: str,
        population: int = 10000,
        trophic_level: float = 2.0,
        status: str = "alive",
    ):
        self.id = hash(lineage_code) % 10000
        self.lineage_code = lineage_code
        self.common_name = f"Species {lineage_code}"
        self.latin_name = f"Testus {lineage_code.lower()}"
        self.status = status
        self.trophic_level = trophic_level
        self.morphology_stats = {"population": population}
        self.hidden_traits = {}


class MockMortalityResult:
    """模拟死亡率结果"""
    
    def __init__(self, species: MockSpecies, death_rate: float):
        self.species = species
        self.death_rate = death_rate


class TestPartitioning:
    """分档测试"""
    
    def setup_method(self):
        self.config = IntelligenceConfig(
            top_a_count=3,
            top_b_count=5,
            priority_threshold=0.3,
        )
        self.intelligence = EcologicalIntelligence(config=self.config)
    
    def test_basic_partition(self):
        """基本分档测试"""
        species = [
            MockSpecies(f"SP-{i:03d}", population=i * 1000)
            for i in range(1, 11)
        ]
        mortalities = [
            MockMortalityResult(sp, 0.1 + i * 0.05)
            for i, sp in enumerate(species)
        ]
        
        partition = self.intelligence.partition_species(species, mortalities)
        
        assert isinstance(partition, PartitionResult)
        assert len(partition.tier_a) == 3  # top_a_count
        assert len(partition.tier_b) <= 5  # top_b_count
        assert partition.total_count == 10
    
    def test_high_risk_species_in_tier_a(self):
        """高风险物种应该进入 A 档"""
        # 创建一个高风险物种和多个低风险物种
        high_risk = MockSpecies("HIGH-RISK", population=50)
        low_risk = [
            MockSpecies(f"LOW-{i}", population=100000)
            for i in range(5)
        ]
        
        species = [high_risk] + low_risk
        mortalities = [
            MockMortalityResult(high_risk, 0.8),  # 高死亡率
        ] + [
            MockMortalityResult(sp, 0.1)
            for sp in low_risk
        ]
        
        partition = self.intelligence.partition_species(species, mortalities)
        
        # 高风险物种应该在 A 档
        tier_a_codes = [p.lineage_code for p in partition.tier_a]
        assert "HIGH-RISK" in tier_a_codes
    
    def test_tier_assignment(self):
        """确保分档后物种的 tier 属性正确"""
        species = [
            MockSpecies(f"SP-{i}", population=i * 1000)
            for i in range(1, 11)
        ]
        mortalities = [
            MockMortalityResult(sp, 0.2)
            for sp in species
        ]
        
        partition = self.intelligence.partition_species(species, mortalities)
        
        # A 档物种应该有 tier = A
        for p in partition.tier_a:
            assert p.tier == AssessmentTier.A
        
        # B 档物种应该有 tier = B
        for p in partition.tier_b:
            assert p.tier == AssessmentTier.B
        
        # C 档物种应该有 tier = C
        for p in partition.tier_c:
            assert p.tier == AssessmentTier.C
    
    def test_extinct_species_excluded(self):
        """灭绝物种不应该被分档"""
        alive = MockSpecies("ALIVE", population=10000)
        extinct = MockSpecies("EXTINCT", population=0, status="extinct")
        
        species = [alive, extinct]
        mortalities = [
            MockMortalityResult(alive, 0.2),
            MockMortalityResult(extinct, 1.0),
        ]
        
        partition = self.intelligence.partition_species(species, mortalities)
        
        assert partition.total_count == 1
        
        all_codes = (
            [p.lineage_code for p in partition.tier_a] +
            [p.lineage_code for p in partition.tier_b] +
            [p.lineage_code for p in partition.tier_c]
        )
        assert "EXTINCT" not in all_codes
    
    def test_empty_input(self):
        """空输入应该返回空分档"""
        partition = self.intelligence.partition_species([], [])
        
        assert partition.total_count == 0
        assert len(partition.tier_a) == 0
        assert len(partition.tier_b) == 0
        assert len(partition.tier_c) == 0
    
    def test_single_species(self):
        """单个物种应该进入 A 档"""
        species = [MockSpecies("ONLY", population=10000)]
        mortalities = [MockMortalityResult(species[0], 0.3)]
        
        partition = self.intelligence.partition_species(species, mortalities)
        
        assert partition.total_count == 1
        assert len(partition.tier_a) == 1
        assert partition.tier_a[0].lineage_code == "ONLY"
    
    def test_priority_threshold(self):
        """低于阈值的物种不应该进入 B 档"""
        config = IntelligenceConfig(
            top_a_count=1,
            top_b_count=5,
            priority_threshold=0.9,  # 很高的阈值
        )
        intelligence = EcologicalIntelligence(config=config)
        
        species = [
            MockSpecies(f"SP-{i}", population=100000)
            for i in range(5)
        ]
        mortalities = [
            MockMortalityResult(sp, 0.05)  # 很低的死亡率
            for sp in species
        ]
        
        partition = intelligence.partition_species(species, mortalities)
        
        # 大多数物种优先级低，应该在 C 档
        assert len(partition.tier_c) >= 2
    
    def test_config_limits_respected(self):
        """配置的数量限制应该被遵守"""
        config = IntelligenceConfig(
            top_a_count=2,
            top_b_count=3,
        )
        intelligence = EcologicalIntelligence(config=config)
        
        species = [
            MockSpecies(f"SP-{i}", population=i * 100)
            for i in range(1, 21)  # 20 个物种
        ]
        mortalities = [
            MockMortalityResult(sp, 0.5)  # 中等死亡率
            for sp in species
        ]
        
        partition = intelligence.partition_species(species, mortalities)
        
        assert len(partition.tier_a) <= 2
        assert len(partition.tier_b) <= 3
        # 其余应该在 C 档
        assert len(partition.tier_c) >= 15


class TestPartitionResult:
    """PartitionResult 测试"""
    
    def test_total_count(self):
        """total_count 应该返回正确的总数"""
        result = PartitionResult(
            tier_a=[MockPriority("A-1"), MockPriority("A-2")],
            tier_b=[MockPriority("B-1")],
            tier_c=[MockPriority("C-1"), MockPriority("C-2"), MockPriority("C-3")],
        )
        
        assert result.total_count == 6


class MockPriority:
    """简单的优先级模拟对象"""
    
    def __init__(self, lineage_code: str):
        self.lineage_code = lineage_code
        self.tier = AssessmentTier.C


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

