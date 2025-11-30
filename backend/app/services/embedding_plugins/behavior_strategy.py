"""行为策略向量插件 (MVP)

为物种生成行为策略的向量表示，支持：
- 行为相似物种聚类
- 行为冲突预测
- 行为生态位分析

数据契约：
- 必需字段: all_species (物种列表)
- 推荐字段: abstract_traits (影响向量质量)
- 降级逻辑:
  - 无 abstract_traits: 使用 trophic_level 推断
  - 繁殖率 r: 从 abstract_traits["繁殖力"] 推断，默认 0.2
  
提升向量质量建议:
- abstract_traits 应包含: 繁殖力, 攻击性, 防御性, 运动能力, 社会性
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...simulation.context import SimulationContext

import logging

logger = logging.getLogger(__name__)


@dataclass
class BehaviorProfile:
    """物种行为档案"""
    lineage_code: str
    predation_strategy: str    # 埋伏/追逐/群体协作/滤食/光合
    defense_strategy: str      # 拟态/结群/穴居/毒素/逃跑/外壳
    reproduction_strategy: str # r策略/K策略/中等投资
    activity_pattern: str      # 昼行/夜行/晨昏/全天候
    social_behavior: str       # 独居/配对/小群/大群
    
    def to_text(self) -> str:
        """转换为向量化文本"""
        return f"""捕食策略: {self.predation_strategy}
