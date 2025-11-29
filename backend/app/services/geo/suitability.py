"""向量化栖息地适宜度计算模块

提供批量计算物种×地块适宜度矩阵的工具函数，
替代多处重复的逐对计算逻辑，显著提升性能。

使用场景：
- MapStateManager.snapshot_habitats
- HabitatManager 地块筛选
- ReproductionService 承载力计算
- SpeciationService 栖息地初始化
- TileBasedMortalityEngine 死亡率计算

【优化v2】
- 统一所有模块的适宜度计算逻辑
- 新增栖息地类型筛选器
- 新增猎物追踪集成
"""
from __future__ import annotations

import math
from typing import Sequence, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ...models.species import Species
    from ...models.environment import MapTile


# ============ 栖息地类型筛选器 (统一版本) ============

def get_habitat_type_mask(
    tiles: Sequence['MapTile'],
    habitat_type: str
) -> np.ndarray:
    """获取适合某种栖息地类型的地块掩码（向量化）
    
    统一各模块的栖息地类型筛选逻辑，避免重复代码。
    
    Args:
        tiles: 地块列表
        habitat_type: 栖息地类型 (marine, deep_sea, terrestrial, coastal, freshwater, aerial, amphibious)
        
    Returns:
        np.ndarray: bool数组，True表示地块适合该栖息地类型
    """
    n_tiles = len(tiles)
    mask = np.zeros(n_tiles, dtype=bool)
    
    habitat_type = habitat_type.lower() if habitat_type else 'terrestrial'
    
    for idx, tile in enumerate(tiles):
        biome = tile.biome.lower() if tile.biome else ""
        is_lake = getattr(tile, 'is_lake', False)
        
        if habitat_type == "marine":
            if "浅海" in biome or "中层" in biome or ("海" in biome and "深海" not in biome):
                mask[idx] = True
        elif habitat_type == "deep_sea":
            if "深海" in biome:
                mask[idx] = True
        elif habitat_type == "coastal":
            if "海岸" in biome or "浅海" in biome:
                mask[idx] = True
        elif habitat_type == "freshwater":
            if is_lake:
                mask[idx] = True
        elif habitat_type == "amphibious":
            if "海岸" in biome or "浅海" in biome or ("平原" in biome and tile.humidity > 0.4):
                mask[idx] = True
        elif habitat_type == "aerial":
            # 空中物种可以在任何非海洋、非高山地块活动
            if "海" not in biome and "高山" not in biome:
                mask[idx] = True
        elif habitat_type in ("terrestrial", ""):
            # 陆生物种：非海洋地块
            if "海" not in biome:
                mask[idx] = True
        else:
            # 未知类型：默认陆地
            if "海" not in biome:
                mask[idx] = True
    
    return mask


def filter_tiles_by_habitat_type(
    tiles: Sequence['MapTile'],
    habitat_type: str
) -> list['MapTile']:
    """根据栖息地类型筛选地块（列表版本）
    
    Args:
        tiles: 候选地块列表
        habitat_type: 栖息地类型
        
    Returns:
        适合该栖息地类型的地块列表
    """
    tiles = list(tiles)
    mask = get_habitat_type_mask(tiles, habitat_type)
    return [t for i, t in enumerate(tiles) if mask[i]]


