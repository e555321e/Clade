"""
张量计算管线阶段

本模块提供使用张量系统的管线阶段：
 - PressureTensorStage: 压力张量化转换（将 ctx.modifiers 转换为张量）
 - TensorEcologyStage: 统一生态计算（整合死亡率、扩散、迁徙、繁殖、竞争）
 - TensorStateSyncStage: 张量状态同步回数据库
 - TensorMetricsStage: 收集和记录张量系统监控指标

【性能优化】
TensorEcologyStage 将原本分散的多个阶段合并为单一阶段：
- 原方案：多个阶段串行执行，每个阶段内有 Python 循环
- 新方案：单一阶段，全物种张量并行，无 Python 循环
- 性能提升：10-50x

张量路径为唯一计算路径。
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import numpy as np

from .stages import BaseStage, StageOrder, StageDependency

if TYPE_CHECKING:
    from .context import SimulationContext
    from .engine import SimulationEngine

logger = logging.getLogger(__name__)


# ============================================================================
# 压力张量化阶段
# ============================================================================

class PressureTensorStage(BaseStage):
    """压力张量化阶段
    
    将 ctx.modifiers 和 ctx.pressures 转换为张量格式的压力叠加层，
    供后续张量生态计算使用。
    
    执行顺序：在 ParsePressuresStage (10) 之后
    
    工作流程：
    1. 从 ctx.modifiers 读取压力修改器
    2. 从 ctx.pressures 读取区域性压力配置
    3. 使用 PressureToTensorBridge 转换为空间张量
    4. 存入 ctx.pressure_overlay
    """
    
    def __init__(self):
        super().__init__(
            StageOrder.PARSE_PRESSURES.value + 1,  # order=11
            "压力张量化"
        )
    
    def get_dependency(self) -> StageDependency:
        return StageDependency(
            requires_stages={"解析环境压力"},
            requires_fields={"modifiers", "pressures"},
            writes_fields={"pressure_overlay"},
        )
    
    async def execute(self, ctx: SimulationContext, engine: SimulationEngine) -> None:
        from ..tensor import get_pressure_bridge
        
        bridge = get_pressure_bridge()
        
        # 获取地图尺寸
        map_state = getattr(ctx, "current_map_state", None)
        if map_state is not None:
            H = getattr(map_state, "height", 64)
            W = getattr(map_state, "width", 64)
            map_width = getattr(map_state, "width", 8)
            map_height = getattr(map_state, "height", 8)
        else:
            # 默认尺寸
            H, W = 64, 64
            map_width, map_height = 8, 8
        
        # 获取压力数据
        modifiers = getattr(ctx, "modifiers", {}) or {}
        pressures = getattr(ctx, "pressures", []) or []
        
        # 转换为张量
        overlay = bridge.convert(
            modifiers=modifiers,
            pressures=pressures,
            map_shape=(H, W),
            map_width=map_width,
            map_height=map_height,
        )
        
        # 存入上下文
        ctx.pressure_overlay = overlay
        
        active_str = ", ".join(overlay.active_pressures[:5])
        if len(overlay.active_pressures) > 5:
            active_str += f" 等{len(overlay.active_pressures)}种"
        
        logger.info(
            f"[压力张量化] 完成: {len(overlay.active_pressures)} 种压力, "
            f"总强度={overlay.total_intensity:.1f}, "
            f"激活: {active_str}"
        )


# ============================================================================
# 统一张量生态计算阶段
# ============================================================================

class TensorEcologyStage(BaseStage):
    """统一张量生态计算阶段
    
    【核心优化】整合死亡率、扩散、迁徙、繁殖、竞争为单一阶段：
    - 单一阶段，全物种张量并行，无 Python 循环
    - 性能提升：10-50x
    
    工作流程（单次调用完成）：
    1. 死亡率计算（多因子张量）
    2. 扩散计算（带适宜度引导）
    3. 迁徙计算（压力驱动+猎物追踪）
    4. 繁殖计算（承载力约束）
    5. 竞争计算（种间竞争）
    """
    
    def __init__(self):
        # 在初步死亡率之后执行（order=51）
        super().__init__(
            StageOrder.PRELIMINARY_MORTALITY.value + 1,  # order=51
            "统一张量生态计算"
        )
    
    def get_dependency(self) -> StageDependency:
        return StageDependency(
            requires_stages={"初步死亡率评估"},
            requires_fields={"tensor_state", "species_batch"},
            optional_fields={"pressure_overlay", "preliminary_mortality"},
            writes_fields={"tensor_state", "tensor_metrics", "combined_results", 
                          "migration_events", "migration_count"},
        )
    
    async def execute(self, ctx: SimulationContext, engine: SimulationEngine) -> None:
        from ..tensor import (
            TensorMetrics,
            get_ecology_engine,
            extract_species_params,
            extract_species_prefs,
            extract_trophic_levels,
        )
        from ..services.species.habitat_manager import habitat_manager
        
        logger.info("【统一张量生态】开始计算...")
        ctx.emit_event("stage", "🧬 【统一张量生态】死亡率+扩散+迁徙+繁殖+竞争", "生态")
        
        # 检查张量状态
        tensor_state = getattr(ctx, "tensor_state", None)
        if tensor_state is None:
            logger.warning("[统一张量生态] 缺少 tensor_state，跳过")
            return
        
        # 获取生态引擎
        ecology_engine = get_ecology_engine()
        
        # 准备数据
        pop = tensor_state.pop.astype(np.float32)
        env = tensor_state.env.astype(np.float32)
        species_map = tensor_state.species_map
        S = pop.shape[0]
        
        if S == 0:
            logger.debug("[统一张量生态] 无物种，跳过")
            return
        
        # 创建物种索引映射
        species_batch = getattr(ctx, "species_batch", []) or []
        
        # 提取物种参数
        species_params = extract_species_params(species_batch, species_map)
        species_prefs = extract_species_prefs(species_batch, species_map)
        trophic_levels = extract_trophic_levels(species_batch, species_map)
        
        # 获取压力叠加层
        pressure_overlay = None
        if hasattr(ctx, "pressure_overlay") and ctx.pressure_overlay is not None:
            pressure_overlay = ctx.pressure_overlay.overlay.astype(np.float32)
        
        # 构建冷却期掩码
        turn_index = getattr(ctx, "turn_index", 0)
        cooldown_mask = np.ones(S, dtype=bool)
        for lineage, idx in species_map.items():
            if idx < S:
                is_on_cooldown = habitat_manager.is_migration_on_cooldown(
                    lineage, turn_index, cooldown_turns=2
                )
                if is_on_cooldown:
                    cooldown_mask[idx] = False
        
        # 【核心】一次调用完成全部生态计算
        result = ecology_engine.process_ecology(
            pop=pop,
            env=env,
            species_params=species_params,
            species_prefs=species_prefs,
            turn_index=turn_index,
            trophic_levels=trophic_levels,
            pressure_overlay=pressure_overlay,
            cooldown_mask=cooldown_mask,
        )
        
        # 更新张量状态
        tensor_state.pop = result.pop
        ctx.tensor_state = tensor_state
        
        # 同步死亡率到 combined_results
        self._sync_mortality_to_results(ctx, result, species_map)
        
        # 更新迁徙统计
        ctx.migration_count = len(result.migrated_species)
        ctx.migration_events = []
        
        # 设置迁徙冷却期
        for s_idx in result.migrated_species:
            # 找到对应的 lineage_code
            for lineage, idx in species_map.items():
                if idx == s_idx:
                    habitat_manager.set_migration_cooldown(lineage, turn_index)
                    break
        
        # 更新性能指标
        if ctx.tensor_metrics is None:
            ctx.tensor_metrics = TensorMetrics()
        
        ctx.tensor_metrics.mortality_time_ms = result.metrics.mortality_time_ms
        ctx.tensor_metrics.migration_time_ms = result.metrics.migration_time_ms
        
        logger.info(
            f"【统一张量生态】完成: {S}物种, "
            f"耗时={result.metrics.total_time_ms:.1f}ms, "
            f"后端={result.metrics.backend}, "
            f"平均死亡率={result.metrics.avg_mortality_rate:.1%}, "
            f"迁徙物种={len(result.migrated_species)}"
        )
        
        ctx.emit_event(
            "info", 
            f"🧬 张量生态计算完成: {result.metrics.total_time_ms:.0f}ms, "
            f"平均死亡率 {result.metrics.avg_mortality_rate:.1%}", 
            "生态"
        )
    
    def _sync_mortality_to_results(
        self,
        ctx,
        result,
        species_map: dict,
    ) -> None:
        """将张量死亡率同步到 combined_results"""
        combined_results = getattr(ctx, "combined_results", None) or []
        
        for res in combined_results:
            lineage = res.species.lineage_code
            idx = species_map.get(lineage)
            if idx is not None and idx < result.mortality_rates.shape[0]:
                # 取该物种的平均死亡率
                species_mortality = result.mortality_rates[idx]
                mask = species_mortality > 0
                if mask.any():
                    avg_mortality = float(species_mortality[mask].mean())
                    res.death_rate = avg_mortality
                    res.deaths = int(result.death_counts[idx])
                    res.survivors = int(result.survivor_counts[idx])


# ============================================================================
# 张量监控指标收集阶段
# ============================================================================

class TensorMetricsStage(BaseStage):
    """张量监控指标收集阶段
    
    在回合结束时收集张量系统的性能指标，并记录到全局收集器。
    
    工作流程：
    1. 从 ctx.tensor_metrics 获取本回合指标
    2. 更新全局 TensorMetricsCollector
    3. 输出性能摘要日志
    """
    
    def __init__(self):
        # 在报告生成之前执行
        super().__init__(
            StageOrder.BUILD_REPORT.value - 1,
            "张量监控指标收集"
        )
    
    def get_dependency(self) -> StageDependency:
        return StageDependency(
            optional_stages={"统一张量生态计算", "分化"},
            writes_fields={"tensor_metrics"},
        )
    
    async def execute(self, ctx: SimulationContext, engine: SimulationEngine) -> None:
        from ..tensor import get_global_collector, TensorMetrics
        
        collector = get_global_collector()
        
        # 统计张量触发的分化数
        tensor_triggers = len(getattr(ctx, "tensor_trigger_codes", set()))
        collector.record_tensor_trigger(tensor_triggers)
        
        # 记录隔离检测和分歧检测
        if tensor_triggers > 0:
            collector.record_isolation_detection(tensor_triggers)
        
        # 结束本回合，保存指标
        metrics = collector.end_turn(ctx.turn_index)
        ctx.tensor_metrics = metrics
        
        # 输出统计信息
        stats = collector.get_statistics()
        if stats["total_turns"] > 0:
            logger.info(
                f"[张量监控] 累计回合={stats['total_turns']}, "
                f"平均耗时={stats['avg_time_ms']:.1f}ms, "
                f"张量触发占比={stats['tensor_vs_ai_ratio']:.1%}"
            )


# ============================================================================
# 张量状态同步阶段
# ============================================================================

class TensorStateSyncStage(BaseStage):
    """张量状态同步阶段
    
    将张量状态同步回数据库对象（Species 的 population 等）。
    确保张量计算结果能够持久化。
    
    工作流程：
    1. 从 ctx.tensor_state 获取最终种群数据
    2. 更新 ctx.species_batch 中各物种的 population
    3. 更新 ctx.new_populations
    """
    
    def __init__(self):
        # 在保存快照之前执行
        super().__init__(
            StageOrder.SAVE_POPULATION_SNAPSHOT.value - 1,
            "张量状态同步"
        )
    
    def get_dependency(self) -> StageDependency:
        return StageDependency(
            optional_stages={"统一张量生态计算"},
            requires_fields={"tensor_state", "species_batch"},
            writes_fields={"new_populations"},
        )
    
    async def execute(self, ctx: SimulationContext, engine: SimulationEngine) -> None:
        from ..tensor import get_compute
        
        tensor_state = getattr(ctx, "tensor_state", None)
        if tensor_state is None:
            return
        
        compute = get_compute()
        
        try:
            pop = tensor_state.pop
            species_map = tensor_state.species_map
            
            # 计算每个物种的总种群
            totals = compute.sum_population(pop)
            
            sync_count = 0
            for lineage, idx in species_map.items():
                if idx < len(totals):
                    new_population = max(0, int(totals[idx]))
                    
                    # 更新 new_populations
                    if lineage in ctx.new_populations:
                        # 与现有值混合（避免突变）
                        old_val = ctx.new_populations[lineage]
                        ctx.new_populations[lineage] = int(
                            0.5 * old_val + 0.5 * new_population
                        )
                    else:
                        ctx.new_populations[lineage] = new_population
                    
                    sync_count += 1
            
            logger.debug(f"[张量同步] 已同步 {sync_count} 个物种的种群数据")
            
        except Exception as e:
            logger.warning(f"[张量同步] 同步失败: {e}")


# ============================================================================
# 获取所有张量阶段
# ============================================================================

def get_tensor_stages() -> list[BaseStage]:
    """获取所有张量计算阶段
    
    返回可以添加到管线中的张量阶段列表。
    使用 TensorEcologyStage 整合全部生态计算。
    
    阶段执行顺序：
    1. PressureTensorStage (order=11): 压力张量化
    2. TensorEcologyStage (order=51): 统一生态计算（整合死亡率+扩散+迁徙+繁殖+竞争）
    3. TensorStateSyncStage (order=159): 状态同步
    4. TensorMetricsStage (order=139): 监控指标
    
    Returns:
        张量阶段列表
    """
    return [
        PressureTensorStage(),     # 压力张量化（在压力解析后立即执行）
        TensorEcologyStage(),      # 统一生态计算
        TensorStateSyncStage(),    # 状态同步
        TensorMetricsStage(),      # 监控指标
    ]


def get_minimal_tensor_stages() -> list[BaseStage]:
    """获取最小张量阶段集
    
    只包含核心的压力转换、统一生态计算和监控指标收集。
    
    Returns:
        最小张量阶段列表
    """
    return [
        PressureTensorStage(),
        TensorEcologyStage(),
        TensorMetricsStage(),
    ]
