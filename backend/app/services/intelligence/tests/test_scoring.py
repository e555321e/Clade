"""
Test Scoring - 物种评分测试

测试 EcologicalIntelligence 的 risk/impact/potential 评分计算。
"""

import pytest
from unittest.mock import MagicMock
from ..ecological_intelligence import EcologicalIntelligence
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
        self.hidden_traits = {"trait1": 0.5, "trait2": 0.3}
        self.climate_niche = None
        self.diet = None
        self.habitats = []
        self.active_genes = []


class TestRiskScoring:
    """风险评分测试"""
    
    def setup_method(self):
        self.config = IntelligenceConfig(
            death_rate_critical_threshold=0.5,
            death_rate_warning_threshold=0.3,
            population_critical_threshold=100,
        )
        self.intelligence = EcologicalIntelligence(config=self.config)
    
    def test_high_death_rate_high_risk(self):
        """高死亡率应该产生高风险评分"""
        species = MockSpecies("TEST-001", population=10000)
        
        risk = self.intelligence.calculate_risk(species, death_rate=0.6)
        
        # 死亡率 0.6 > 0.5 (critical)，应该接近最大
        assert risk >= 0.5
    
    def test_low_death_rate_low_risk(self):
        """低死亡率应该产生低风险评分"""
        species = MockSpecies("TEST-002", population=50000)
        
        risk = self.intelligence.calculate_risk(species, death_rate=0.1)
        
        assert risk < 0.3
    
    def test_small_population_increases_risk(self):
        """小种群应该增加风险"""
        species_small = MockSpecies("TEST-SMALL", population=50)
        species_large = MockSpecies("TEST-LARGE", population=100000)
        
        risk_small = self.intelligence.calculate_risk(species_small, death_rate=0.2)
        risk_large = self.intelligence.calculate_risk(species_large, death_rate=0.2)
        
        assert risk_small > risk_large
    
    def test_zero_population_max_risk(self):
        """零种群应该产生最高风险"""
        species = MockSpecies("TEST-EXTINCT", population=0)
        
        risk = self.intelligence.calculate_risk(species, death_rate=0.2)
        
        # 种群评分部分应该最大
        assert risk >= 0.3  # 0.3 是种群权重
    
    def test_risk_always_in_range(self):
        """风险评分应该始终在 [0, 1] 范围内"""
        species = MockSpecies("TEST")
        
        for death_rate in [0.0, 0.1, 0.5, 0.9, 1.0]:
            for population in [0, 50, 1000, 100000]:
                species.morphology_stats["population"] = population
                risk = self.intelligence.calculate_risk(species, death_rate)
                
                assert 0.0 <= risk <= 1.0, f"Risk {risk} out of range"


class TestImpactScoring:
    """生态影响评分测试"""
    
    def setup_method(self):
        self.config = IntelligenceConfig(
            biomass_high_impact_threshold=0.2,
        )
        self.intelligence = EcologicalIntelligence(config=self.config)
    
    def test_dominant_species_high_impact(self):
        """主导物种应该有高影响评分"""
        dominant = MockSpecies("DOMINANT", population=90000)
        others = [
            MockSpecies("OTHER-1", population=5000),
            MockSpecies("OTHER-2", population=5000),
        ]
        all_species = [dominant] + others
        
        impact = self.intelligence.calculate_impact(dominant, all_species)
        
        # 90% 生物量，应该接近最高
        assert impact >= 0.4
    
    def test_rare_species_lower_impact(self):
        """稀有物种应该有较低影响评分"""
        rare = MockSpecies("RARE", population=100)
        others = [
            MockSpecies("COMMON-1", population=50000),
            MockSpecies("COMMON-2", population=50000),
        ]
        all_species = [rare] + others
        
        impact = self.intelligence.calculate_impact(rare, all_species)
        
        assert impact < 0.5
    
    def test_apex_predator_high_impact(self):
        """顶级捕食者应该有高影响评分"""
        apex = MockSpecies("APEX", population=1000, trophic_level=4.5)
        prey = MockSpecies("PREY", population=100000, trophic_level=2.0)
        
        all_species = [apex, prey]
        
        impact_apex = self.intelligence.calculate_impact(apex, all_species)
        impact_prey = self.intelligence.calculate_impact(prey, all_species)
        
        # 虽然种群小，但顶级捕食者影响更高
        assert impact_apex > 0.3
    
    def test_bottleneck_species_high_impact(self):
        """瓶颈物种应该有高影响评分"""
        bottleneck = MockSpecies("BOTTLENECK", population=5000)
        others = [MockSpecies(f"OTHER-{i}", population=10000) for i in range(5)]
        
        # 模拟食物网分析结果
        food_web = MagicMock()
        food_web.bottleneck_species = ["BOTTLENECK"]
        food_web.total_links = 20
        
        all_species = [bottleneck] + others
        
        impact = self.intelligence.calculate_impact(bottleneck, all_species, food_web)
        
        # 瓶颈物种应该有较高中心度评分
        assert impact >= 0.3