def compute_suitability_matrix(
    species_list: Sequence['Species'],
    tiles: Sequence['MapTile'],
    weights: dict[str, float] | None = None
) -> np.ndarray:
    """批量计算物种×地块的适宜度矩阵（向量化）
    
    Args:
        species_list: 物种列表 (N个)
        tiles: 地块列表 (M个)
        weights: 各因子权重，默认 {"temp": 0.35, "humidity": 0.30, "resource": 0.35}
        
    Returns:
        np.ndarray: shape (N, M) 的适宜度矩阵，值域 [0, 1]
    """
    if not species_list or not tiles:
        return np.array([])
    
    if weights is None:
        weights = {"temp": 0.35, "humidity": 0.30, "resource": 0.35}
    
    n_species = len(species_list)
    n_tiles = len(tiles)
    
    # ============ 提取物种属性矩阵 (N × K) ============
    heat_pref = np.array([sp.abstract_traits.get("耐热性", 5) for sp in species_list])
    cold_pref = np.array([sp.abstract_traits.get("耐寒性", 5) for sp in species_list])
    drought_pref = np.array([sp.abstract_traits.get("耐旱性", 5) for sp in species_list])
    
    # ============ 提取地块属性矩阵 (M,) ============
    temperatures = np.array([t.temperature for t in tiles])
    humidities = np.array([t.humidity for t in tiles])
    resources = np.array([t.resources for t in tiles])
    
    # ============ 向量化计算温度适应度 ============
    # 热带（>20°C）：使用耐热性
    # 寒冷（<5°C）：使用耐寒性
    # 温和（5-20°C）：基础分0.8
    
    # 创建温度分数矩阵 (N, M)
    temp_score = np.zeros((n_species, n_tiles))
    
    # 使用广播计算
    hot_mask = temperatures > 20  # (M,)
    cold_mask = temperatures < 5  # (M,)
    mild_mask = ~hot_mask & ~cold_mask  # (M,)
    
    # 热区：temp_score = heat_pref / 10
    temp_score[:, hot_mask] = (heat_pref[:, np.newaxis] / 10.0)[:, :np.sum(hot_mask)]
    
    # 冷区：temp_score = cold_pref / 10
    temp_score[:, cold_mask] = (cold_pref[:, np.newaxis] / 10.0)[:, :np.sum(cold_mask)]
    
    # 温和区：固定0.8
    temp_score[:, mild_mask] = 0.8
    
    # ============ 向量化计算湿度适应度 ============
    # 物种偏好湿度 = 1 - drought_pref/10（耐旱性越高，偏好越干燥）
    species_humidity_pref = 1.0 - drought_pref / 10.0  # (N,)
    
    # 湿度匹配度 = 1 - |实际湿度 - 偏好湿度|
    humidity_diff = np.abs(humidities[np.newaxis, :] - species_humidity_pref[:, np.newaxis])
    humidity_score = 1.0 - humidity_diff  # (N, M)
    humidity_score = np.clip(humidity_score, 0.0, 1.0)
    
    # ============ 向量化计算资源适应度 ============
    # 使用对数归一化（资源是指数分布的）
    resource_score = np.minimum(1.0, np.log(resources + 1) / np.log(1001))  # (M,)
    resource_score = resource_score[np.newaxis, :].repeat(n_species, axis=0)  # (N, M)
    
    # ============ 组合得分 ============
    suitability = (
        temp_score * weights["temp"] +
        humidity_score * weights["humidity"] +
        resource_score * weights["resource"]
    )
    
    # 确保非负
    suitability = np.maximum(suitability, 0.0)
    
    return suitability


def compute_suitability_for_species(
    species: 'Species',
    tiles: Sequence['MapTile'],
    include_resource: bool = True
) -> np.ndarray:
    """计算单个物种对所有地块的适宜度（向量化）
    
    Args:
        species: 目标物种
        tiles: 地块列表
        include_resource: 是否包含资源因子
        
    Returns:
        np.ndarray: shape (M,) 的适宜度数组
    """
    if not tiles:
        return np.array([])
    
    n_tiles = len(tiles)
    
    # 提取物种属性
    heat_pref = species.abstract_traits.get("耐热性", 5)
    cold_pref = species.abstract_traits.get("耐寒性", 5)
    drought_pref = species.abstract_traits.get("耐旱性", 5)
    
    # 提取地块属性
    temperatures = np.array([t.temperature for t in tiles])
    humidities = np.array([t.humidity for t in tiles])
    
    # 温度适应度
    temp_score = np.zeros(n_tiles)
    hot_mask = temperatures > 20
    cold_mask = temperatures < 5
    mild_mask = ~hot_mask & ~cold_mask
    
    temp_score[hot_mask] = heat_pref / 10.0
    temp_score[cold_mask] = cold_pref / 10.0
    temp_score[mild_mask] = 0.8
    
    # 湿度适应度
    humidity_pref = 1.0 - drought_pref / 10.0
    humidity_score = 1.0 - np.abs(humidities - humidity_pref)
    humidity_score = np.clip(humidity_score, 0.0, 1.0)
    
    if include_resource:
        resources = np.array([t.resources for t in tiles])
        resource_score = np.minimum(1.0, resources / 500.0)
        suitability = temp_score * 0.4 + humidity_score * 0.3 + resource_score * 0.3
    else:
        suitability = temp_score * 0.5 + humidity_score * 0.5
    
    return np.maximum(suitability, 0.0)


