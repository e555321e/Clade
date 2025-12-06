"""
Turn Report Service - 回合报告服务

构建每回合的详细报告。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...schemas.responses import TurnReport, SpeciesSnapshot
    from ..species.trophic_interaction import TrophicInteractionService

from ...schemas.responses import SpeciesSnapshot, EcologicalRealismSnapshot, EcologicalRealismSummary
from ...core.config import get_settings
from ...simulation.constants import get_time_config

logger = logging.getLogger(__name__)


class TurnReportService:
    """回合报告服务
    
    负责构建每回合的详细报告。
    """
    
    def __init__(
        self,
        report_builder: Any,
        environment_repository: Any,
        trophic_service: "TrophicInteractionService",
        emit_event_fn: Callable[[str, str, str], None] | None = None,
    ):
        self.report_builder = report_builder
        self.environment_repository = environment_repository
        self.trophic_service = trophic_service
        self.emit_event_fn = emit_event_fn
    
    def _emit_event(self, event_type: str, message: str, category: str = "报告"):
        """发送事件"""
        if self.emit_event_fn:
            try:
                self.emit_event_fn(event_type, message, category)
            except Exception:
                pass
    
    def _get_ecological_role(self, trophic_level: float) -> str:
        """根据营养级确定生态角色"""
        if trophic_level < 1.5:
            return "生产者"
        elif trophic_level < 2.5:
            return "初级消费者"
        elif trophic_level < 3.5:
            return "次级消费者"
        elif trophic_level < 4.5:
            return "高级消费者"
        else:
            return "顶级掠食者"
    
    def _build_ecological_realism_snapshot(
        self,
        lineage_code: str,
        ecological_realism_data: Dict[str, Any] | None,
    ) -> EcologicalRealismSnapshot | None:
        """构建物种的生态拟真快照"""
        if not ecological_realism_data:
            return None
        
        allee_results = ecological_realism_data.get("allee_results", {})
        disease_results = ecological_realism_data.get("disease_results", {})
        env_modifiers = ecological_realism_data.get("env_modifiers", {})
        assimilation = ecological_realism_data.get("assimilation_efficiencies", {})
        adaptation = ecological_realism_data.get("adaptation_penalties", {})
        mutualism_benefits = ecological_realism_data.get("mutualism_benefits", {})
        mutualism_links = ecological_realism_data.get("mutualism_links", [])
        
        # 获取该物种的数据
        allee = allee_results.get(lineage_code, {})
        disease = disease_results.get(lineage_code, {})
        
        # 获取共生伙伴
        partners = []
        for link in mutualism_links:
            if link.get("species_a") == lineage_code:
                partners.append(link.get("species_b", ""))
            elif link.get("species_b") == lineage_code:
                partners.append(link.get("species_a", ""))
        
        return EcologicalRealismSnapshot(
            is_below_mvp=allee.get("is_below_mvp", False),
            allee_reproduction_modifier=allee.get("reproduction_modifier", 1.0),
            disease_pressure=disease.get("disease_pressure", 0.0),
            disease_mortality_modifier=disease.get("mortality_modifier", 0.0),
            env_fluctuation_modifier=env_modifiers.get(lineage_code, 1.0),
            assimilation_efficiency=assimilation.get(lineage_code, 0.10),
            adaptation_penalty=adaptation.get(lineage_code, 0.0),
            mutualism_benefit=mutualism_benefits.get(lineage_code, 0.0),
            mutualism_partners=partners,
        )
    
    def _build_ecological_realism_summary(
        self,
        species_data: List[Dict],
        ecological_realism_data: Dict[str, Any] | None,
    ) -> EcologicalRealismSummary | None:
        """构建生态拟真系统整体统计"""
        if not ecological_realism_data:
            return None
        
        allee_results = ecological_realism_data.get("allee_results", {})
        disease_results = ecological_realism_data.get("disease_results", {})
        env_modifiers = ecological_realism_data.get("env_modifiers", {})
        adaptation = ecological_realism_data.get("adaptation_penalties", {})
        mutualism_links = ecological_realism_data.get("mutualism_links", [])
        mutualism_benefits = ecological_realism_data.get("mutualism_benefits", {})
        
        # 统计受影响的物种
        allee_affected = [code for code, data in allee_results.items() if data.get("is_below_mvp", False)]
        disease_affected = [code for code, data in disease_results.items() if data.get("disease_pressure", 0) > 0.1]
        adaptation_stressed = [code for code, pen in adaptation.items() if pen > 0.05]
        
        # 计算平均值
        disease_pressures = [d.get("disease_pressure", 0) for d in disease_results.values()]
        avg_disease = sum(disease_pressures) / len(disease_pressures) if disease_pressures else 0.0
        
        env_vals = list(env_modifiers.values())
        avg_env = sum(env_vals) / len(env_vals) if env_vals else 1.0
        
        # 统计共生物种
        mutualism_species = set()
        for link in mutualism_links:
            mutualism_species.add(link.get("species_a", ""))
            mutualism_species.add(link.get("species_b", ""))
        mutualism_species.discard("")
        
        return EcologicalRealismSummary(
            allee_affected_count=len(allee_affected),
            allee_affected_species=allee_affected[:10],  # 最多显示10个
            disease_affected_count=len(disease_affected),
            avg_disease_pressure=avg_disease,
            mutualism_links_count=len(mutualism_links),
            mutualism_species_count=len(mutualism_species),
            adaptation_stressed_count=len(adaptation_stressed),
            avg_env_modifier=avg_env,
        )
    
    def _build_simple_narrative(
        self,
        turn_index: int,
        species_data: List[Dict],
        pressures: List[Any],
        branching_events: List[Any] | None = None,
        major_events: List[Any] | None = None,
        migration_events: List[Any] | None = None,
        reemergence_events: List[Any] | None = None,
        gene_diversity_events: List[Dict] | None = None,
    ) -> str:
        """构建简单模式下的丰富叙事（不使用 LLM）"""
        lines: List[str] = []
        
        # 获取当前时代信息
        time_config = get_time_config(turn_index)
        years_per_turn = time_config["years_per_turn"]
        era_name = time_config["era_name"]
        current_year = time_config["current_year"]
        
        # 格式化时间跨度显示
        if years_per_turn >= 1_000_000:
            time_span_str = f"{years_per_turn // 1_000_000} 百万年"
        else:
            time_span_str = f"{years_per_turn // 10_000} 万年"
        
        # 格式化当前年份显示
        if current_year < 0:
            if abs(current_year) >= 100_000_000:
                year_str = f"{abs(current_year) / 100_000_000:.1f} 亿年前"
            else:
                year_str = f"{abs(current_year) / 1_000_000:.1f} 百万年前"
        else:
            year_str = "现代"
        
        # ═══ 标题 ═══
        lines.append(f"## 🕐 第 {turn_index} 回合")
        lines.append(f"**{era_name}** · {year_str} · {time_span_str}/回合")
        lines.append("")
        
        # ═══ 环境状况 ═══
        lines.append("### 🌍 环境状况")
        if pressures:
            for p in pressures:
                if hasattr(p, 'narrative') and p.narrative:
                    lines.append(f"- {p.narrative}")
                elif hasattr(p, 'kind') and hasattr(p, 'intensity'):
                    intensity_desc = "轻微" if p.intensity < 0.3 else "中等" if p.intensity < 0.6 else "强烈"
                    lines.append(f"- **{p.kind}** ({intensity_desc}，强度 {p.intensity:.1f})")
        else:
            lines.append("- 环境相对稳定，无显著压力变化")
        lines.append("")
        
        # ═══ 生态概况 ═══
        alive_species = [s for s in species_data if s.get("status") == "alive"]
        extinct_species = [s for s in species_data if s.get("status") == "extinct"]
        
        total_population = sum(s.get("population", 0) for s in alive_species)
        total_deaths = sum(s.get("deaths", 0) for s in species_data)
        total_births = sum(s.get("births", 0) for s in species_data)
        
        lines.append("### 📊 生态概况")
        lines.append(f"- **存活物种**: {len(alive_species)} 种")
        lines.append(f"- **总生物量**: {total_population:,} 个体")
        
        if total_births > 0 or total_deaths > 0:
            net_change = total_births - total_deaths
            change_icon = "📈" if net_change > 0 else "📉" if net_change < 0 else "➡️"
            lines.append(f"- **本回合变动**: 出生 +{total_births:,} / 死亡 -{total_deaths:,} ({change_icon} 净变化 {net_change:+,})")
        
        # 计算平均死亡率
        death_rates = [s.get("death_rate", 0) for s in alive_species if s.get("deaths", 0) > 0]
        if death_rates:
            avg_death_rate = sum(death_rates) / len(death_rates)
            rate_desc = "稳定" if avg_death_rate < 0.15 else "略高" if avg_death_rate < 0.3 else "较高" if avg_death_rate < 0.5 else "危机"
            lines.append(f"- **平均死亡率**: {avg_death_rate:.1%} ({rate_desc})")
        lines.append("")
        
        # ═══ 重大事件 ═══
        has_events = False
        
        # 物种分化
        if branching_events:
            if not has_events:
                lines.append("### ⚡ 本回合事件")
                has_events = True
            lines.append("")
            lines.append("**🧬 物种分化**")
            for b in branching_events[:5]:
                parent = getattr(b, 'parent_lineage', '?')
                child = getattr(b, 'new_lineage', '?') or getattr(b, 'child_code', '?')
                desc = getattr(b, 'description', '')
                child_name = getattr(b, 'child_name', '')
                
                if child_name:
                    lines.append(f"> `{parent}` → `{child}` **{child_name}**")
                else:
                    lines.append(f"> `{parent}` → `{child}`")
                if desc:
                    lines.append(f"> _{desc[:80]}{'...' if len(desc) > 80 else ''}_")
                lines.append("")
        
        # 灭绝事件
        new_extinct = [s for s in extinct_species if s.get("deaths", 0) > 0]
        if new_extinct:
            if not has_events:
                lines.append("### ⚡ 本回合事件")
                has_events = True
            lines.append("")
            lines.append("**💀 物种灭绝**")
            for s in new_extinct[:3]:
                lines.append(f"> **{s.get('common_name', '未知')}** (*{s.get('latin_name', '')}*) 走向灭绝")
            lines.append("")
        
        # 重大事件
        if major_events:
            if not has_events:
                lines.append("### ⚡ 本回合事件")
                has_events = True
            lines.append("")
            lines.append("**🌋 环境事件**")
            for e in major_events[:3]:
                desc = getattr(e, 'description', str(e))
                lines.append(f"> {desc}")
            lines.append("")
        
        # 迁徙事件
        if migration_events:
            if not has_events:
                lines.append("### ⚡ 本回合事件")
                has_events = True
            lines.append("")
            lines.append(f"**🦅 物种迁徙**: 发生了 {len(migration_events)} 次迁徙活动")
            lines.append("")
        
        # 物种重现
        if reemergence_events:
            if not has_events:
                lines.append("### ⚡ 本回合事件")
                has_events = True
            lines.append("")
            lines.append(f"**🔄 物种重现**: {len(reemergence_events)} 个物种重新活跃")
            lines.append("")

        # 基因多样性变动
        if gene_diversity_events:
            if not has_events:
                lines.append("### ⚡ 本回合事件")
                has_events = True
            lines.append("")
            lines.append("**🧬 基因多样性变动**")
            for evt in gene_diversity_events[:6]:
                code = evt.get("lineage_code", "?")
                name = evt.get("name", code)
                old = evt.get("old", 0.0)
                new = evt.get("new", 0.0)
                reason = evt.get("reason", "自然演化")
                lines.append(f"- {name} ({code}): {old:.2f} → {new:.2f}（{reason}）")
            lines.append("")
        
        if not has_events:
            lines.append("### ⚡ 本回合事件")
            lines.append("- 未发生重大事件，生态系统平稳运转")
            lines.append("")
        
        # ═══ 物种动态 ═══
        lines.append("### 🐾 物种动态")
        
        # 按状态和变化率排序，展示关键物种
        # 1. 表现最好的（死亡率最低）
        thriving = sorted(
            [s for s in alive_species if s.get("deaths", 0) > 0],
            key=lambda x: x.get("death_rate", 1)
        )[:2]
        
        # 2. 面临压力的（死亡率最高）
        struggling = sorted(
            [s for s in alive_species if s.get("death_rate", 0) > 0.3],
            key=lambda x: -x.get("death_rate", 0)
        )[:2]
        
        # 3. 主导物种（占比最高）
        dominant = sorted(
            alive_species,
            key=lambda x: -x.get("population_share", 0)
        )[:2]
        
        if thriving:
            lines.append("")
            lines.append("**🌟 适应良好**")
            for s in thriving:
                dr = s.get("death_rate", 0)
                lines.append(f"- **{s.get('common_name')}** (`{s.get('lineage_code')}`) — 死亡率 {dr:.1%}，种群稳健")
        
        if struggling:
            lines.append("")
            lines.append("**⚠️ 面临压力**")
            for s in struggling:
                dr = s.get("death_rate", 0)
                pop = s.get("population", 0)
                lines.append(f"- **{s.get('common_name')}** (`{s.get('lineage_code')}`) — 死亡率 {dr:.1%}，剩余 {pop:,} 个体")
        
        if dominant and not thriving and not struggling:
            lines.append("")
            lines.append("**👑 主导物种**")
            for s in dominant:
                share = s.get("population_share", 0)
                pop = s.get("population", 0)
                lines.append(f"- **{s.get('common_name')}** — 占生物量 {share:.1%}，共 {pop:,} 个体")
        
        lines.append("")
        
        # ═══ 小结 ═══
        lines.append("---")
        # 根据情况生成小结
        if branching_events:
            lines.append(f"*本回合见证了 {len(branching_events)} 次物种分化，生命多样性持续扩展。*")
        elif new_extinct:
            lines.append(f"*{len(new_extinct)} 个物种在本回合中消逝，自然选择无情地筛选着适应者。*")
        elif total_deaths > total_births:
            lines.append("*本回合生态系统承受了一定压力，整体种群数量有所下降。*")
        elif total_births > total_deaths * 1.5:
            lines.append("*本回合生态繁荣，物种繁衍旺盛。*")
        else:
            lines.append("*生态系统保持动态平衡，物种在竞争与共存中延续。*")
        
        return "\n".join(lines)
    
    async def build_report(
        self,
        turn_index: int,
        mortality_results: List[Any],
        pressures: List[Any],
        branching_events: List[Any],
        background_summary: Any = None,
        reemergence_events: List[Any] | None = None,
        major_events: List[Any] | None = None,
        map_changes: List[Any] | None = None,
        migration_events: List[Any] | None = None,
        stream_callback: Callable[[str], Coroutine[Any, Any, None]] | None = None,
        all_species: List[Any] | None = None,
        ecological_realism_data: Dict[str, Any] | None = None,  # 【新增】生态拟真数据
        gene_diversity_events: List[Dict] | None = None,
    ) -> "TurnReport":
        """构建回合报告
        
        Args:
            turn_index: 回合索引
            mortality_results: 死亡率结果
            pressures: 压力列表
            branching_events: 分化事件
            background_summary: 背景物种摘要
            reemergence_events: 重现事件
            major_events: 重大事件
            map_changes: 地图变化
            migration_events: 迁徙事件
            stream_callback: 流式输出回调
            all_species: 当前所有物种列表（从模拟上下文传入，避免数据库会话问题）
            
        Returns:
            TurnReport
        """
        from ...schemas.responses import TurnReport
        
        self._emit_event("info", "构建回合报告...", "报告")
        
        # 构建压力摘要
        pressure_summary = "环境稳定"
        if pressures:
            pressure_parts = []
            for p in pressures:
                if hasattr(p, 'kind') and hasattr(p, 'intensity'):
                    pressure_parts.append(f"{p.kind}: {p.intensity:.1f}")
            if pressure_parts:
                pressure_summary = ", ".join(pressure_parts)
        
        # 构建物种数据 - 使用传入的物种列表（避免数据库会话隔离问题）
        # 如果没有传入，才从数据库查询（向后兼容）
        if all_species is None:
            from ...repositories.species_repository import species_repository
            all_species = species_repository.list_species()
            logger.warning("[TurnReport] 未传入 all_species，从数据库重新查询（可能数据不完整）")
        
        # 构建 mortality_results 的查找字典
        mortality_lookup: Dict[str, Any] = {}
        for result in mortality_results:
            if hasattr(result, 'species'):
                mortality_lookup[result.species.lineage_code] = result
        
        # 计算总生物量（只计算存活物种）
        total_population = sum(
            sp.morphology_stats.get("population", 0) or 0
            for sp in all_species
            if sp.status == "alive"
        ) or 1  # 避免除零
        
        species_data = []
        for species in all_species:
            pop = species.morphology_stats.get("population", 0) or 0
            
            # 尝试从 mortality_results 获取详细信息
            mortality_result = mortality_lookup.get(species.lineage_code)
            
            if mortality_result:
                # 有死亡率计算结果，使用更详细的数据
                pop = getattr(mortality_result, 'final_population', 0) or pop
                initial_pop = getattr(mortality_result, 'initial_population', 0) or pop
                births = getattr(mortality_result, 'births', 0)
                net_change_rate = (pop - initial_pop) / max(1, initial_pop)
                species_data.append({
                    "lineage_code": species.lineage_code,
                    "latin_name": species.latin_name,
                    "common_name": species.common_name,
                    "population": pop,
                    "population_share": pop / total_population if species.status == "alive" else 0,
                    "deaths": getattr(mortality_result, 'deaths', 0),
                    "death_rate": mortality_result.death_rate,
                    "net_change_rate": net_change_rate,
                    "ecological_role": self._get_ecological_role(species.trophic_level),
                    "status": species.status,
                    "notes": getattr(mortality_result, 'notes', []) or [],
                    "niche_overlap": getattr(mortality_result, 'niche_overlap', None),
                    "resource_pressure": getattr(mortality_result, 'resource_pressure', None),
                    "is_background": getattr(mortality_result, 'is_background', False),
                    "tier": getattr(mortality_result, 'tier', None),
                    "trophic_level": species.trophic_level,
                    "grazing_pressure": getattr(mortality_result, 'grazing_pressure', None),
                    "predation_pressure": getattr(mortality_result, 'predation_pressure', None),
                    "ai_narrative": getattr(mortality_result, 'ai_narrative', None),
                    "initial_population": initial_pop,
                    "births": births,
                    "survivors": getattr(mortality_result, 'survivors', 0),
                    # 【修复】地块分布统计
                    "total_tiles": getattr(mortality_result, 'total_tiles', 0),
                    "healthy_tiles": getattr(mortality_result, 'healthy_tiles', 0),
                    "warning_tiles": getattr(mortality_result, 'warning_tiles', 0),
                    "critical_tiles": getattr(mortality_result, 'critical_tiles', 0),
                    "best_tile_rate": getattr(mortality_result, 'best_tile_rate', 0.0),
                    "worst_tile_rate": getattr(mortality_result, 'worst_tile_rate', 1.0),
                    "has_refuge": getattr(mortality_result, 'has_refuge', True),
                    "distribution_status": getattr(mortality_result, 'distribution_status', ''),
                    # 【新增】生态拟真数据
                    "ecological_realism": self._build_ecological_realism_snapshot(
                        species.lineage_code, ecological_realism_data
                    ),
                })
            else:
                # 没有死亡率计算结果（新分化的物种或其他情况），使用基础数据
                species_data.append({
                    "lineage_code": species.lineage_code,
                    "latin_name": species.latin_name,
                    "common_name": species.common_name,
                    "population": pop,
                    "population_share": pop / total_population if species.status == "alive" else 0,
                    "deaths": 0,
                    "death_rate": 0.0,
                    "net_change_rate": 0.0,
                    "ecological_role": self._get_ecological_role(species.trophic_level),
                    "status": species.status,
                    "notes": [],
                    "niche_overlap": None,
                    "resource_pressure": None,
                    "is_background": species.is_background,
                    "tier": None,
                    "trophic_level": species.trophic_level,
                    "grazing_pressure": None,
                    "predation_pressure": None,
                    "ai_narrative": None,
                    "initial_population": pop,
                    "births": 0,
                    "survivors": pop,
                    # 【修复】地块分布统计（新物种无数据时给默认值）
                    "total_tiles": 0,
                    "healthy_tiles": 0,
                    "warning_tiles": 0,
                    "critical_tiles": 0,
                    "best_tile_rate": 0.0,
                    "worst_tile_rate": 1.0,
                    "has_refuge": True,
                    "distribution_status": "初始",
                    # 【新增】生态拟真数据
                    "ecological_realism": self._build_ecological_realism_snapshot(
                        species.lineage_code, ecological_realism_data
                    ),
                })
        
        logger.info(f"[TurnReport] 族谱物种总数: {len(all_species)}, 存活: {sum(1 for s in species_data if s['status'] == 'alive')}")
        
        # ========== 检查 LLM 回合报告开关 ==========
        # 优先从 UI 配置读取，否则从系统配置读取
        try:
            from pathlib import Path
            settings = get_settings()
            ui_config_path = Path(settings.ui_config_path)
            ui_config = self.environment_repository.load_ui_config(ui_config_path)
            enable_turn_report_llm = ui_config.turn_report_llm_enabled
        except Exception:
            # 回退到系统配置
            settings = get_settings()
            enable_turn_report_llm = settings.enable_turn_report_llm
        
        # 如果开关关闭，直接使用简单模式，不调用 LLM
        if not enable_turn_report_llm:
            logger.info("[TurnReportService] LLM 回合报告已关闭，使用简单模式")
            self._emit_event("info", "📝 LLM 回合报告已关闭", "报告")
            
            narrative = self._build_simple_narrative(
                turn_index=turn_index,
                species_data=species_data,
                pressures=pressures,
                branching_events=branching_events,
                major_events=major_events,
                migration_events=migration_events,
                reemergence_events=reemergence_events,
                gene_diversity_events=gene_diversity_events,
            )
            
            # 简单模式下流式输出
            if stream_callback:
                for char in narrative:
                    await stream_callback(char)
                    await asyncio.sleep(0.01)
            
            return TurnReport(
                turn_index=turn_index,
                narrative=narrative,
                pressures_summary=pressure_summary,
                species=species_data,
                branching_events=branching_events or [],
                major_events=major_events or [],
                ecological_realism=self._build_ecological_realism_summary(species_data, ecological_realism_data),
                gene_diversity_events=gene_diversity_events or [],
            )
        
        # ========== 【修复】调用 LLM 叙事引擎 ==========
        # 将 mortality_results 转换为 SpeciesSnapshot 列表
        species_snapshots: List[SpeciesSnapshot] = []
        for result in mortality_results:
            if hasattr(result, 'species') and hasattr(result, 'death_rate'):
                pop = getattr(result, 'final_population', 0) or result.species.morphology_stats.get("population", 0)
                initial_pop = getattr(result, 'initial_population', 0) or pop
                deaths = getattr(result, 'deaths', 0)
                births = getattr(result, 'births', 0)
                net_change_rate = (pop - initial_pop) / max(1, initial_pop)
                
                species_snapshots.append(SpeciesSnapshot(
                    lineage_code=result.species.lineage_code,
                    latin_name=result.species.latin_name,
                    common_name=result.species.common_name,
                    population=pop,
                    population_share=pop / total_population,
                    deaths=deaths,
                    death_rate=result.death_rate,
                    net_change_rate=net_change_rate,
                    ecological_role=self._get_ecological_role(result.species.trophic_level),
                    status=result.species.status,
                    notes=getattr(result, 'notes', []) or [],
                    niche_overlap=getattr(result, 'niche_overlap', None),
                    resource_pressure=getattr(result, 'resource_pressure', None),
                    is_background=getattr(result, 'is_background', False),
                    tier=getattr(result, 'tier', None),
                    trophic_level=result.species.trophic_level,
                    grazing_pressure=getattr(result, 'grazing_pressure', None),
                    predation_pressure=getattr(result, 'predation_pressure', None),
                    ai_narrative=getattr(result, 'ai_narrative', None),
                    initial_population=initial_pop,
                    births=births,
                    survivors=getattr(result, 'survivors', 0),
                    # 【修复】地块分布统计完整字段
                    total_tiles=getattr(result, 'total_tiles', 0),
                    healthy_tiles=getattr(result, 'healthy_tiles', 0),
                    warning_tiles=getattr(result, 'warning_tiles', 0),
                    critical_tiles=getattr(result, 'critical_tiles', 0),
                    best_tile_rate=getattr(result, 'best_tile_rate', 0.0),
                    worst_tile_rate=getattr(result, 'worst_tile_rate', 1.0),
                    has_refuge=getattr(result, 'has_refuge', True),
                    distribution_status=getattr(result, 'get_distribution_status', lambda: '')() if hasattr(result, 'get_distribution_status') else '',
                ))
        
        # 调用 LLM 叙事引擎生成叙事
        narrative = ""
        try:
            if self.report_builder is not None:
                self._emit_event("info", "🤖 调用 AI 生成回合叙事...", "报告")
                
                narrative = await self.report_builder.build_turn_narrative_async(
                    species=species_snapshots,
                    pressures=pressures or [],
                    background=background_summary,
                    reemergence=reemergence_events,
                    major_events=major_events,
                    map_changes=map_changes,
                    migration_events=migration_events,
                    branching_events=branching_events,
                    stream_callback=stream_callback,
                )
                
                if narrative and len(narrative) > 50:
                    self._emit_event("info", "✅ AI 叙事生成完成", "报告")
                else:
                    self._emit_event("warning", "⚠️ AI 叙事过短，使用简单模式", "报告")
                    narrative = ""
            else:
                logger.warning("[TurnReportService] report_builder 未初始化，跳过 LLM 叙事")
        except asyncio.TimeoutError:
            logger.warning("[TurnReportService] LLM 叙事生成超时")
            self._emit_event("warning", "⏱️ AI 叙事超时", "报告")
            narrative = ""
        except Exception as e:
            logger.error(f"[TurnReportService] LLM 叙事生成失败: {e}")
            self._emit_event("warning", f"⚠️ AI 叙事失败: {e}", "报告")
            narrative = ""
        
        # 如果 LLM 失败，使用丰富的回退叙事
        if not narrative:
            narrative = self._build_simple_narrative(
                turn_index=turn_index,
                species_data=species_data,
                pressures=pressures,
                branching_events=branching_events,
                major_events=major_events,
                migration_events=migration_events,
                reemergence_events=reemergence_events,
                gene_diversity_events=gene_diversity_events,
            )
            
            # 回退模式下流式输出
            if stream_callback:
                for char in narrative:
                    await stream_callback(char)
                    await asyncio.sleep(0.01)

        # 附加基因多样性摘要，确保即便LLM生成也能看到关键数据
        if gene_diversity_events:
            summary_lines = ["", "### 🧬 基因多样性变动"]
            for evt in gene_diversity_events[:8]:
                code = evt.get("lineage_code", "?")
                name = evt.get("name", code)
                old = evt.get("old", 0.0)
                new = evt.get("new", 0.0)
                reason = evt.get("reason", "自然演化")
                summary_lines.append(f"- {name} ({code}): {old:.2f} → {new:.2f}（{reason}）")
            narrative = narrative + "\n" + "\n".join(summary_lines)
        
        return TurnReport(
            turn_index=turn_index,
            narrative=narrative,
            pressures_summary=pressure_summary,
            species=species_data,
            branching_events=branching_events or [],
            major_events=major_events or [],
            ecological_realism=self._build_ecological_realism_summary(species_data, ecological_realism_data),
            gene_diversity_events=gene_diversity_events or [],
        )


def create_turn_report_service(
    report_builder: Any,
    environment_repository: Any,
    trophic_service: "TrophicInteractionService",
    emit_event_fn: Callable[[str, str, str], None] | None = None,
) -> TurnReportService:
    """工厂函数：创建回合报告服务实例"""
    return TurnReportService(
        report_builder=report_builder,
        environment_repository=environment_repository,
        trophic_service=trophic_service,
        emit_event_fn=emit_event_fn,
    )