防御策略: {self.defense_strategy}
繁殖策略: {self.reproduction_strategy}
活动节律: {self.activity_pattern}
社会行为: {self.social_behavior}"""


@register_plugin("behavior_strategy")
class BehaviorStrategyPlugin(EmbeddingPlugin):
    """行为策略向量插件
    
    MVP 功能:
    1. 从物种特征推断行为档案
    2. 构建行为向量索引
    3. 搜索行为相似物种
    4. 检测行为冲突
    """
    
    # 声明依赖的 Context 字段
    required_context_fields = {"all_species"}
    
    # 可选但影响质量的字段
    # 注意: reproduction_r 从 abstract_traits 推断，不是 Species 模型字段
    QUALITY_FIELDS = {"abstract_traits", "trophic_level"}
    
    @property
    def name(self) -> str:
        return "behavior_strategy"
    
    def _do_initialize(self) -> None:
        """初始化"""
        self._profile_cache: dict[str, BehaviorProfile] = {}
        self._quality_issues: list[str] = []
    
    def _check_data_quality(self, ctx: 'SimulationContext') -> dict[str, list[str]]:
        """检查数据质量"""
        warnings = []
        missing_optional = []
        
        if not ctx.all_species:
            return {"warnings": ["无物种数据"], "missing_optional": []}
        
        # 抽样检查（最多检查 10 个）
        sample_size = min(10, len(ctx.all_species))
        missing_traits = 0
        missing_trophic = 0
        low_quality_traits = 0
        
        for sp in ctx.all_species[:sample_size]:
            traits = getattr(sp, 'abstract_traits', None)
            if not traits:
                missing_traits += 1
            elif len(traits) < 3:
                # abstract_traits 存在但内容太少
                low_quality_traits += 1
            if getattr(sp, 'trophic_level', None) is None:
                missing_trophic += 1
        
        if missing_traits > sample_size * 0.5:
            missing_optional.append("abstract_traits")
            warnings.append(
                f"{missing_traits}/{sample_size} 物种缺少 abstract_traits，"
                "行为推断将使用 trophic_level 降级（精度较低）"
            )
        elif low_quality_traits > sample_size * 0.3:
            warnings.append(
                f"{low_quality_traits}/{sample_size} 物种 abstract_traits 内容较少，"
                "建议补充 '繁殖力', '攻击性', '防御性' 等特征"
            )
        
        if missing_trophic > sample_size * 0.3:
            missing_optional.append("trophic_level")
            warnings.append(
                f"{missing_trophic}/{sample_size} 物种缺少 trophic_level，"
                "将使用默认值 2.0"
            )
        
        # 注意: reproduction_r 不是 Species 模型字段，
        # 本插件会从 abstract_traits 推断繁殖率
        
        self._quality_issues = warnings
        return {"warnings": warnings, "missing_optional": missing_optional}
    
    def _estimate_reproduction_r(self, species: 'Species') -> float:
        """估算繁殖率 r
        
        Species 模型没有显式 reproduction_r 字段，
        需要从其他特征推断。
        
        推断逻辑:
        - 从 abstract_traits 的 "繁殖力", "产卵数" 等推断
        - 营养级越高，繁殖率通常越低
        - 默认返回 0.2（中等繁殖策略）
        """
        traits = getattr(species, 'abstract_traits', None) or {}
        trophic = getattr(species, 'trophic_level', 2.0)
        
        # 从特征推断
        fertility = traits.get("繁殖力", traits.get("产卵数", 5))
        
        # 归一化到 0.05-0.5
        base_r = fertility / 10.0
        base_r = max(0.05, min(0.5, base_r))
        
        # 营养级修正（顶级捕食者繁殖慢）
        trophic_factor = 1 - (min(trophic, 5) - 1) * 0.08
        
        return round(base_r * trophic_factor, 3)
    
    def infer_behavior_profile(self, species: 'Species') -> BehaviorProfile:
        """从物种特征推断行为档案
        
        降级逻辑: 仅依赖 trophic_level, abstract_traits
        reproduction_r 从特征推断
        """
        traits = getattr(species, 'abstract_traits', None) or {}
        trophic = getattr(species, 'trophic_level', 2.0)
        reproduction_r = self._estimate_reproduction_r(species)
        
        # 推断捕食策略
        if trophic < 1.5:
            predation = "光合/滤食"
        elif trophic < 2.5:
            predation = "杂食/机会主义"
        elif traits.get("攻击性", 5) > 7:
            if traits.get("社会性", 5) > 6:
                predation = "群体协作捕食"
            else:
                predation = "主动追逐捕食"
        elif traits.get("运动能力", 5) < 4:
            predation = "埋伏捕食"
        else:
            predation = "伏击/机会捕食"
        
        # 推断防御策略
        defense_val = traits.get("防御性", 5)
        mobility_val = traits.get("运动能力", 5)
        social_val = traits.get("社会性", 5)
        
        if defense_val > 7:
            defense = "坚硬外壳/毒素"
        elif mobility_val > 7:
            defense = "高速逃跑"
        elif social_val > 6:
            defense = "结群防御"
        elif mobility_val < 3:
            defense = "穴居/隐藏"
        else:
            defense = "拟态/保护色"
        
        # 推断繁殖策略
        if reproduction_r > 0.3:
            reproduction = "r策略-高繁殖低投资"
        elif reproduction_r < 0.1:
            reproduction = "K策略-低繁殖高投资"
        else:
            reproduction = "中等繁殖-父母抚育"
        
        # 推断活动节律（基于感知能力推断）
        perception = traits.get("感知能力", 5)
        heat_tolerance = traits.get("耐热性", 5)
        
        if perception > 7 and heat_tolerance < 4:
            activity = "夜行性"
        elif heat_tolerance > 7:
            activity = "昼行性"
        else:
            activity = "晨昏活动"
        
        # 推断社会行为
        if social_val > 8:
            social = "大群/社会性"
        elif social_val > 5:
            social = "小群/配对"
        else:
            social = "独居"
        
        return BehaviorProfile(
            lineage_code=species.lineage_code,
            predation_strategy=predation,
            defense_strategy=defense,
            reproduction_strategy=reproduction,
            activity_pattern=activity,
            social_behavior=social,
        )
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建行为策略向量索引"""
        store = self._get_vector_store()
        
        species_list = ctx.all_species or []
        if not species_list:
            return 0
        
        texts = []
        ids = []
        metadata_list = []
        
        for sp in species_list:
            profile = self.infer_behavior_profile(sp)
            self._profile_cache[sp.lineage_code] = profile
            
            texts.append(profile.to_text())
            ids.append(sp.lineage_code)
            metadata_list.append({
                "common_name": getattr(sp, 'common_name', sp.lineage_code),
                "predation": profile.predation_strategy,
                "activity": profile.activity_pattern,
                "social": profile.social_behavior,
            })
        
        vectors = self._embed_texts(texts)
        if not vectors:
            return 0
        
        return store.add_batch(ids, vectors, metadata_list)
    
    def _build_index_fallback(self, ctx: 'SimulationContext') -> int:
        """降级逻辑：无 all_species 时跳过"""
        logger.warning(f"[{self.name}] 无物种数据，跳过索引构建")
        return 0
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索行为相似的物种"""
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
    
    def find_similar_species(
        self, 
        species: 'Species', 
        top_k: int = 5
    ) -> list[dict[str, Any]]:
        """查找行为相似的物种"""
        profile = self.infer_behavior_profile(species)
        results = self.search(profile.to_text(), top_k + 1)
        
        # 排除自己
        return [r for r in results if r["lineage_code"] != species.lineage_code][:top_k]
    
    def find_behavior_conflicts(
        self, 
        species_a: 'Species', 
        species_b: 'Species'
    ) -> list[str]:
        """检测两个物种之间的行为冲突"""
        profile_a = self._profile_cache.get(species_a.lineage_code) or self.infer_behavior_profile(species_a)
        profile_b = self._profile_cache.get(species_b.lineage_code) or self.infer_behavior_profile(species_b)
        
        conflicts = []
        
        # 活动节律冲突
        if profile_a.activity_pattern != profile_b.activity_pattern:
            if "夜行" in profile_a.activity_pattern and "昼行" in profile_b.activity_pattern:
                conflicts.append(f"活动时间完全错开: {profile_a.activity_pattern} vs {profile_b.activity_pattern}")
            elif "夜行" in profile_b.activity_pattern and "昼行" in profile_a.activity_pattern:
                conflicts.append(f"活动时间完全错开: {profile_a.activity_pattern} vs {profile_b.activity_pattern}")
        
        # 竞争冲突（相同社会结构 + 相同捕食策略 = 高竞争）
        if profile_a.predation_strategy == profile_b.predation_strategy:
            if profile_a.social_behavior == profile_b.social_behavior:
                conflicts.append(f"高度生态位重叠: 相同捕食策略和社会结构")
        
        # 捕食者-猎物关系推断
        if "追逐" in profile_a.predation_strategy and "逃跑" in profile_b.defense_strategy:
            conflicts.append("可能的捕食关系: A 捕食 B")
        elif "追逐" in profile_b.predation_strategy and "逃跑" in profile_a.defense_strategy:
            conflicts.append("可能的捕食关系: B 捕食 A")
        
        return conflicts
    
    def get_behavior_summary(self) -> dict[str, Any]:
        """获取行为分布摘要"""
        if not self._profile_cache:
            return {}
        
        # 统计各策略的分布
        predation_dist: dict[str, int] = {}
        activity_dist: dict[str, int] = {}
        social_dist: dict[str, int] = {}
        
        for profile in self._profile_cache.values():
            predation_dist[profile.predation_strategy] = predation_dist.get(profile.predation_strategy, 0) + 1
            activity_dist[profile.activity_pattern] = activity_dist.get(profile.activity_pattern, 0) + 1
            social_dist[profile.social_behavior] = social_dist.get(profile.social_behavior, 0) + 1
        
        return {
            "total_species": len(self._profile_cache),
            "predation_distribution": predation_dist,
            "activity_distribution": activity_dist,
            "social_distribution": social_dist,
        }
    
    def export_for_save(self) -> dict[str, Any]:
        """导出数据"""
        base = super().export_for_save()
        base["profile_count"] = len(self._profile_cache)
        return base