class TestPotentialScoring:
    """潜力评分测试"""
    
    def setup_method(self):
        self.config = IntelligenceConfig()
        self.intelligence = EcologicalIntelligence(config=self.config)
    
    def test_high_genetic_diversity_high_potential(self):
        """高遗传多样性应该有高潜力"""
        diverse = MockSpecies("DIVERSE", population=10000)
        diverse.hidden_traits = {f"trait_{i}": 0.5 for i in range(8)}  # 8个隐藏特征
        
        simple = MockSpecies("SIMPLE", population=10000)
        simple.hidden_traits = {"trait_1": 0.5}  # 1个隐藏特征
        
        potential_diverse = self.intelligence.calculate_potential(diverse)
        potential_simple = self.intelligence.calculate_potential(simple)
        
        assert potential_diverse > potential_simple
    
    def test_medium_population_optimal_potential(self):
        """中等种群有最佳演化潜力"""
        small = MockSpecies("SMALL", population=200)
        medium = MockSpecies("MEDIUM", population=10000)
        large = MockSpecies("LARGE", population=1000000)
        
        # 设置相同的隐藏特征
        for sp in [small, medium, large]:
            sp.hidden_traits = {"trait_1": 0.5, "trait_2": 0.3}
        
        pot_small = self.intelligence.calculate_potential(small)
        pot_medium = self.intelligence.calculate_potential(medium)
        pot_large = self.intelligence.calculate_potential(large)
        
        # 中等种群应该有最高潜力
        assert pot_medium >= pot_small
        assert pot_medium >= pot_large
    
    def test_unique_niche_high_potential(self):
        """独特生态位应该有高潜力"""
        species = MockSpecies("UNIQUE", population=10000)
        
        # 模拟低重叠的生态位指标
        niche_metrics = {
            "UNIQUE": MagicMock(overlap=0.1, saturation=0.3),
        }
        
        potential = self.intelligence.calculate_potential(species, niche_metrics)
        
        # 低重叠意味着独特生态位
        assert potential >= 0.3


class TestPriorityCalculation:
    """优先级计算测试"""
    
    def setup_method(self):
        self.config = IntelligenceConfig(
            risk_weight=0.4,
            impact_weight=0.3,
            potential_weight=0.3,
        )
        self.intelligence = EcologicalIntelligence(config=self.config)
    
    def test_priority_is_weighted_sum(self):
        """优先级应该是加权和"""
        species = MockSpecies("TEST", population=5000)
        all_species = [species]
        
        priority = self.intelligence.calculate_priority(
            species, death_rate=0.4, all_species=all_species
        )
        
        # 手动计算预期值
        expected = (
            priority.risk * 0.4 +
            priority.impact * 0.3 +
            priority.potential * 0.3
        )
        
        assert abs(priority.priority - expected) < 0.01
    
    def test_priority_caching(self):
        """优先级计算应该被缓存"""
        species = MockSpecies("CACHED", population=10000)
        all_species = [species]
        
        # 第一次计算
        priority1 = self.intelligence.calculate_priority(
            species, death_rate=0.3, all_species=all_species
        )
        
        # 第二次计算（应该使用缓存）
        priority2 = self.intelligence.calculate_priority(
            species, death_rate=0.3, all_species=all_species
        )
        
        assert priority1 is priority2  # 同一个对象
    
    def test_cache_clear(self):
        """缓存清除应该正常工作"""
        species = MockSpecies("CLEAR", population=10000)
        all_species = [species]
        
        priority1 = self.intelligence.calculate_priority(
            species, death_rate=0.3, all_species=all_species
        )
        
        self.intelligence.clear_cache()
        
        priority2 = self.intelligence.calculate_priority(
            species, death_rate=0.3, all_species=all_species
        )
        
        # 不同的对象
        assert priority1 is not priority2
        # 但值相同
        assert abs(priority1.priority - priority2.priority) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