def filter_suitable_tiles(
    species: 'Species',
    tiles: Sequence['MapTile'],
    min_suitability: float = 0.3,
    top_k: int | None = None
) -> list[tuple['MapTile', float]]:
    """筛选适宜的地块并返回排序结果
    
    Args:
        species: 目标物种
        tiles: 候选地块列表
        min_suitability: 最小适宜度阈值
        top_k: 返回前k个结果（None表示全部）
        
    Returns:
        [(tile, suitability), ...] 按适宜度降序排列
    """
    if not tiles:
        return []
    
    tiles = list(tiles)
    suitability = compute_suitability_for_species(species, tiles)
    
    # 过滤低于阈值的
    valid_indices = np.where(suitability >= min_suitability)[0]
    
    if len(valid_indices) == 0:
        # 如果没有合适的，返回最佳的几个
        top_indices = np.argsort(suitability)[-min(5, len(tiles)):][::-1]
        return [(tiles[i], float(suitability[i])) for i in top_indices]
    
    # 按适宜度排序
    sorted_indices = valid_indices[np.argsort(suitability[valid_indices])[::-1]]
    
    if top_k is not None:
        sorted_indices = sorted_indices[:top_k]
    
    return [(tiles[i], float(suitability[i])) for i in sorted_indices]


def compute_batch_suitability_dict(
    species_list: Sequence['Species'],
    tiles: Sequence['MapTile']
) -> dict[tuple[int, int], float]:
    """批量计算物种×地块适宜度并返回字典格式
    
    Args:
        species_list: 物种列表
        tiles: 地块列表
        
    Returns:
        {(species_id, tile_id): suitability} 字典
    """
    if not species_list or not tiles:
        return {}
    
    species_list = list(species_list)
    tiles = list(tiles)
    
    matrix = compute_suitability_matrix(species_list, tiles)
    
    result = {}
    for i, sp in enumerate(species_list):
        if sp.id is None:
            continue
        for j, tile in enumerate(tiles):
            if tile.id is None:
                continue
            result[(sp.id, tile.id)] = float(matrix[i, j])
    
    return result


# ============ 消费者感知的适宜度计算 ============

