"""Prompt 优化插件

使用向量相似度为 LLM 筛选最相关的上下文，减少 token 消耗。

数据契约：
- 必需字段: all_species
- 可选字段: major_events, pressures
- 降级策略: 仅用物种描述，跳过事件/压力筛选
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, List

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...simulation.context import SimulationContext

import logging

logger = logging.getLogger(__name__)


@dataclass
class PromptContext:
    """优化后的 Prompt 上下文"""
    species_summary: str
    relevant_events: List[str] = field(default_factory=list)
    relevant_pressures: List[str] = field(default_factory=list)
    similar_species_fates: List[str] = field(default_factory=list)
    estimated_tokens: int = 0
    
    def to_prompt_section(self) -> str:
        """转换为 Prompt 文本段落"""
        sections = [f"【物种概要】\n{self.species_summary}"]
        
        if self.relevant_events:
            sections.append("【相关历史事件】\n" + "\n".join(f"- {e}" for e in self.relevant_events))
        
        if self.relevant_pressures:
            sections.append("【当前面临压力】\n" + "\n".join(f"- {p}" for p in self.relevant_pressures))
        
        if self.similar_species_fates:
            sections.append("【相似物种命运参考】\n" + "\n".join(f"- {f}" for f in self.similar_species_fates))
        
        return "\n\n".join(sections)


@register_plugin("prompt_optimizer")
class PromptOptimizerPlugin(EmbeddingPlugin):
    """Prompt 优化插件
    
    MVP 功能:
    1. 为物种构建精简的上下文
    2. 筛选相关事件和压力
    3. 查找相似物种命运
    4. Token 估算和裁剪
    """
    
    DEFAULT_SIMILARITY_THRESHOLD = 0.6
    DEFAULT_MAX_EVENTS = 5
    DEFAULT_MAX_PRESSURES = 3
    DEFAULT_MAX_SIMILAR = 3
    
    required_context_fields = {"all_species"}
    
    @property
    def name(self) -> str:
        return "prompt_optimizer"
    
    def _do_initialize(self) -> None:
        """初始化"""
        self._token_savings_total = 0
        self._optimizations_count = 0
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """索引事件（委托给 EmbeddingService）"""
        events = self._collect_events(ctx)
        if events:
            return self.embeddings.index_events_batch(events)
        return 0
    
    def _collect_events(self, ctx: 'SimulationContext') -> list[dict]:
        """收集事件用于索引"""
        events = []
        
        for i, event in enumerate(ctx.major_events or []):
            if isinstance(event, dict):
                events.append({
                    "id": f"turn_{ctx.turn_index}_{i}",
                    "title": event.get("title", event.get("type", "事件")),
                    "description": event.get("description", str(event))[:500],
                    "metadata": {
                        "turn": ctx.turn_index,
                        "type": event.get("type", "unknown"),
                    }
                })
        
        return events
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索相关事件"""
        results = self.embeddings.search_events(query, top_k)
        self._stats.searches += 1
        return [
            {"id": r.id, "similarity": round(r.score, 3), **r.metadata}
            for r in results
        ]
    
    def build_optimized_context(
        self,
        species: 'Species',
        ctx: 'SimulationContext',
        max_tokens: int = 1000
    ) -> PromptContext:
        """为物种构建优化的 LLM 上下文"""
        # 1. 构建物种摘要
        species_summary = self._build_species_summary(species)
        
        # 2. 搜索相关事件
        species_text = self.embeddings.build_species_text(species)
        relevant_events = self._find_relevant_events(species_text)
        
        # 3. 筛选相关压力
        relevant_pressures = self._find_relevant_pressures(species, ctx)
        
        # 4. 查找相似物种命运
        similar_fates = self._find_similar_fates(species)
        
        # 5. 构建上下文
        context = PromptContext(
            species_summary=species_summary,
            relevant_events=[e[:150] for e in relevant_events],
            relevant_pressures=relevant_pressures,
            similar_species_fates=similar_fates,
        )
        
        # 6. 估算并裁剪
        full_text = context.to_prompt_section()
        context.estimated_tokens = len(full_text) // 2  # 粗略估算
        
        while context.estimated_tokens > max_tokens:
            if context.relevant_events:
                context.relevant_events.pop()
            elif context.similar_species_fates:
                context.similar_species_fates.pop()
            else:
                break
            context.estimated_tokens = len(context.to_prompt_section()) // 2
        
        self._optimizations_count += 1
        return context
    
    def _build_species_summary(self, species: 'Species') -> str:
        """构建简洁的物种摘要"""
        traits = getattr(species, 'abstract_traits', None) or {}
        
        key_traits = []
        for trait, value in traits.items():
            if value > 7:
                key_traits.append(f"高{trait}")
            elif value < 3:
                key_traits.append(f"低{trait}")
        
        lines = [
            f"{species.common_name} ({getattr(species, 'latin_name', '')})",
            f"营养级: {getattr(species, 'trophic_level', 2.0):.1f}, 种群: {getattr(species, 'total_population', 0)}",
        ]
        
        if key_traits:
            lines.append(f"特征: {', '.join(key_traits[:5])}")
        
        return "\n".join(lines)
    
    def _find_relevant_events(self, species_text: str) -> list[str]:
        """查找相关事件"""
        results = self.embeddings.search_events(
            species_text, 
            top_k=self.DEFAULT_MAX_EVENTS,
            threshold=self.DEFAULT_SIMILARITY_THRESHOLD
        )
        return [r.metadata.get("description", r.id)[:200] for r in results]
    
    def _find_relevant_pressures(
        self, 
        species: 'Species', 
        ctx: 'SimulationContext'
    ) -> list[str]:
        """筛选相关压力"""
        relevant = []
        traits = getattr(species, 'abstract_traits', None) or {}
        trophic = getattr(species, 'trophic_level', 2.0)
        
        for pressure in (ctx.pressures or []):
            if not isinstance(pressure, dict):
                continue
            
            p_type = pressure.get("type", "")
            strength = pressure.get("strength", 0.5)
            
            # 温度相关
            if "温度" in p_type or "climate" in p_type.lower():
                if traits.get("耐热性", 5) < 4 or traits.get("耐寒性", 5) < 4:
                    relevant.append(f"{p_type} (强度{strength:.1f}) - 温度敏感")
            
            # 捕食压力
            elif "predation" in p_type.lower() or "捕食" in p_type:
                if trophic < 3:
                    relevant.append(f"{p_type} (强度{strength:.1f}) - 猎物物种")
            
            # 通用压力
            elif strength > 0.7:
                relevant.append(f"{p_type} (强度{strength:.1f})")
        
        return relevant[:self.DEFAULT_MAX_PRESSURES]
    
    def _find_similar_fates(self, species: 'Species') -> list[str]:
        """查找相似物种的命运"""
        fates = []
        
        species_text = self.embeddings.build_species_text(species)
        results = self.embeddings.search_species(
            species_text,
            top_k=self.DEFAULT_MAX_SIMILAR + 1,
            exclude_codes={species.lineage_code}
        )
        
        for r in results[:self.DEFAULT_MAX_SIMILAR]:
            name = r.metadata.get("common_name", r.id)
            status = r.metadata.get("status", "alive")
            
            status_text = {
                "extinct": "已灭绝",
                "endangered": "濒危中",
                "alive": "存活中"
            }.get(status, status)
            
            fates.append(f"{name} {status_text} (相似度{r.score:.2f})")
        
        return fates
    
    def get_optimization_stats(self) -> dict[str, Any]:
        """获取优化统计"""
        return {
            "optimizations_count": self._optimizations_count,
            "token_savings_total": self._token_savings_total,
            **self._stats,
        }

