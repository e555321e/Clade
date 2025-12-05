"""区域/地块向量插件 (MVP)

为地块生成综合向量，整合气候、植被、物种分布等信息。

数据契约：
- 必需字段: all_tiles, all_species
- 可选字段: all_habitats, populations
- 降级策略: 无 all_tiles 时跳过索引；缺少关键字段时使用简化向量

【张量集成优化】
- 优先从 TensorState 获取物种分布数据
- 避免重复计算 species_distribution 映射
- 使用张量环境数据补充地块信息
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, Union

from .base import EmbeddingPlugin, PluginConfig
from .registry import register_plugin

if TYPE_CHECKING:
    from ...models.species import Species
    from ...models.environment import Habitat
    from ...simulation.context import SimulationContext

import logging

logger = logging.getLogger(__name__)


def _normalize_habitats(raw_habitats: Any) -> dict[str, Any]:
    """归一化 all_habitats 到 dict 格式
    
    SimulationContext.all_habitats 类型为 list[Habitat]，
    但旧代码可能传入 dict。此函数统一转换为 {id: habitat} 形式。
    """
    if raw_habitats is None:
        return {}
    
    if isinstance(raw_habitats, dict):
        return raw_habitats
    
    if isinstance(raw_habitats, list):
        result = {}
        for h in raw_habitats:
            if isinstance(h, dict):
                hid = h.get("id", h.get("habitat_id", ""))
                if hid:
                    result[str(hid)] = h
            else:
                hid = getattr(h, 'id', getattr(h, 'habitat_id', None))
                if hid:
                    result[str(hid)] = h
        return result
    
    return {}


@dataclass
class TileProfile:
    """地块综合档案"""
    tile_id: str
    biome: str = "unknown"
    temperature: float = 20.0
    precipitation: float = 500.0
    elevation: float = 0.0
    vegetation_density: float = 0.5
    species_count: int = 0
    dominant_trophic: float = 2.0
    features: list[str] = field(default_factory=list)
    
    def to_text(self) -> str:
        """转换为向量化文本"""
        feature_str = ", ".join(self.features) if self.features else "无特殊特征"
        
        return f"""地块 {self.tile_id}:
