"""混合 Embedding 宜居度服务

结合语义向量和特征向量计算物种-地块宜居度。

架构:
1. 语义相似度 (50%): 使用在线 Embedding API 获取语义理解
2. 特征相似度 (50%): 使用 12 维数值向量计算精确匹配

优化:
- 矩阵计算: 一次性计算 N物种 × M地块
- 缓存机制: 向量缓存 + 矩阵缓存
- 增量更新: 只重算变化的部分
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

if TYPE_CHECKING:
    from ...models.species import Species
    from ...models.environment import MapTile
    from ..system.embedding import EmbeddingService

logger = logging.getLogger(__name__)


# ============ 12 维特征空间定义 ============

DIMENSION_NAMES = [
    "thermal",      # 热量偏好
    "moisture",     # 水分偏好
    "altitude",     # 海拔偏好
    "salinity",     # 盐度偏好
    "resources",    # 资源需求
    "aquatic",      # 水域性
    "depth",        # 深度偏好
    "light",        # 光照需求
    "volcanic",     # 地热偏好
    "stability",    # 稳定性偏好
    "vegetation",   # 植被偏好
    "river",        # 河流偏好
]

# 各维度权重 (总和 = 1.0)
DIMENSION_WEIGHTS = np.array([
    0.10,   # thermal - 温度重要
    0.08,   # moisture - 湿度中等
    0.08,   # altitude - 海拔中等
    0.10,   # salinity - 盐度重要(区分淡水/海水)
    0.08,   # resources - 资源中等
    0.22,   # aquatic - 水域性最重要！(水生上岸必死)
    0.08,   # depth - 深度中等
    0.06,   # light - 光照次要
    0.04,   # volcanic - 地热次要
    0.04,   # stability - 稳定性次要
    0.06,   # vegetation - 植被次要
    0.06,   # river - 河流次要
])

# 语义 vs 特征的权重
SEMANTIC_WEIGHT = 0.4
FEATURE_WEIGHT = 0.6


@dataclass
class SuitabilityResult:
    """宜居度计算结果"""
    total: float
    semantic_score: float
    feature_score: float
    feature_breakdown: dict[str, float] = field(default_factory=dict)
    species_text: str = ""
    tile_text: str = ""


class SuitabilityService:
    """混合 Embedding 宜居度服务
    
    结合语义向量(在线API)和特征向量(12D)计算宜居度。
    """
    
    def __init__(
        self, 
        embedding_service: "EmbeddingService | None" = None,
        use_semantic: bool = True,
        semantic_weight: float = SEMANTIC_WEIGHT,
        feature_weight: float = FEATURE_WEIGHT,
    ):
        self.embeddings = embedding_service
        self.use_semantic = use_semantic and embedding_service is not None
        self.semantic_weight = semantic_weight
        self.feature_weight = feature_weight
        
        # 向量缓存
        self._species_semantic_cache: dict[str, np.ndarray] = {}  # lineage_code -> vector
        self._species_feature_cache: dict[str, np.ndarray] = {}
        self._tile_semantic_cache: dict[int, np.ndarray] = {}     # tile_id -> vector
        self._tile_feature_cache: dict[int, np.ndarray] = {}
        
        # 文本缓存 (用于显示)
        self._species_text_cache: dict[str, str] = {}
        self._tile_text_cache: dict[int, str] = {}
        
        # 矩阵缓存
        self._matrix_cache: np.ndarray | None = None
        self._cache_species_codes: list[str] = []
        self._cache_tile_ids: list[int] = []
        self._cache_turn: int = -1
        
        # 统计
        self._stats = {
            "compute_calls": 0,
            "cache_hits": 0,
            "semantic_calls": 0,
            "matrix_computes": 0,
        }
    
    # ============ 语义描述生成 ============
    
    def _build_species_text(self, species: "Species") -> str:
        """生成物种的语义描述文本"""
        traits = getattr(species, 'abstract_traits', {}) or {}
        habitat = getattr(species, 'habitat_type', 'terrestrial') or 'terrestrial'
        caps = getattr(species, 'capabilities', []) or []
        diet = getattr(species, 'diet_type', 'omnivore') or 'omnivore'
        trophic = getattr(species, 'trophic_level', 1.0) or 1.0
        growth = getattr(species, 'growth_form', 'aquatic') or 'aquatic'
        
        habitat_cn = {
            "marine": "海洋生物，生活在海水中",
            "deep_sea": "深海生物，适应高压低温黑暗环境",
            "freshwater": "淡水生物，生活在湖泊河流中",
            "coastal": "海岸潮间带生物，适应潮汐变化",
            "terrestrial": "陆地生物",
            "amphibious": "两栖生物，可在水陆间活动",
            "aerial": "空中生物，主要在空中活动",
        }.get(habitat, habitat)
        
        diet_cn = {
            "autotroph": "自养型，通过光合作用或化能合成获取能量",
            "herbivore": "草食性，以植物或藻类为食",
            "carnivore": "肉食性，捕食其他动物",
            "omnivore": "杂食性，食物来源多样",
            "detritivore": "腐食性，分解有机物",
        }.get(diet, "")
        
        growth_cn = {
            "aquatic": "水生形态",
            "moss": "苔藓形态",
            "herb": "草本形态",
            "shrub": "灌木形态",
            "tree": "乔木形态",
        }.get(growth, "")
        
        cap_str = "、".join(caps[:5]) if caps else "无特殊能力"
        
        # 温度偏好描述
        heat = traits.get('耐热性', 5)
        cold = traits.get('耐寒性', 5)
        if heat > 7:
            temp_pref = "喜高温环境"
        elif cold > 7:
            temp_pref = "喜低温环境"
        else:
            temp_pref = "适应温和气候"
        
        # 湿度偏好描述
        drought = traits.get('耐旱性', 5)
        if drought > 7:
            humid_pref = "耐干旱"
        elif drought < 3:
            humid_pref = "需要高湿度"
        else:
            humid_pref = "适应中等湿度"
        
        desc = getattr(species, 'description', '') or ''
        common_name = getattr(species, 'common_name', '') or '未知物种'
        latin_name = getattr(species, 'latin_name', '') or ''
        
        text = f"""{common_name} ({latin_name})
