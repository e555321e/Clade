"""演化向量空间插件

追踪和分析宏观演化趋势，支持：
- 存储演化方向向量
- 趋势聚类分析
- 收敛演化检测
- 轨迹预测

数据契约：
- 必需字段: all_species
- 可选字段: combined_results, adaptation_events
- 降级策略: 不记录演化事件，仅保留已有索引
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, List
from collections import defaultdict

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...simulation.context import SimulationContext

import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EvolutionEvent:
    """演化事件记录"""
    turn: int
    species_code: str
    species_name: str
    direction_text: str
    cluster_id: int = -1


@dataclass
class EvolutionTrend:
    """演化趋势"""
    trend_id: int
    name: str
    description: str
    species_count: int
    example_species: List[str]
    strength: float


@register_plugin("evolution_space")
class EvolutionSpacePlugin(EmbeddingPlugin):
    """演化向量空间插件
    
    MVP 功能:
    1. 记录演化事件
    2. 构建演化向量索引
    3. 趋势分析（简单分组）
    4. 收敛演化检测
    """
    
    required_context_fields = {"all_species"}
    
    # 预定义演化方向模板
    DIRECTION_TEMPLATES = {
        "cold_adaptation": "向寒冷环境适应，发展保温层、防冻机制",
        "heat_adaptation": "向炎热环境适应，发展散热机制、夜行性",
        "aquatic_transition": "向水生环境过渡，发展水中呼吸、流线型身体",
        "terrestrial_transition": "向陆地环境过渡，发展肺呼吸、四肢",
        "aerial_adaptation": "发展飞行能力，轻量化骨骼、翅膀",
        "size_increase": "体型增大，代谢率降低",
        "size_decrease": "体型缩小，代谢率升高",
        "predator_specialization": "捕食者特化，发展锋利牙齿、敏锐感官",
        "defense_enhancement": "防御强化，发展外壳、毒素、拟态",
        "social_evolution": "社会性演化，发展群体协作、通讯",
    }
    
    @property
    def name(self) -> str:
        return "evolution_space"
    
    def _do_initialize(self) -> None:
        """初始化"""
        self._evolution_events: List[EvolutionEvent] = []
        self._trend_cache: List[EvolutionTrend] = []
        self._template_vectors: dict[str, np.ndarray] = {}
        self._cluster_interval = 5
        self._last_cluster_turn = -1
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建演化事件索引"""
        store = self._get_vector_store()
        
        # 收集新的演化事件
        new_events = self._collect_evolution_events(ctx)
        if not new_events:
            return 0
        
        texts = [e.direction_text for e in new_events]
        vectors = self._embed_texts(texts)
        if not vectors:
            return 0
        
        ids = [f"{e.turn}_{e.species_code}" for e in new_events]
        metadata_list = [
            {
                "turn": e.turn,
                "species_code": e.species_code,
                "species_name": e.species_name,
            }
            for e in new_events
        ]
        
        # 保存事件
        self._evolution_events.extend(new_events)
        
        # 定期更新聚类
        if ctx.turn_index - self._last_cluster_turn >= self._cluster_interval:
            self._update_trends()
            self._last_cluster_turn = ctx.turn_index
        
        return store.add_batch(ids, vectors, metadata_list)
    
    def _collect_evolution_events(self, ctx: 'SimulationContext') -> List[EvolutionEvent]:
        """从上下文收集演化事件"""
        events = []
        
        # 从 combined_results 收集
        for result in (ctx.combined_results or []):
            if not isinstance(result, dict):
                continue
            
            direction = result.get("evolution_direction", result.get("direction", ""))
            if direction:
                if isinstance(direction, list):
                    direction = ", ".join(str(d) for d in direction)
                
                events.append(EvolutionEvent(
                    turn=ctx.turn_index,
                    species_code=result.get("lineage_code", ""),
                    species_name=result.get("common_name", ""),
                    direction_text=str(direction)[:200],
                ))
        
        # 从 adaptation_events 收集
        for event in (ctx.adaptation_events or []):
            if not isinstance(event, dict):
                continue
            
            events.append(EvolutionEvent(
                turn=ctx.turn_index,
                species_code=event.get("species_code", ""),
                species_name=event.get("species_name", ""),
                direction_text=event.get("adaptation_type", "适应性变化"),
            ))
        
        return events
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索相似演化事件"""
        store = self._get_vector_store(create=False)
        if not store or store.size == 0:
            return []
        
        query_vec = self.embeddings.embed_single(query)
        results = store.search(query_vec, top_k)
        self._stats.searches += 1
        
        return [
            {"id": r.id, "similarity": round(r.score, 3), **r.metadata}
            for r in results
        ]
    
    def _update_trends(self) -> None:
        """更新演化趋势（简单分组方法）"""
        if len(self._evolution_events) < 5:
            return
        
        # 确保有模板向量
        if not self._template_vectors:
            self._build_template_vectors()
        
        # 为每个事件分配最接近的模板
        trend_groups: dict[str, list[EvolutionEvent]] = defaultdict(list)
        
        for event in self._evolution_events:
            if not event.direction_text:
                continue
            
            event_vec = np.array(self.embeddings.embed_single(event.direction_text))
            
            best_template = "unknown"
            best_sim = -1
            
            for name, template_vec in self._template_vectors.items():
                sim = self._cosine_similarity(event_vec, template_vec)
                if sim > best_sim:
                    best_sim = sim
                    best_template = name
            
            if best_sim > 0.5:
                event.cluster_id = list(self.DIRECTION_TEMPLATES.keys()).index(best_template)
                trend_groups[best_template].append(event)
        
        # 生成趋势
        self._trend_cache = []
        total_events = len(self._evolution_events)
        
        for i, (name, events) in enumerate(sorted(
            trend_groups.items(), 
            key=lambda x: len(x[1]), 
            reverse=True
        )):
            if not events:
                continue
            
            self._trend_cache.append(EvolutionTrend(
                trend_id=i,
                name=name,
                description=self.DIRECTION_TEMPLATES.get(name, "未知趋势"),
                species_count=len(events),
                example_species=[e.species_name for e in events[:5]],
                strength=len(events) / total_events if total_events > 0 else 0,
            ))
    
    def _build_template_vectors(self) -> None:
        """构建模板向量"""
        for name, desc in self.DIRECTION_TEMPLATES.items():
            vec = self.embeddings.embed_single(desc)
            self._template_vectors[name] = np.array(vec)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def get_current_trends(self, top_k: int = 5) -> list[dict[str, Any]]:
        """获取当前主要演化趋势"""
        if not self._trend_cache:
            self._update_trends()
        
        return [
            {
                "trend_id": t.trend_id,
                "name": t.name,
                "description": t.description,
                "species_count": t.species_count,
                "strength": round(t.strength, 3),
                "examples": t.example_species,
            }
            for t in self._trend_cache[:top_k]
        ]
    
    def predict_species_trajectory(
        self, 
        species: 'Species'
    ) -> list[dict[str, Any]]:
        """预测物种的演化轨迹"""
        # 找到该物种的历史演化事件
        species_events = [
            e for e in self._evolution_events 
            if e.species_code == species.lineage_code
        ]
        
        if not species_events:
            return []
        
        # 收集最近事件的向量
        recent_texts = [e.direction_text for e in species_events[-5:]]
        if not recent_texts:
            return []
        
        recent_vectors = self._embed_texts(recent_texts)
        if not recent_vectors:
            return []
        
        # 计算平均方向
        avg_direction = np.mean(recent_vectors, axis=0)
        
        # 与模板比较
        if not self._template_vectors:
            self._build_template_vectors()
        
        predictions = []
        for name, template_vec in self._template_vectors.items():
            sim = self._cosine_similarity(avg_direction, template_vec)
            if sim > 0.4:
                predictions.append({
                    "direction": name,
                    "description": self.DIRECTION_TEMPLATES[name],
                    "probability": round(sim, 3),
                })
        
        predictions.sort(key=lambda x: x["probability"], reverse=True)
        return predictions[:3]
    
    def detect_convergent_evolution(self, min_species: int = 3) -> list[dict[str, Any]]:
        """检测收敛演化"""
        convergences = []
        
        for trend in self._trend_cache:
            if trend.species_count < min_species:
                continue
            
            # 检查物种是否来自不同谱系
            lineage_prefixes = set()
            for event in self._evolution_events:
                if event.cluster_id == trend.trend_id:
                    prefix = event.species_code.split("_")[0] if "_" in event.species_code else event.species_code[:2]
                    lineage_prefixes.add(prefix)
            
            if len(lineage_prefixes) >= 2:
                convergences.append({
                    "trend": trend.name,
                    "description": trend.description,
                    "species_count": trend.species_count,
                    "lineage_count": len(lineage_prefixes),
                    "examples": trend.example_species,
                })
        
        return convergences
    
    def get_evolution_summary(self) -> dict[str, Any]:
        """获取演化空间摘要"""
        return {
            "total_events": len(self._evolution_events),
            "trends": self.get_current_trends(top_k=5),
            "convergent_evolutions": self.detect_convergent_evolution(),
        }
    
    def export_for_save(self) -> dict[str, Any]:
        """导出数据"""
        base = super().export_for_save()
        base["event_count"] = len(self._evolution_events)
        base["last_cluster_turn"] = self._last_cluster_turn
        return base