def compute_consumer_aware_suitability(
    species: 'Species',
    tiles: Sequence['MapTile'],
    prey_tile_ids: set[int] | None = None,
    weights: dict[str, float] | None = None
) -> np.ndarray:
    """计算消费者的适宜度（考虑猎物分布）
    
    对于消费者（T≥2），在有猎物的地块适宜度更高。
    统一了 map_manager._suitability_score 的逻辑。
    
    Args:
        species: 目标物种
        tiles: 地块列表
        prey_tile_ids: 猎物所在的地块ID集合（仅对消费者有效）
        weights: 权重配置，默认 {"temp": 0.20, "humidity": 0.15, "food": 0.30, "biome": 0.25, "special": 0.10}
        
    Returns:
        np.ndarray: shape (M,) 的适宜度数组
    """
    if not tiles:
        return np.array([])
    
    tiles = list(tiles)
    n_tiles = len(tiles)
    
    if weights is None:
        weights = {"temp": 0.20, "humidity": 0.15, "food": 0.30, "biome": 0.25, "special": 0.10}
    
    # 物种属性
    traits = getattr(species, 'abstract_traits', {}) or {}
    trophic_level = getattr(species, 'trophic_level', 1.0) or 1.0
    habitat_type = (getattr(species, 'habitat_type', 'terrestrial') or 'terrestrial').lower()
    is_consumer = trophic_level >= 2.0
    
    heat_tolerance = traits.get("耐热性", 5)
    cold_tolerance = traits.get("耐寒性", 5)
    drought_tolerance = traits.get("耐旱性", 5)
    
    # 提取地块属性
    temperatures = np.array([t.temperature for t in tiles])
    humidities = np.array([t.humidity for t in tiles])
    resources = np.array([t.resources for t in tiles])
    tile_ids = [t.id for t in tiles]
    
    # ===== 温度适应性 =====
    ideal_temp_min = -10 + (15 - cold_tolerance) * 2
    ideal_temp_max = 10 + heat_tolerance * 2
    
    temp_score = np.ones(n_tiles)
    too_cold = temperatures < ideal_temp_min
    too_hot = temperatures > ideal_temp_max
    
    temp_score[too_cold] = np.maximum(0.2, 1.0 - (ideal_temp_min - temperatures[too_cold]) / 30)
    temp_score[too_hot] = np.maximum(0.2, 1.0 - (temperatures[too_hot] - ideal_temp_max) / 30)
    
    # ===== 湿度适应性 =====
    ideal_humidity = 0.7 - drought_tolerance * 0.04
    humidity_diff = np.abs(humidities - ideal_humidity)
    humidity_score = np.maximum(0.3, 1.0 - humidity_diff * 1.5)
    
    # ===== 食物/资源适应性 =====
    if is_consumer and prey_tile_ids is not None:
        # 消费者：检查是否有猎物
        food_score = np.full(n_tiles, 0.2)  # 默认无猎物
        for i, tid in enumerate(tile_ids):
            if tid in prey_tile_ids:
                food_score[i] = 1.0  # 有猎物
    else:
        # 生产者：使用地块资源
        food_score = np.where(
            resources > 0,
            np.minimum(1.0, 0.3 + 0.7 * np.log(resources + 1) / np.log(1001)),
            0.3
        )
    
    # ===== 生物群系匹配 =====
    biome_score = np.full(n_tiles, 0.6)  # 基础分
    habitat_mask = get_habitat_type_mask(tiles, habitat_type)
    biome_score[habitat_mask] = 1.0
    
    # ===== 特殊栖息地加成 =====
    special_bonus = np.zeros(n_tiles)
    if habitat_type == "hydrothermal":
        for i, tile in enumerate(tiles):
            volcanic = getattr(tile, 'volcanic_potential', 0.0)
            if volcanic > 0.3:
                special_bonus[i] = 0.3
    elif habitat_type == "deep_sea":
        for i, tile in enumerate(tiles):
            if tile.elevation < -2000:
                special_bonus[i] = 0.2
    
    # ===== 综合评分 =====
    suitability = (
        temp_score * weights["temp"] +
        humidity_score * weights["humidity"] +
        food_score * weights["food"] +
        biome_score * weights["biome"] +
        special_bonus * weights["special"]
    )
    
    # 保证最低适宜度
    return np.maximum(0.15, np.minimum(1.0, suitability))


def separate_producers_consumers(
    species_list: Sequence['Species']
) -> tuple[list['Species'], list['Species']]:
    """将物种列表分为生产者和消费者
    
    用于分两阶段处理栖息地分布：先生产者，再消费者。
    
    Args:
        species_list: 物种列表
        
    Returns:
        (producers, consumers) 两个列表
    """
    producers = []
    consumers = []
    
    for sp in species_list:
        if getattr(sp, 'status', 'alive') != 'alive':
            continue
        trophic = getattr(sp, 'trophic_level', 1.0) or 1.0
        if trophic < 2.0:
            producers.append(sp)
        else:
            consumers.append(sp)
    
    return producers, consumers