生物群落: {self.biome}
温度: {self.temperature:.1f}°C
降水量: {self.precipitation:.0f}mm
海拔: {self.elevation:.0f}m
植被密度: {self.vegetation_density:.0%}
物种多样性: {self.species_count}种
主导营养级: {self.dominant_trophic:.1f}
特征: {feature_str}"""


@register_plugin("tile_biome")
class TileBiomePlugin(EmbeddingPlugin):
    """区域/地块向量插件
    
    MVP 功能:
    1. 从地块数据构建综合档案
    2. 构建向量索引
    3. 物种-地块匹配度计算
    4. 生态热点识别
    
    张量集成:
    - 优先从 TensorState 获取物种分布
    - 使用张量环境数据增强地块信息
    """
    
    # 声明依赖的 Context 字段
    required_context_fields = {"all_tiles", "all_species"}
    # 启用张量数据
    use_tensor_data = True
    
    @property
    def name(self) -> str:
        return "tile_biome"
    
    def _do_initialize(self) -> None:
        """初始化"""
        self._profile_cache: dict[str, TileProfile] = {}
        self._species_distribution: dict[str, list[str]] = {}  # tile_id -> [species_codes]
        self._using_tensor_data = False  # 追踪是否使用了张量数据
    
    def build_tile_profiles(
        self, 
        ctx: 'SimulationContext'
    ) -> dict[str, TileProfile]:
        """从 Context 构建地块档案
        
        【张量集成】优先从 TensorState 获取物种分布数据
        """
        profiles: dict[str, TileProfile] = {}
        
        tiles = ctx.all_tiles or []
        if not tiles:
            logger.debug(f"[{self.name}] all_tiles 为空，跳过地块档案构建")
            return profiles
        
        # 构建物种分布映射
        self._species_distribution.clear()
        self._using_tensor_data = False
        
        # 【张量优先】尝试从张量桥接获取物种分布
        if self.has_tensor_data:
            tensor_dist = self.tensor_bridge.to_legacy_species_distribution()
            if tensor_dist:
                self._species_distribution = tensor_dist
                self._using_tensor_data = True
                logger.debug(f"[{self.name}] 使用张量数据: {len(tensor_dist)} 个地块有物种分布")
        
        # 回退：从物种对象提取分布
        if not self._using_tensor_data:
            missing_populations = 0
            
            for sp in (ctx.all_species or []):
                populations = getattr(sp, 'populations', None)
                if populations is None:
                    missing_populations += 1
                    continue
                
                for pop in populations:
                    if isinstance(pop, dict):
                        tile_id = pop.get("tile_id", pop.get("habitat_id", ""))
                    else:
                        tile_id = getattr(pop, 'tile_id', getattr(pop, 'habitat_id', ''))
                    
                    if tile_id:
                        tile_id = str(tile_id)
                        if tile_id not in self._species_distribution:
                            self._species_distribution[tile_id] = []
                        self._species_distribution[tile_id].append(sp.lineage_code)
            
            if missing_populations > 0:
                logger.debug(f"[{self.name}] {missing_populations} 个物种缺少 populations 字段")
        
        # 归一化栖息地信息（list[Habitat] -> dict）
        raw_habitats = getattr(ctx, 'all_habitats', None)
        habitats = _normalize_habitats(raw_habitats)
        
        for tile in tiles:
            if isinstance(tile, dict):
                tile_id = str(tile.get("id", tile.get("tile_id", "")))
            else:
                tile_id = str(getattr(tile, 'id', getattr(tile, 'tile_id', '')))
            
            if not tile_id:
                continue
            
            # 提取地块属性
            if isinstance(tile, dict):
                temp = tile.get("temperature", 20)
                precip = tile.get("precipitation", 500)
                elev = tile.get("elevation", 0)
                biome = tile.get("biome", "unknown")
                veg = tile.get("vegetation", tile.get("vegetation_cover", 0.5))
            else:
                temp = getattr(tile, 'temperature', 20)
                precip = getattr(tile, 'precipitation', 500)
                elev = getattr(tile, 'elevation', 0)
                biome = getattr(tile, 'biome', 'unknown')
                veg = getattr(tile, 'vegetation', 0.5)
            
            # 从栖息地获取额外信息（已归一化为 dict）
            habitat = habitats.get(tile_id)
            if habitat is not None:
                if isinstance(habitat, dict):
                    biome = habitat.get("biome", biome)
                    veg = habitat.get("vegetation_cover", veg)
                else:
                    biome = getattr(habitat, 'biome', biome)
                    veg = getattr(habitat, 'vegetation_cover', veg)
            
            # 计算物种统计
            species_codes = self._species_distribution.get(tile_id, [])
            species_count = len(species_codes)
            
            # 计算主导营养级
            if species_codes and ctx.all_species:
                trophic_sum = 0
                count = 0
                for sp in ctx.all_species:
                    if sp.lineage_code in species_codes:
                        trophic_sum += getattr(sp, 'trophic_level', 2.0)
                        count += 1
                dominant_trophic = trophic_sum / count if count > 0 else 2.0
            else:
                dominant_trophic = 2.0
            
            # 识别特殊特征
            features = []
            if temp < 0:
                features.append("冰冻环境")
            elif temp > 35:
                features.append("极端高温")
            if precip > 2000:
                features.append("高降水热带")
            elif precip < 200:
                features.append("干旱荒漠")
            if elev > 2000:
                features.append("高海拔")
            if species_count > 20:
                features.append("高生物多样性")
            elif species_count == 0:
                features.append("无物种分布")
            
            profiles[tile_id] = TileProfile(
                tile_id=tile_id,
                biome=biome,
                temperature=temp,
                precipitation=precip,
                elevation=elev,
                vegetation_density=veg if isinstance(veg, float) else 0.5,
                species_count=species_count,
                dominant_trophic=dominant_trophic,
                features=features,
            )
        
        self._profile_cache = profiles
        return profiles
    
    def build_index(self, ctx: 'SimulationContext') -> int:
        """构建地块向量索引"""
        store = self._get_vector_store()
        
        profiles = self.build_tile_profiles(ctx)
        if not profiles:
            return 0
        
        texts = []
        ids = []
        metadata_list = []
        
        for tile_id, profile in profiles.items():
            texts.append(profile.to_text())
            ids.append(tile_id)
            metadata_list.append({
                "biome": profile.biome,
                "temperature": profile.temperature,
                "species_count": profile.species_count,
                "elevation": profile.elevation,
            })
        
        vectors = self._embed_texts(texts)
        if not vectors:
            return 0
        
        return store.add_batch(ids, vectors, metadata_list)
    
    def _build_index_fallback(self, ctx: 'SimulationContext') -> int:
        """降级逻辑：无 all_tiles 时跳过"""
        logger.warning(f"[{self.name}] 无地块数据，跳过索引构建")
        return 0
    
    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """搜索匹配的地块"""
        store = self._get_vector_store(create=False)
        if not store or store.size == 0:
            return []
        
        query_vec = self.embeddings.embed_single(query)
        results = store.search(query_vec, top_k)
        self._stats.searches += 1
        
        return [
            {
                "tile_id": r.id,
                "similarity": round(r.score, 3),
                **r.metadata
            }
            for r in results
        ]
    
    def calculate_species_tile_compatibility(
        self, 
        species: 'Species', 
        tile_id: str
    ) -> dict[str, float]:
        """计算物种与地块的兼容性"""
        profile = self._profile_cache.get(tile_id)
        if not profile:
            return {"overall_compatibility": 0, "reason": "地块不存在"}
        
        traits = getattr(species, 'abstract_traits', None) or {}
        
        # 气候匹配（基于温度耐受）
        heat_tolerance = traits.get("耐热性", 5)
        cold_tolerance = traits.get("耐寒性", 5)
        
        if profile.temperature > 30:
            climate_match = min(1.0, heat_tolerance / 10)
        elif profile.temperature < 5:
            climate_match = min(1.0, cold_tolerance / 10)
        else:
            climate_match = 0.8  # 温和气候
        
        # 生态位可用性（物种越少空间越大）
        max_capacity = 30
        niche_availability = max(0, 1 - profile.species_count / max_capacity)
        
        # 竞争风险（基于营养级差异）
        species_trophic = getattr(species, 'trophic_level', 2.0)
        trophic_diff = abs(species_trophic - profile.dominant_trophic)
        competition_risk = max(0, 1 - trophic_diff / 2) if trophic_diff < 1 else 0.3
        
        # 综合评分
        overall = (climate_match * 0.4 + niche_availability * 0.3 + (1 - competition_risk * 0.5) * 0.3)
        
        return {
            "overall_compatibility": round(overall, 3),
            "climate_match": round(climate_match, 3),
            "niche_availability": round(niche_availability, 3),
            "competition_risk": round(competition_risk, 3),
        }
    
    def find_best_tiles_for_species(
        self, 
        species: 'Species', 
        top_k: int = 5
    ) -> list[dict[str, Any]]:
        """为物种找到最适合的地块（智能迁徙推荐）"""
        results = []
        
        for tile_id, profile in self._profile_cache.items():
            compat = self.calculate_species_tile_compatibility(species, tile_id)
            if compat.get("overall_compatibility", 0) > 0.3:
                results.append({
                    "tile_id": tile_id,
                    "biome": profile.biome,
                    "temperature": profile.temperature,
                    **compat
                })
        
        results.sort(key=lambda x: x.get("overall_compatibility", 0), reverse=True)
        return results[:top_k]
    
    def find_ecological_hotspots(self, top_k: int = 10) -> list[dict[str, Any]]:
        """找出最具适应潜力的生态热点区域"""
        hotspots = []
        
        for tile_id, profile in self._profile_cache.items():
            # 热点评分：高多样性 + 适宜气候 + 适中海拔
            diversity_score = min(1.0, profile.species_count / 20)
            climate_score = max(0, 1 - abs(profile.temperature - 20) / 25)
            elevation_score = max(0, 1 - profile.elevation / 3000) if profile.elevation < 3000 else 0.1
            
            hotspot_score = (diversity_score * 0.4 + climate_score * 0.35 + elevation_score * 0.25)
            
            hotspots.append({
                "tile_id": tile_id,
                "biome": profile.biome,
                "hotspot_score": round(hotspot_score, 3),
                "species_count": profile.species_count,
                "temperature": profile.temperature,
            })
        
        hotspots.sort(key=lambda x: x["hotspot_score"], reverse=True)
        return hotspots[:top_k]
    
    def get_tile_summary(self) -> dict[str, Any]:
        """获取地块分布摘要"""
        if not self._profile_cache:
            return {}
        
        biome_dist: dict[str, int] = {}
        total_species = 0
        
        for profile in self._profile_cache.values():
            biome_dist[profile.biome] = biome_dist.get(profile.biome, 0) + 1
            total_species += profile.species_count
        
        return {
            "total_tiles": len(self._profile_cache),
            "biome_distribution": biome_dist,
            "total_species_positions": total_species,
            "hotspots": self.find_ecological_hotspots(top_k=3),
        }

