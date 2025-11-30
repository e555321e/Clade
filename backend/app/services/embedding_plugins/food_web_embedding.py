"""生态网络向量插件 (MVP)

将食物网关系编码为向量，支持：
- 识别关键物种 (Keystone Species)
- 生态稳定性分析
- 灭绝后的补位预测

数据契约：
- 优先字段: food_web_analysis (来自 FoodWebStage)
- 降级字段: all_species + trophic_level + prey_species
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...simulation.context import SimulationContext

import logging

logger = logging.getLogger(__name__)


@dataclass
class EcologicalPosition:
    """物种生态网络位置"""
    lineage_code: str
    predators: list[str] = field(default_factory=list)
    prey: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    trophic_level: float = 2.0
    
    def to_text(self) -> str:
        """转换为向量化文本"""
        parts = [f"营养级 {self.trophic_level:.1f} 的物种"]
        
        if self.prey:
            parts.append(f"捕食 {len(self.prey)} 种生物")
        if self.predators:
            parts.append(f"被 {len(self.predators)} 种生物捕食")
        if self.competitors:
            parts.append(f"与 {len(self.competitors)} 种生物竞争")
        
        # 生态角色描述
        if self.trophic_level >= 4:
            parts.append("顶级掠食者")
        elif self.trophic_level >= 3:
            parts.append("中级捕食者")
        elif self.trophic_level >= 2:
            parts.append("初级消费者")
        else:
            parts.append("生产者")
        
        degree = len(self.prey) + len(self.predators) + len(self.competitors)
        if degree > 10:
            parts.append("高连接度物种")
        elif degree < 3:
            parts.append("低连接度物种")
        
        return "; ".join(parts)
    
    @property
    def degree(self) -> int:
        """网络度（连接总数）"""
        return len(self.predators) + len(self.prey) + len(self.competitors)


@register_plugin("food_web")
class FoodWebEmbeddingPlugin(EmbeddingPlugin):
    """生态网络向量插件
    
    MVP 功能:
    1. 从食物网数据构建生态位置
    2. 构建向量索引
    3. 识别关键物种
    
    数据质量要求:
    - 优先使用 food_web_analysis（FoodWebStage 输出）
    - 降级使用 all_species + prey_species
    4. 灭绝补位预测
    """
    
    # 优先使用 food_web_analysis，降级到 all_species
    required_context_fields = {"all_species"}
    
    @property
    def name(self) -> str:
        return "food_web"
    
    def _do_initialize(self) -> None:
        """初始化"""
        self._position_cache: dict[str, EcologicalPosition] = {}
        self._using_fallback = False
    
    def _check_data_quality(self, ctx: 'SimulationContext') -> dict[str, list[str]]:
        """检查数据质量"""
        warnings = []
        missing_optional = []
        
        # 检查是否有食物网分析数据
        has_food_web = getattr(ctx, 'food_web_analysis', None) is not None
        has_trophic = getattr(ctx, 'trophic_interactions', None) and len(ctx.trophic_interactions) > 0
        
        if not has_food_web and not has_trophic:
            missing_optional.append("food_web_analysis")
            missing_optional.append("trophic_interactions")
            warnings.append("无食物网分析数据，将基于 prey_species 构建简化网络")
            self._using_fallback = True
        else:
            self._using_fallback = False
        
        # 检查物种是否有 prey_species
        if ctx.all_species:
            missing_prey = sum(1 for sp in ctx.all_species[:20] 
                              if not getattr(sp, 'prey_species', None))
            if missing_prey > 10:
                warnings.append(f"{missing_prey}/20 物种缺少 prey_species，网络连接将不完整")
        
        return {"warnings": warnings, "missing_optional": missing_optional}
    
    def build_ecological_positions(
        self, 
        ctx: 'SimulationContext'
    ) -> dict[str, EcologicalPosition]:
        """从 Context 构建生态位置信息
        
        优先使用 food_web_analysis，降级到基于 trophic_level 推断
        """
        positions: dict[str, EcologicalPosition] = {}
        species_list = ctx.all_species or []
        
        if not species_list:
            return positions
        
        # 初始化所有物种的位置
        for sp in species_list:
            positions[sp.lineage_code] = EcologicalPosition(
                lineage_code=sp.lineage_code,
                trophic_level=getattr(sp, 'trophic_level', 2.0),
            )
        
        # 尝试从 food_web_analysis 获取详细信息
        fwa = getattr(ctx, 'food_web_analysis', None)
        if fwa:
            # 使用 FoodWebAnalysis 的数据
            for code, pos in positions.items():
                # 从关系数据中提取
                pass  # 具体字段依赖 FoodWebAnalysis 的结构
        
        # 降级: 从物种的 prey_species 属性构建
        for sp in species_list:
            code = sp.lineage_code
            if code not in positions:
                continue
            
            # 获取猎物列表
            prey_species = getattr(sp, 'prey_species', None) or []
            if isinstance(prey_species, list):
                for prey_code in prey_species:
                    if isinstance(prey_code, str):
                        positions[code].prey.append(prey_code)
                        # 反向记录被捕食关系
                        if prey_code in positions:
                            positions[prey_code].predators.append(code)
        
        # 推断竞争关系（相同营养级的物种）
        by_trophic: dict[int, list[str]] = {}
        for code, pos in positions.items():
            level = round(pos.trophic_level)
            if level not in by_trophic:
                by_trophic[level] = []
            by_trophic[level].append(code)
        
        for level, codes in by_trophic.items():
            if len(codes) > 1:
                for i, code_a in enumerate(codes):
                    for code_b in codes[i+1:]:
                        positions[code_a].competitors.append(code_b)
                        positions[code_b].competitors.append(code_a)
        
        self._position_cache = positions
        return positions
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建生态网络向量索引"""
        store = self._get_vector_store()
        
        positions = self.build_ecological_positions(ctx)
        if not positions:
            return 0
        
        texts = []
        ids = []
        metadata_list = []
        
        for code, pos in positions.items():
            texts.append(pos.to_text())
            ids.append(code)
            metadata_list.append({
                "degree": pos.degree,
                "trophic_level": pos.trophic_level,
                "predator_count": len(pos.predators),
                "prey_count": len(pos.prey),
                "competitor_count": len(pos.competitors),
            })
        
        vectors = self._embed_texts(texts)
        if not vectors:
            return 0
        
        return store.add_batch(ids, vectors, metadata_list)
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索生态位置相似的物种"""
        store = self._get_vector_store(create=False)
        if not store or store.size == 0:
            return []
        
        query_vec = self.embeddings.embed_single(query)
        results = store.search(query_vec, top_k)
        self._stats.searches += 1
        
        return [
            {
                "lineage_code": r.id,
                "similarity": round(r.score, 3),
                **r.metadata
            }
            for r in results
        ]
    
    def find_keystone_species(self, top_k: int = 5) -> list[dict[str, Any]]:
        """识别关键物种
        
        关键物种特征：
        1. 高网络度（连接多个物种）
        2. 中等营养级（连接上下层）
        3. 在向量空间中接近中心
        """
        if not self._position_cache:
            return []
        
        candidates = []
        
        for code, pos in self._position_cache.items():
            # 计算关键度分数
            degree_score = min(1.0, pos.degree / 10)  # 连接度归一化
            
            # 中间营养级更关键（2-3 级）
            trophic_score = 1.0 - abs(pos.trophic_level - 2.5) / 2.5
            trophic_score = max(0, trophic_score)
            
            # 综合评分
            keystone_score = degree_score * 0.6 + trophic_score * 0.4
            
            candidates.append({
                "lineage_code": code,
                "keystone_score": round(keystone_score, 3),
                "degree": pos.degree,
                "trophic_level": pos.trophic_level,
            })
        
        candidates.sort(key=lambda x: x["keystone_score"], reverse=True)
        return candidates[:top_k]
    
    def find_replacement_candidates(
        self, 
        extinct_code: str, 
        top_k: int = 3
    ) -> list[dict[str, Any]]:
        """为灭绝物种寻找潜在补位物种"""
        store = self._get_vector_store(create=False)
        if not store:
            return []
        
        extinct_vec = store.get(extinct_code)
        if extinct_vec is None:
            # 如果没有向量，尝试从缓存获取位置信息
            extinct_pos = self._position_cache.get(extinct_code)
            if not extinct_pos:
                return []
            
            # 用位置描述生成向量
            extinct_vec = self.embeddings.embed_single(extinct_pos.to_text())
        
        results = store.search(extinct_vec, top_k + 1, exclude_ids={extinct_code})
        
        return [
            {
                "lineage_code": r.id,
                "similarity": round(r.score, 3),
                "replacement_potential": round(r.score * 0.8, 3),
                **r.metadata
            }
            for r in results[:top_k]
        ]
    
    def calculate_ecosystem_stability(self) -> dict[str, float]:
        """计算生态系统稳定性指标"""
        if not self._position_cache:
            return {"connectance": 0, "average_degree": 0, "species_count": 0}
        
        n = len(self._position_cache)
        total_connections = sum(p.degree for p in self._position_cache.values())
        max_connections = n * (n - 1)  # 完全图的边数
        
        connectance = total_connections / max_connections if max_connections > 0 else 0
        average_degree = total_connections / n if n > 0 else 0
        
        # 营养级分布均匀度
        trophic_levels = [p.trophic_level for p in self._position_cache.values()]
        if trophic_levels:
            import numpy as np
            trophic_std = float(np.std(trophic_levels))
        else:
            trophic_std = 0
        
        return {
            "connectance": round(connectance, 4),
            "average_degree": round(average_degree, 2),
            "species_count": n,
            "trophic_level_std": round(trophic_std, 2),
        }
    
    def get_network_summary(self) -> dict[str, Any]:
        """获取网络摘要"""
        stability = self.calculate_ecosystem_stability()
        keystones = self.find_keystone_species(top_k=3)
        
        return {
            "stability": stability,
            "top_keystones": keystones,
            "cached_positions": len(self._position_cache),
        }

