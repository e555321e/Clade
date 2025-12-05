"""
TensorMetrics 和 TensorMetricsCollector 单元测试

测试张量系统监控指标的核心功能。
"""

import time

import pytest

from ..metrics import (
    TensorMetrics,
    TensorMetricsCollector,
    get_global_collector,
    reset_global_collector,
)


class TestTensorMetrics:
    """TensorMetrics 测试套件"""
    
    def test_default_values(self):
        """测试默认值"""
        metrics = TensorMetrics()
        
        assert metrics.mortality_time_ms == 0.0
        assert metrics.speciation_detection_time_ms == 0.0
        assert metrics.tradeoff_time_ms == 0.0
        assert metrics.tensor_triggers == 0
        assert metrics.ai_fallback_count == 0
    
    def test_total_time(self):
        """测试总耗时计算"""
        metrics = TensorMetrics(
            mortality_time_ms=10.0,
            speciation_detection_time_ms=5.0,
            tradeoff_time_ms=3.0,
        )
        
        assert metrics.total_time_ms() == 18.0
    
    def test_trigger_hit_rate_with_speciations(self):
        """测试触发命中率"""
        metrics = TensorMetrics(tensor_triggers=8)
        
        assert metrics.trigger_hit_rate(10) == 0.8
    
    def test_trigger_hit_rate_zero_speciations(self):
        """测试零分化时的命中率"""
        metrics = TensorMetrics(tensor_triggers=5)
        
        assert metrics.trigger_hit_rate(0) == 0.0
    
    def test_trigger_hit_rate_exceeds_one(self):
        """测试命中率上限为1.0"""
        metrics = TensorMetrics(tensor_triggers=15)
        
        assert metrics.trigger_hit_rate(10) == 1.0
    
    def test_to_dict(self):
        """测试转换为字典"""
        metrics = TensorMetrics(
            mortality_time_ms=10.5,
            speciation_detection_time_ms=5.3,
            tradeoff_time_ms=2.1,
            tensor_triggers=3,
            ai_fallback_count=1,
        )
        
        d = metrics.to_dict()
        
        assert d["mortality_time_ms"] == 10.5
        assert d["speciation_detection_time_ms"] == 5.3
        assert d["tradeoff_time_ms"] == 2.1
        assert d["total_time_ms"] == 17.9
        assert d["tensor_triggers"] == 3
        assert d["ai_fallback_count"] == 1