栖息环境: {habitat_cn}
营养级: {trophic:.1f} ({diet_cn})
{f'生长形态: {growth_cn}' if trophic < 2.0 else ''}
温度适应: {temp_pref} (耐热{heat}/10, 耐寒{cold}/10)
湿度适应: {humid_pref} (耐旱{drought}/10)
特殊能力: {cap_str}
{desc[:150] if desc else ''}"""
        
        return text.strip()
    
    def _build_tile_text(self, tile: "MapTile") -> str:
        """生成地块的语义描述文本"""
        biome = getattr(tile, 'biome', '') or '未知'
        temp = getattr(tile, 'temperature', 20)
        humidity = getattr(tile, 'humidity', 0.5)
        elevation = getattr(tile, 'elevation', 0)
        salinity = getattr(tile, 'salinity', 0)
        resources = getattr(tile, 'resources', 100)
        cover = getattr(tile, 'cover', '') or '无'
        has_river = getattr(tile, 'has_river', False)
        is_lake = getattr(tile, 'is_lake', False)
        volcanic = getattr(tile, 'volcanic_potential', 0)
        earthquake = getattr(tile, 'earthquake_risk', 0)
        
        # 判断水域类型
        is_water = "海" in biome or is_lake
        
        if is_water:
            if salinity > 30:
                water_type = "高盐度海水环境"
            elif salinity > 10:
                water_type = "半咸水环境"
            elif is_lake:
                water_type = "淡水湖泊环境"
            else:
                water_type = "淡水环境"
        else:
            water_type = "陆地环境"
        
        # 深度/海拔描述
        if elevation < -3000:
            elev_desc = "深海区域，极高水压，完全黑暗，温度接近0°C"
        elif elevation < -1000:
            elev_desc = "中层海域，光线微弱，水压较高"
        elif elevation < -200:
            elev_desc = "浅海区域，光线充足"
        elif elevation < 0:
            elev_desc = "近岸浅水区"
        elif elevation > 4000:
            elev_desc = "极高海拔，氧气稀薄，气温极低"
        elif elevation > 2000:
            elev_desc = "高海拔山地，气温较低"
        elif elevation > 500:
            elev_desc = "丘陵或低山"
        else:
            elev_desc = "低海拔平原"
        
        # 温度描述
        if temp > 35:
            temp_desc = "极端高温"
        elif temp > 25:
            temp_desc = "温暖炎热"
        elif temp > 15:
            temp_desc = "温和适宜"
        elif temp > 5:
            temp_desc = "凉爽"
        elif temp > -10:
            temp_desc = "寒冷"
        else:
            temp_desc = "极寒"
        
        tile_id = getattr(tile, 'id', 0)
        x = getattr(tile, 'x', 0)
        y = getattr(tile, 'y', 0)
        
        text = f"""地块 #{tile_id} 坐标({x}, {y})