class TestTensorMetricsCollector:
    """TensorMetricsCollector 测试套件"""
    
    @pytest.fixture
    def collector(self) -> TensorMetricsCollector:
        """创建新的收集器"""
        return TensorMetricsCollector()
    
    def test_initial_state(self, collector: TensorMetricsCollector):
        """测试初始状态"""
        assert collector.total_turns == 0
        assert collector.total_tensor_triggers == 0
        assert collector.total_ai_fallbacks == 0
        assert len(collector.history) == 0
    
    def test_track_mortality_timing(self, collector: TensorMetricsCollector):
        """测试死亡率计时"""
        with collector.track_mortality():
            time.sleep(0.01)  # 10ms
        
        assert collector.current.mortality_time_ms >= 10.0
    
    def test_track_speciation_detection_timing(self, collector: TensorMetricsCollector):
        """测试分化检测计时"""
        with collector.track_speciation_detection():
            time.sleep(0.01)
        
        assert collector.current.speciation_detection_time_ms >= 10.0
    
    def test_track_tradeoff_timing(self, collector: TensorMetricsCollector):
        """测试代价计算计时"""
        with collector.track_tradeoff():
            time.sleep(0.01)
        
        assert collector.current.tradeoff_time_ms >= 10.0
    
    def test_record_tensor_trigger(self, collector: TensorMetricsCollector):
        """测试记录张量触发"""
        collector.record_tensor_trigger(3)
        collector.record_tensor_trigger(2)
        
        assert collector.current.tensor_triggers == 5
    
    def test_record_ai_fallback(self, collector: TensorMetricsCollector):
        """测试记录 AI 回退"""
        collector.record_ai_fallback(1)
        collector.record_ai_fallback(2)
        
        assert collector.current.ai_fallback_count == 3
    
    def test_end_turn_updates_totals(self, collector: TensorMetricsCollector):
        """测试结束回合更新累计"""
        collector.record_tensor_trigger(5)
        collector.record_ai_fallback(2)
        collector.current.mortality_time_ms = 10.0
        
        collector.end_turn(turn=1)
        
        assert collector.total_turns == 1
        assert collector.total_tensor_triggers == 5
        assert collector.total_ai_fallbacks == 2
        assert collector.total_time_ms == 10.0
    
    def test_end_turn_saves_to_history(self, collector: TensorMetricsCollector):
        """测试结束回合保存到历史"""
        collector.record_tensor_trigger(3)
        collector.end_turn()
        
        assert len(collector.history) == 1
        assert collector.history[0].tensor_triggers == 3
    
    def test_end_turn_resets_current(self, collector: TensorMetricsCollector):
        """测试结束回合重置当前"""
        collector.record_tensor_trigger(5)
        collector.end_turn()
        
        assert collector.current.tensor_triggers == 0
    
    def test_history_limit(self, collector: TensorMetricsCollector):
        """测试历史记录上限"""
        collector.max_history = 3
        
        for i in range(5):
            collector.record_tensor_trigger(i)
            collector.end_turn()
        
        assert len(collector.history) == 3
        # 应该保留最后3个
        assert collector.history[0].tensor_triggers == 2
        assert collector.history[1].tensor_triggers == 3
        assert collector.history[2].tensor_triggers == 4
    
    def test_get_statistics_empty(self, collector: TensorMetricsCollector):
        """测试空统计"""
        stats = collector.get_statistics()
        
        assert stats["total_turns"] == 0
        assert stats["avg_time_ms"] == 0.0
        assert stats["tensor_vs_ai_ratio"] == 0.0
    
    def test_get_statistics_with_data(self, collector: TensorMetricsCollector):
        """测试有数据的统计"""
        for i in range(5):
            collector.record_tensor_trigger(2)
            collector.record_ai_fallback(1)
            collector.current.mortality_time_ms = 10.0
            collector.end_turn()
        
        stats = collector.get_statistics()
        
        assert stats["total_turns"] == 5
        assert stats["avg_time_ms"] == 10.0
        assert stats["total_tensor_triggers"] == 10
        assert stats["total_ai_fallbacks"] == 5
        # 10 / (10 + 5) = 0.667
        assert 0.66 <= stats["tensor_vs_ai_ratio"] <= 0.67
    
    def test_get_recent_average_empty(self, collector: TensorMetricsCollector):
        """测试空时的最近平均"""
        avg = collector.get_recent_average()
        
        assert avg["avg_mortality_ms"] == 0.0
        assert avg["avg_total_ms"] == 0.0
    
    def test_get_recent_average_with_data(self, collector: TensorMetricsCollector):
        """测试有数据的最近平均"""
        for i in range(10):
            collector.current.mortality_time_ms = 10.0 + i
            collector.end_turn()
        
        # 最近5回合：15, 16, 17, 18, 19 -> 平均 17
        avg = collector.get_recent_average(n=5)
        
        assert avg["avg_mortality_ms"] == 17.0


class TestGlobalCollector:
    """全局收集器测试"""
    
    def test_get_global_collector_singleton(self):
        """测试全局收集器是单例"""
        reset_global_collector()
        
        c1 = get_global_collector()
        c2 = get_global_collector()
        
        assert c1 is c2
    
    def test_reset_global_collector(self):
        """测试重置全局收集器"""
        c1 = get_global_collector()
        c1.record_tensor_trigger(10)
        
        reset_global_collector()
        
        c2 = get_global_collector()
        assert c2.current.tensor_triggers == 0
        assert c1 is not c2