地形: {biome}
环境类型: {water_type}
{elev_desc}
温度: {temp:.1f}°C ({temp_desc})
湿度: {humidity:.0%}
海拔: {elevation:.0f}米
{'盐度: ' + f'{salinity:.1f}‰' if is_water else ''}
资源丰富度: {resources:.0f}
植被: {cover}
{'有河流' if has_river else ''}
{'火山活跃区' if volcanic > 0.5 else ''}
{'地震风险区' if earthquake > 0.5 else ''}"""
        
        return text.strip()
    
    # ============ 特征向量提取 ============
    
    def _extract_species_features(self, species: "Species") -> np.ndarray:
        """从物种属性提取 12 维特征向量
        
        【改进】综合多个属性判断水生/陆生，而不仅仅依赖 habitat_type
        """
        traits = getattr(species, 'abstract_traits', {}) or {}
        habitat = (getattr(species, 'habitat_type', '') or '').lower()
        trophic = getattr(species, 'trophic_level', 1.0) or 1.0
        caps = getattr(species, 'capabilities', []) or []
        growth = (getattr(species, 'growth_form', '') or '').lower()
        common_name = (getattr(species, 'common_name', '') or '').lower()
        desc = (getattr(species, 'description', '') or '').lower()
        
        # 【智能判断】物种是否为水生
        # 综合考虑: habitat_type, growth_form, common_name, description, capabilities
        is_aquatic_species = False
        is_deep_sea = False
        is_freshwater = False
        
        # 1. 从 habitat_type 判断
        if habitat in ("marine", "deep_sea", "freshwater", "coastal"):
            is_aquatic_species = True
            is_deep_sea = habitat == "deep_sea"
            is_freshwater = habitat == "freshwater"
        
        # 2. 从 growth_form 判断 (水生植物)
        if growth == "aquatic" and trophic < 2.0:
            is_aquatic_species = True
        
        # 3. 从名称/描述判断
        aquatic_keywords = ["藻", "浮游", "海洋", "深海", "水生", "海", "鱼", "虾", "蟹", "贝", 
                          "珊瑚", "水母", "海星", "海胆", "鲸", "鲨", "细菌"]
        freshwater_keywords = ["淡水", "河", "湖", "溪"]
        deep_keywords = ["深海", "热泉", "硫", "化能"]
        
        for kw in aquatic_keywords:
            if kw in common_name or kw in desc:
                is_aquatic_species = True
                break
        
        for kw in freshwater_keywords:
            if kw in common_name or kw in desc:
                is_freshwater = True
                is_aquatic_species = True
                break
        
        for kw in deep_keywords:
            if kw in common_name or kw in desc:
                is_deep_sea = True
                is_aquatic_species = True
                break
        
        # 4. 从能力判断
        if "chemosynthesis" in caps:
            is_deep_sea = True
            is_aquatic_species = True
        
        # D0: 热量偏好 (0=极寒, 0.5=温和, 1=极热)
        heat = traits.get('耐热性', 5)
        cold = traits.get('耐寒性', 5)
        thermal = (heat - cold + 10) / 20  # [-10, 10] -> [0, 1]
        thermal = np.clip(thermal, 0, 1)
        
        # D1: 水分偏好 (0=干旱, 1=湿润)
        drought = traits.get('耐旱性', 5)
        moisture = 1 - drought / 10
        if is_aquatic_species:
            moisture = max(moisture, 0.8)  # 水生物种偏好高湿度
        
        # D2: 海拔偏好 (0=深海, 0.5=海平面, 1=高山)
        if is_deep_sea:
            altitude = 0.1
        elif is_aquatic_species and not is_freshwater:
            altitude = 0.3  # 海洋
        elif is_freshwater:
            altitude = 0.5  # 淡水
        elif habitat == "aerial":
            altitude = 0.75
        elif habitat == "terrestrial" or not is_aquatic_species:
            altitude = 0.6
        else:
            altitude = 0.5
        
        # D3: 盐度偏好 (0=淡水, 1=高盐)
        if is_freshwater:
            salinity_pref = 0.1
        elif is_aquatic_species:
            salinity_pref = 0.85  # 海洋生物偏好高盐
        else:
            salinity_pref = 0.3  # 陆生不太在意
        
        # D4: 资源偏好 (生产者需要高资源，水生消费者也需要)
        if trophic < 2.0:
            resources_pref = 0.8
        elif is_aquatic_species:
            resources_pref = 0.5  # 水生消费者需要猎物，间接需要资源
        else:
            resources_pref = 0.4
        
        # D5: 水域性 (0=纯陆地, 1=纯水域) - 最重要！
        if is_aquatic_species:
            aquatic = 1.0
        elif habitat == "amphibious":
            aquatic = 0.5
        else:
            aquatic = 0.0
        
        # D6: 深度偏好 (0=浅/陆, 1=深海)
        if is_deep_sea:
            depth_pref = 0.9
        elif is_aquatic_species:
            depth_pref = 0.4  # 一般水生物种偏好中等深度
        else:
            depth_pref = 0.0
        
        # D7: 光照需求 (0=喜暗, 1=需光)
        if "photosynthesis" in caps:
            light_pref = 0.95  # 光合作用必须有光
        elif "chemosynthesis" in caps or "bioluminescence" in caps:
            light_pref = 0.2   # 化能/发光生物适应黑暗
        elif is_deep_sea:
            light_pref = 0.1
        elif is_aquatic_species:
            light_pref = 0.5  # 一般水生物种
        else:
            light_pref = 0.6
        
        # D8: 地热偏好
        if "chemosynthesis" in caps or is_deep_sea:
            volcanic_pref = 0.8  # 深海/化能合成物种喜欢地热
        else:
            volcanic_pref = 0.3
        
        # D9: 稳定性偏好 (大多数生物喜欢稳定)
        stability_pref = 0.6
        
        # D10: 植被偏好
        if is_aquatic_species:
            vegetation_pref = 0.2  # 水生物种不关心陆地植被
        elif growth in ("moss", "herb", "shrub", "tree"):
            vegetation_map = {"moss": 0.3, "herb": 0.5, "shrub": 0.7, "tree": 0.9}
            vegetation_pref = vegetation_map.get(growth, 0.5)
        else:
            vegetation_pref = 0.4
        
        # D11: 河流偏好
        # 【改进】海洋生物不关心河流，用中性值
        if is_freshwater:
            river_pref = 0.9  # 淡水物种非常需要河流
        elif is_aquatic_species:
            river_pref = 0.3  # 海洋物种不需要河流，给低值使其与无河流地块匹配
        else:
            river_pref = 0.4  # 陆生物种中等偏好
        
        return np.array([
            thermal, moisture, altitude, salinity_pref,
            resources_pref, aquatic, depth_pref, light_pref,
            volcanic_pref, stability_pref, vegetation_pref, river_pref
        ])
    
    def _extract_tile_features(self, tile: "MapTile") -> np.ndarray:
        """从地块属性提取 12 维特征向量
        
        【改进】更智能地检测水域地块
        """
        biome = (getattr(tile, 'biome', '') or '').lower()
        temp = getattr(tile, 'temperature', 20)
        humidity = getattr(tile, 'humidity', 0.5)
        elevation = getattr(tile, 'elevation', 0)
        salinity = getattr(tile, 'salinity', 0)
        resources = getattr(tile, 'resources', 100)
        cover = (getattr(tile, 'cover', '') or '').lower()
        has_river = getattr(tile, 'has_river', False)
        is_lake = getattr(tile, 'is_lake', False)
        volcanic = getattr(tile, 'volcanic_potential', 0)
        earthquake = getattr(tile, 'earthquake_risk', 0)
        
        # 【智能判断】地块是否为水域
        # 综合考虑: biome名称, elevation, is_lake, salinity
        water_keywords = ["海", "洋", "水", "湖", "河", "溪", "浅海", "深海", "大陆架", "大陆坡", "海沟"]
        is_water = False
        is_deep_water = False
        is_freshwater_tile = False
        
        # 1. 从 biome 名称判断
        for kw in water_keywords:
            if kw in biome:
                is_water = True
                break
        
        # 2. 从海拔判断 (海拔<0 通常是水下)
        if elevation < 0:
            is_water = True
        
        # 3. 湖泊判断
        if is_lake:
            is_water = True
            is_freshwater_tile = salinity < 10
        
        # 4. 从盐度判断
        if salinity > 20:
            is_water = True
        elif salinity < 5 and is_water:
            is_freshwater_tile = True
        
        # 5. 深海判断
        if elevation < -1000 or "深海" in biome or "海沟" in biome:
            is_deep_water = True
            is_water = True
        
        # D0: 热量 (归一化温度)
        thermal = (temp + 30) / 70  # [-30, 40] -> [0, 1]
        thermal = np.clip(thermal, 0, 1)
        
        # D1: 水分
        moisture = humidity
        if is_water:
            moisture = 1.0  # 水域湿度为最高
        
        # D2: 海拔 (sigmoid 归一化)
        # -5000m -> 0.0, 0m -> 0.5, 5000m -> 1.0
        altitude = 1 / (1 + np.exp(-elevation / 1500))
        
        # D3: 盐度
        if is_water:
            salinity_norm = min(1.0, salinity / 40)
        else:
            salinity_norm = 0.3  # 陆地盐度中性
        
        # D4: 资源
        resources_norm = min(1.0, math.log(resources + 1) / math.log(1001))
        
        # D5: 水域性 - 最重要！
        aquatic = 1.0 if is_water else 0.0
        
        # D6: 深度
        if is_deep_water or elevation < -3000:
            depth = 1.0  # 深海
        elif elevation < -1000:
            depth = 0.7  # 中层
        elif elevation < 0:
            depth = 0.4  # 浅海
        elif is_lake:
            depth = 0.3  # 湖泊
        else:
            depth = 0.0  # 陆地
        
        # D7: 光照 (与深度相关)
        if elevation < -1000:
            light = 0.1  # 深海无光
        elif elevation < -200:
            light = 0.4  # 弱光层
        elif is_water:
            light = 0.7  # 浅水有光但弱于陆地
        else:
            light = 0.9  # 陆地有光
        
        # D8: 地热
        volcanic_val = volcanic
        
        # D9: 稳定性
        stability = 1.0 - earthquake
        
        # D10: 植被密度
        if is_water:
            vegetation = 0.2  # 水域无陆地植被
        elif "森林" in cover or "林" in cover or "雨林" in cover:
            vegetation = 0.9
        elif "草" in cover or "灌" in cover:
            vegetation = 0.6
        elif "苔" in cover:
            vegetation = 0.4
        elif "沙" in cover or "岩" in cover or "冰" in cover:
            vegetation = 0.1
        else:
            vegetation = 0.3
        
        # D11: 河流
        # 【改进】对于海洋地块，河流值应该是低的（与海洋物种匹配）
        if is_freshwater_tile or has_river:
            river = 0.9
        elif is_water:
            river = 0.3  # 海洋无河流，给低值与海洋物种匹配
        else:
            river = 0.4  # 陆地无河流
        
        return np.array([
            thermal, moisture, altitude, salinity_norm,
            resources_norm, aquatic, depth, light,
            volcanic_val, stability, vegetation, river
        ])
    
    # ============ 核心计算 ============
    
    def compute_suitability(
        self, 
        species: "Species", 
        tile: "MapTile"
    ) -> SuitabilityResult:
        """计算单个物种-地块的宜居度"""
        self._stats["compute_calls"] += 1
        
        lineage_code = getattr(species, 'lineage_code', '')
        tile_id = getattr(tile, 'id', 0)
        
        # 获取/生成特征向量
        if lineage_code not in self._species_feature_cache:
            self._species_feature_cache[lineage_code] = self._extract_species_features(species)
        if tile_id not in self._tile_feature_cache:
            self._tile_feature_cache[tile_id] = self._extract_tile_features(tile)
        
        sp_features = self._species_feature_cache[lineage_code]
        tile_features = self._tile_feature_cache[tile_id]
        
        # 计算特征相似度 (高斯距离)
        diff = sp_features - tile_features
        weighted_sq_diff = DIMENSION_WEIGHTS * (diff ** 2)
        distance = np.sqrt(np.sum(weighted_sq_diff))
        feature_score = float(np.exp(-distance ** 2 / (2 * 0.4 ** 2)))
        
        # 特征分解
        feature_breakdown = {}
        for i, name in enumerate(DIMENSION_NAMES):
            # 单维度相似度
            single_diff = abs(sp_features[i] - tile_features[i])
            single_score = float(np.exp(-single_diff ** 2 / (2 * 0.3 ** 2)))
            feature_breakdown[name] = round(single_score, 3)
        
        # 语义相似度 (如果启用)
        semantic_score = 0.5  # 默认中等
        species_text = ""
        tile_text = ""
        
        if self.use_semantic and self.embeddings is not None:
            try:
                # 获取/生成语义向量
                if lineage_code not in self._species_semantic_cache:
                    species_text = self._build_species_text(species)
                    self._species_text_cache[lineage_code] = species_text
                    vec = self.embeddings.embed_single(species_text)
                    self._species_semantic_cache[lineage_code] = np.array(vec)
                    self._stats["semantic_calls"] += 1
                else:
                    species_text = self._species_text_cache.get(lineage_code, "")
                
                if tile_id not in self._tile_semantic_cache:
                    tile_text = self._build_tile_text(tile)
                    self._tile_text_cache[tile_id] = tile_text
                    vec = self.embeddings.embed_single(tile_text)
                    self._tile_semantic_cache[tile_id] = np.array(vec)
                    self._stats["semantic_calls"] += 1
                else:
                    tile_text = self._tile_text_cache.get(tile_id, "")
                
                # 余弦相似度
                sp_vec = self._species_semantic_cache[lineage_code]
                tile_vec = self._tile_semantic_cache[tile_id]
                
                sp_norm = sp_vec / (np.linalg.norm(sp_vec) + 1e-8)
                tile_norm = tile_vec / (np.linalg.norm(tile_vec) + 1e-8)
                semantic_score = float(np.dot(sp_norm, tile_norm))
                semantic_score = (semantic_score + 1) / 2  # [-1, 1] -> [0, 1]
                
            except Exception as e:
                logger.warning(f"[SuitabilityService] 语义计算失败: {e}")
                semantic_score = 0.5
        
        # 融合得分
        if self.use_semantic:
            total = self.semantic_weight * semantic_score + self.feature_weight * feature_score
        else:
            total = feature_score
        
        # 确保范围
        total = max(0.1, min(1.0, total))
        
        return SuitabilityResult(
            total=round(total, 3),
            semantic_score=round(semantic_score, 3),
            feature_score=round(feature_score, 3),
            feature_breakdown=feature_breakdown,
            species_text=species_text,
            tile_text=tile_text,
        )
    
    def compute_matrix(
        self,
        species_list: Sequence["Species"],
        tiles: Sequence["MapTile"],
        turn_index: int = -1,
    ) -> np.ndarray:
        """批量计算 N物种 × M地块 的宜居度矩阵"""
        self._stats["matrix_computes"] += 1
        
        species_list = list(species_list)
        tiles = list(tiles)
        N, M = len(species_list), len(tiles)
        
        if N == 0 or M == 0:
            return np.array([])
        
        # 检查缓存
        current_codes = [sp.lineage_code for sp in species_list]
        current_tile_ids = [t.id for t in tiles]
        
        if (self._matrix_cache is not None and 
            self._cache_turn == turn_index and
            self._cache_species_codes == current_codes and
            self._cache_tile_ids == current_tile_ids):
            self._stats["cache_hits"] += 1
            return self._matrix_cache
        
        logger.info(f"[SuitabilityService] 计算 {N}×{M} 宜居度矩阵...")
        
        # 提取所有特征向量
        species_features = np.array([
            self._extract_species_features(sp) for sp in species_list
        ])  # (N, 12)
        
        tile_features = np.array([
            self._extract_tile_features(t) for t in tiles
        ])  # (M, 12)
        
        # 缓存特征向量
        for sp in species_list:
            if sp.lineage_code not in self._species_feature_cache:
                self._species_feature_cache[sp.lineage_code] = self._extract_species_features(sp)
        for t in tiles:
            if t.id not in self._tile_feature_cache:
                self._tile_feature_cache[t.id] = self._extract_tile_features(t)
        
        # 矩阵计算: (N, 1, 12) - (1, M, 12) = (N, M, 12)
        diff = species_features[:, np.newaxis, :] - tile_features[np.newaxis, :, :]
        
        # 加权距离
        weighted_sq_diff = DIMENSION_WEIGHTS * (diff ** 2)  # (N, M, 12)
        distances = np.sqrt(weighted_sq_diff.sum(axis=2))  # (N, M)
        
        # 高斯核转换
        feature_similarity = np.exp(-distances ** 2 / (2 * 0.4 ** 2))  # (N, M)
        
        # 语义相似度 (如果启用)
        if self.use_semantic and self.embeddings is not None:
            try:
                # 批量生成语义向量
                species_texts = []
                tiles_texts = []
                
                for sp in species_list:
                    if sp.lineage_code not in self._species_text_cache:
                        text = self._build_species_text(sp)
                        self._species_text_cache[sp.lineage_code] = text
                    species_texts.append(self._species_text_cache[sp.lineage_code])
                
                for t in tiles:
                    if t.id not in self._tile_text_cache:
                        text = self._build_tile_text(t)
                        self._tile_text_cache[t.id] = text
                    tiles_texts.append(self._tile_text_cache[t.id])
                
                # 批量 embedding
                species_semantic = np.array(self.embeddings.embed(species_texts))  # (N, D)
                tile_semantic = np.array(self.embeddings.embed(tiles_texts))  # (M, D)
                
                # 缓存语义向量
                for i, sp in enumerate(species_list):
                    self._species_semantic_cache[sp.lineage_code] = species_semantic[i]
                for i, t in enumerate(tiles):
                    self._tile_semantic_cache[t.id] = tile_semantic[i]
                
                # 余弦相似度矩阵
                sp_norm = species_semantic / (np.linalg.norm(species_semantic, axis=1, keepdims=True) + 1e-8)
                tile_norm = tile_semantic / (np.linalg.norm(tile_semantic, axis=1, keepdims=True) + 1e-8)
                semantic_similarity = sp_norm @ tile_norm.T  # (N, M)
                semantic_similarity = (semantic_similarity + 1) / 2  # [-1, 1] -> [0, 1]
                
                # 融合
                suitability_matrix = (
                    self.semantic_weight * semantic_similarity + 
                    self.feature_weight * feature_similarity
                )
                
                self._stats["semantic_calls"] += N + M
                
            except Exception as e:
                logger.warning(f"[SuitabilityService] 语义矩阵计算失败: {e}")
                suitability_matrix = feature_similarity
        else:
            suitability_matrix = feature_similarity
        
        # 确保范围
        suitability_matrix = np.clip(suitability_matrix, 0.1, 1.0)
        
        # 更新缓存
        self._matrix_cache = suitability_matrix
        self._cache_species_codes = current_codes
        self._cache_tile_ids = current_tile_ids
        self._cache_turn = turn_index
        
        logger.info(f"[SuitabilityService] 矩阵计算完成，平均宜居度: {suitability_matrix.mean():.3f}")
        
        return suitability_matrix
    
    def get_suitability_from_matrix(
        self,
        species_index: int,
        tile_index: int,
    ) -> float:
        """从缓存矩阵获取宜居度"""
        if self._matrix_cache is None:
            return 0.5
        
        if 0 <= species_index < self._matrix_cache.shape[0] and \
           0 <= tile_index < self._matrix_cache.shape[1]:
            return float(self._matrix_cache[species_index, tile_index])
        
        return 0.5
    
    def clear_cache(self):
        """清除所有缓存"""
        self._species_semantic_cache.clear()
        self._species_feature_cache.clear()
        self._tile_semantic_cache.clear()
        self._tile_feature_cache.clear()
        self._species_text_cache.clear()
        self._tile_text_cache.clear()
        self._matrix_cache = None
        self._cache_species_codes = []
        self._cache_tile_ids = []
        self._cache_turn = -1
    
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "species_cached": len(self._species_feature_cache),
            "tiles_cached": len(self._tile_feature_cache),
            "semantic_species_cached": len(self._species_semantic_cache),
            "semantic_tiles_cached": len(self._tile_semantic_cache),
            "matrix_cached": self._matrix_cache is not None,
        }


# 全局实例
_global_suitability_service: SuitabilityService | None = None


def get_suitability_service(
    embedding_service: "EmbeddingService | None" = None
) -> SuitabilityService:
    """获取全局宜居度服务实例"""
    global _global_suitability_service
    
    if _global_suitability_service is None:
        _global_suitability_service = SuitabilityService(
            embedding_service=embedding_service,
            use_semantic=embedding_service is not None,
        )
    elif embedding_service is not None and _global_suitability_service.embeddings is None:
        _global_suitability_service.embeddings = embedding_service
        _global_suitability_service.use_semantic = True
    
    return _global_suitability_service

