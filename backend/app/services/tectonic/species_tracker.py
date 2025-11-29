"""物种-板块追踪器

追踪物种随板块移动，检测隔离和接触事件。
区分陆地物种和海洋物种的不同行为。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence, TYPE_CHECKING

import numpy as np

from .models import (
    Plate, SimpleTile, IsolationEvent, ContactEvent, BoundaryType
)

if TYPE_CHECKING:
    pass


class HabitatType(Enum):
    """栖息地类型"""
    TERRESTRIAL = "terrestrial"   # 陆生
    AQUATIC = "aquatic"           # 淡水
    MARINE = "marine"             # 海洋
    AMPHIBIOUS = "amphibious"     # 两栖（可跨越）
    COASTAL = "coastal"           # 沿海（陆地和浅海）


@dataclass
class SimpleSpecies:
    """简化的物种数据（用于独立测试）"""
    id: int
    lineage_code: str
    name: str
    trophic_level: float = 2.0
    habitat_type: str = "terrestrial"  # terrestrial, marine, amphibious, coastal
    
    # 迁移能力
    dispersal_ability: float = 0.5  # 0-1, 越高越能跨越障碍
    
    # 所在板块分布
    plate_distribution: dict[int, float] | None = None  # {plate_id: population_ratio}
    
    def can_cross_ocean(self) -> bool:
        """是否能跨越海洋"""
        return self.habitat_type in ["marine", "amphibious", "coastal"] or \
               self.dispersal_ability > 0.8
    
    def can_cross_land(self) -> bool:
        """是否能跨越陆地（对海洋物种）"""
        return self.habitat_type in ["terrestrial", "amphibious", "coastal"] or \
               self.dispersal_ability > 0.8
    
    def is_marine(self) -> bool:
        """是否是海洋物种"""
        return self.habitat_type == "marine"
    
    def is_terrestrial(self) -> bool:
        """是否是陆地物种"""
        return self.habitat_type == "terrestrial"


@dataclass
class SimpleHabitat:
    """简化的栖息地数据"""
    tile_id: int
    species_id: int
    population: float = 0.0


@dataclass
class PlateMovementResult:
    """板块移动结果"""
    tiles_moved: int
    isolation_events: list[IsolationEvent]
    contact_events: list[ContactEvent]
    species_affected: int
    
    # 新增：按栖息地类型分类
    terrestrial_isolation: int = 0
    marine_isolation: int = 0
    terrestrial_contact: int = 0
    marine_contact: int = 0


@dataclass
class BarrierInfo:
    """障碍信息"""
    barrier_type: str  # "ocean", "land", "mountain"
    width: float       # 障碍宽度
    plate_a: int
    plate_b: int


class PlateSpeciesTracker:
    """物种-板块追踪器
    
    核心功能：
    1. 追踪物种在各板块上的分布
    2. 检测隔离事件（板块分裂）
    3. 检测接触事件（板块碰撞）
    4. 区分陆地物种和海洋物种的行为差异
    
    隔离机制：
    - 陆地物种：被海洋分隔时隔离
    - 海洋物种：被陆地分隔时隔离（如洋盆关闭）
    
    接触机制：
    - 陆地物种：板块碰撞时接触
    - 海洋物种：新海峡/海道开通时可能接触
    """
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # 板块-物种分布缓存
        # {plate_id: {species_id: population}}
        self._plate_species_distribution: dict[int, dict[int, float]] = {}
        
        # 物种-板块分布缓存
        # {species_id: {plate_id: population}}
        self._species_plate_distribution: dict[int, dict[int, float]] = {}
        
        # 板块连通性缓存（考虑陆地/海洋）
        # {(plate_a, plate_b): {"land_connected": bool, "sea_connected": bool}}
        self._plate_connectivity: dict[tuple[int, int], dict[str, bool]] = {}
        
        # 隔离历史
        # {species_id: {"plates": [plate_ids], "turns_isolated": int}}
        self._isolation_history: dict[int, dict] = {}
        
        # 上一回合的板块距离
        self._last_plate_distances: dict[tuple[int, int], float] = {}
        
        # 上一回合的板块连通性
        self._last_connectivity: dict[tuple[int, int], dict[str, bool]] = {}
    
    def update_distributions(
        self,
        species_list: Sequence[SimpleSpecies],
        habitats: Sequence[SimpleHabitat],
        tiles: list[SimpleTile],
    ) -> None:
        """更新物种分布"""
        self._plate_species_distribution.clear()
        self._species_plate_distribution.clear()
        
        tile_map = {t.id: t for t in tiles}
        
        for habitat in habitats:
            tile = tile_map.get(habitat.tile_id)
            if not tile:
                continue
            
            plate_id = tile.plate_id
            species_id = habitat.species_id
            pop = habitat.population
            
            # 更新板块-物种
            if plate_id not in self._plate_species_distribution:
                self._plate_species_distribution[plate_id] = {}
            self._plate_species_distribution[plate_id][species_id] = \
                self._plate_species_distribution[plate_id].get(species_id, 0) + pop
            
            # 更新物种-板块
            if species_id not in self._species_plate_distribution:
                self._species_plate_distribution[species_id] = {}
            self._species_plate_distribution[species_id][plate_id] = \
                self._species_plate_distribution[species_id].get(plate_id, 0) + pop
    
    def update_connectivity(
        self,
        plates: list[Plate],
        tiles: list[SimpleTile],
    ) -> None:
        """更新板块连通性（区分陆地连通和海洋连通）"""
        self._last_connectivity = self._plate_connectivity.copy()
        self._plate_connectivity.clear()
        
        n_plates = len(plates)
        tile_map = {t.id: t for t in tiles}
        
        # 统计每对板块之间的边界类型
        for tile in tiles:
            if tile.boundary_type == BoundaryType.INTERNAL:
                continue
            
            plate_a = tile.plate_id
            neighbors = self._get_neighbors(tile.x, tile.y)
            
            for nx, ny in neighbors:
                if not (0 <= ny < self.height):
                    continue
                neighbor_id = ny * self.width + nx
                neighbor = tile_map.get(neighbor_id)
                if not neighbor or neighbor.plate_id == plate_a:
                    continue
                
                plate_b = neighbor.plate_id
                key = (min(plate_a, plate_b), max(plate_a, plate_b))
                
                if key not in self._plate_connectivity:
                    self._plate_connectivity[key] = {
                        "land_connected": False,
                        "sea_connected": False,
                        "land_boundary_count": 0,
                        "sea_boundary_count": 0,
                    }
                
                # 判断边界类型
                if tile.elevation >= 0 and neighbor.elevation >= 0:
                    # 两边都是陆地 → 陆地连通
                    self._plate_connectivity[key]["land_connected"] = True
                    self._plate_connectivity[key]["land_boundary_count"] += 1
                elif tile.elevation < 0 and neighbor.elevation < 0:
                    # 两边都是海洋 → 海洋连通
                    self._plate_connectivity[key]["sea_connected"] = True
                    self._plate_connectivity[key]["sea_boundary_count"] += 1
    
    def detect_isolation_events(
        self,
        plates: list[Plate],
        species_list: Sequence[SimpleSpecies],
        plate_distances: dict[tuple[int, int], float],
        turn_index: int,
    ) -> list[IsolationEvent]:
        """
        检测隔离事件
        
        陆地物种隔离条件：
        1. 同一物种分布在多个板块
        2. 板块之间失去陆地连通（被海洋分隔）
        
        海洋物种隔离条件：
        1. 同一物种分布在多个海域
        2. 海域之间失去海洋连通（被陆地分隔，如洋盆关闭）
        """
        events = []
        
        for species in species_list:
            plate_dist = self._species_plate_distribution.get(species.id, {})
            
            # 需要分布在2个以上板块
            if len(plate_dist) < 2:
                continue
            
            plate_ids = list(plate_dist.keys())
            is_marine = species.is_marine()
            is_terrestrial = species.is_terrestrial()
            
            for i, p1 in enumerate(plate_ids):
                for p2 in plate_ids[i+1:]:
                    key = (min(p1, p2), max(p1, p2))
                    
                    # 检查连通性变化
                    current_conn = self._plate_connectivity.get(key, {})
                    last_conn = self._last_connectivity.get(key, {})
                    
                    isolation_detected = False
                    isolation_reason = ""
                    
                    if is_terrestrial:
                        # 陆地物种：检查陆地连通性丢失
                        was_connected = last_conn.get("land_connected", True)
                        now_connected = current_conn.get("land_connected", False)
                        
                        if was_connected and not now_connected:
                            isolation_detected = True
                            isolation_reason = "海洋分隔"
                        elif not now_connected:
                            # 检查距离增加
                            current_dist = plate_distances.get(key, 0)
                            last_dist = self._last_plate_distances.get(key, current_dist)
                            if current_dist - last_dist > 5:
                                isolation_detected = True
                                isolation_reason = "板块漂移"
                    
                    elif is_marine:
                        # 海洋物种：检查海洋连通性丢失
                        was_connected = last_conn.get("sea_connected", True)
                        now_connected = current_conn.get("sea_connected", False)
                        
                        if was_connected and not now_connected:
                            isolation_detected = True
                            isolation_reason = "洋盆关闭"
                    
                    else:
                        # 其他类型：通用距离检测
                        current_dist = plate_distances.get(key, 0)
                        last_dist = self._last_plate_distances.get(key, current_dist)
                        if current_dist - last_dist > 5:
                            isolation_detected = True
                            isolation_reason = "地理分隔"
                    
                    if isolation_detected:
                        # 更新隔离历史
                        if species.id not in self._isolation_history:
                            self._isolation_history[species.id] = {
                                "plates": [p1, p2],
                                "turns_isolated": 1,
                                "reason": isolation_reason,
                            }
                        else:
                            self._isolation_history[species.id]["turns_isolated"] += 1
                        
                        # 隔离3回合以上可能导致物种形成
                        turns = self._isolation_history[species.id]["turns_isolated"]
                        may_speciate = turns >= 3
                        
                        events.append(IsolationEvent(
                            species_id=species.id,
                            lineage_code=species.lineage_code,
                            plate_a=p1,
                            plate_b=p2,
                            distance_increase=plate_distances.get(key, 0) - \
                                              self._last_plate_distances.get(key, 0),
                            may_speciate=may_speciate,
                        ))
        
        # 更新距离缓存
        self._last_plate_distances = plate_distances.copy()
        
        return events
    
    def detect_contact_events(
        self,
        plates: list[Plate],
        species_list: Sequence[SimpleSpecies],
        plate_distances: dict[tuple[int, int], float],
    ) -> list[ContactEvent]:
        """
        检测接触事件
        
        陆地物种接触条件：
        - 两个板块碰撞，建立陆地连通
        
        海洋物种接触条件：
        - 新的海峡/海道开通（虽然较少见）
        """
        events = []
        
        # 找出正在接近的板块对（有新的连通性）
        converging_pairs = []
        for key, conn in self._plate_connectivity.items():
            last_conn = self._last_connectivity.get(key, {})
            
            # 检查新建立的陆地连通
            if conn.get("land_connected") and not last_conn.get("land_connected", False):
                converging_pairs.append((key[0], key[1], "land"))
            
            # 检查新建立的海洋连通
            if conn.get("sea_connected") and not last_conn.get("sea_connected", False):
                converging_pairs.append((key[0], key[1], "sea"))
        
        # 也检查距离减少
        for (p1, p2), dist in plate_distances.items():
            last_dist = self._last_plate_distances.get((p1, p2), dist)
            if last_dist - dist > 3:  # 距离减少超过3格
                if (p1, p2, "approach") not in [(c[0], c[1], c[2]) for c in converging_pairs]:
                    converging_pairs.append((p1, p2, "approach"))
        
        species_map = {s.id: s for s in species_list}
        
        for p1, p2, contact_type in converging_pairs:
            # 获取两个板块上的物种
            species_p1 = set(self._plate_species_distribution.get(p1, {}).keys())
            species_p2 = set(self._plate_species_distribution.get(p2, {}).keys())
            
            for sp1_id in species_p1:
                for sp2_id in species_p2:
                    if sp1_id == sp2_id:
                        continue
                    
                    sp1 = species_map.get(sp1_id)
                    sp2 = species_map.get(sp2_id)
                    
                    if not sp1 or not sp2:
                        continue
                    
                    # 检查栖息地兼容性
                    if contact_type == "land":
                        # 陆地连通：只有陆地物种会接触
                        if not (sp1.can_cross_land() and sp2.can_cross_land()):
                            continue
                    elif contact_type == "sea":
                        # 海洋连通：只有海洋物种会接触
                        if not (sp1.can_cross_ocean() and sp2.can_cross_ocean()):
                            continue
                    
                    # 计算生态相似度
                    similarity = self._compute_similarity(sp1, sp2)
                    
                    # 确定交互类型
                    trophic_diff = abs(sp1.trophic_level - sp2.trophic_level)
                    if trophic_diff >= 0.8:
                        interaction = "predation"
                    elif similarity > 0.7:
                        interaction = "competition"
                    else:
                        interaction = "neutral"
                    
                    # 只记录非中性交互
                    if interaction != "neutral":
                        events.append(ContactEvent(
                            species_a_id=sp1_id,
                            species_b_id=sp2_id,
                            plate_a=p1,
                            plate_b=p2,
                            interaction_type=interaction,
                            similarity=similarity,
                        ))
        
        return events
    
    def _compute_similarity(
        self, 
        sp1: SimpleSpecies, 
        sp2: SimpleSpecies
    ) -> float:
        """计算两个物种的生态相似度"""
        # 营养级相似度
        trophic_sim = 1 - abs(sp1.trophic_level - sp2.trophic_level) / 4
        
        # 栖息地相似度
        if sp1.habitat_type == sp2.habitat_type:
            habitat_sim = 1.0
        elif (sp1.habitat_type in ["coastal", "amphibious"] or 
              sp2.habitat_type in ["coastal", "amphibious"]):
            habitat_sim = 0.6
        else:
            habitat_sim = 0.2
        
        return (trophic_sim * 0.6 + habitat_sim * 0.4)
    
    def compute_plate_distances(
        self,
        plates: list[Plate],
    ) -> dict[tuple[int, int], float]:
        """计算所有板块对之间的距离"""
        distances = {}
        n = len(plates)
        
        for i in range(n):
            for j in range(i + 1, n):
                p1, p2 = plates[i], plates[j]
                
                # 计算中心距离
                dx = p2.rotation_center_x - p1.rotation_center_x
                # 处理X循环
                if abs(dx) > self.width / 2:
                    dx = dx - self.width if dx > 0 else dx + self.width
                dy = p2.rotation_center_y - p1.rotation_center_y
                
                dist = math.sqrt(dx*dx + dy*dy)
                distances[(i, j)] = dist
        
        return distances
    
    def apply_plate_movement(
        self,
        old_coords: np.ndarray,
        new_coords: np.ndarray,
        tiles: list[SimpleTile],
        species_list: Sequence[SimpleSpecies],
        habitats: Sequence[SimpleHabitat],
        plates: list[Plate],
    ) -> PlateMovementResult:
        """
        应用板块移动到物种分布
        """
        # 更新分布
        self.update_distributions(species_list, habitats, tiles)
        
        # 更新连通性
        self.update_connectivity(plates, tiles)
        
        # 计算板块距离
        plate_distances = self.compute_plate_distances(plates)
        
        # 检测事件
        isolation_events = self.detect_isolation_events(
            plates, species_list, plate_distances, turn_index=0
        )
        contact_events = self.detect_contact_events(
            plates, species_list, plate_distances
        )
        
        # 统计移动的地块
        coord_diff = np.abs(new_coords - old_coords)
        tiles_moved = int(np.sum(coord_diff.sum(axis=1) > 0.01))
        
        # 统计受影响的物种
        affected_species = set()
        for event in isolation_events:
            affected_species.add(event.species_id)
        for event in contact_events:
            affected_species.add(event.species_a_id)
            affected_species.add(event.species_b_id)
        
        # 按类型统计
        species_map = {s.id: s for s in species_list}
        terrestrial_iso = sum(1 for e in isolation_events 
                             if species_map.get(e.species_id, SimpleSpecies(0, "", "")).is_terrestrial())
        marine_iso = sum(1 for e in isolation_events 
                        if species_map.get(e.species_id, SimpleSpecies(0, "", "")).is_marine())
        
        return PlateMovementResult(
            tiles_moved=tiles_moved,
            isolation_events=isolation_events,
            contact_events=contact_events,
            species_affected=len(affected_species),
            terrestrial_isolation=terrestrial_iso,
            marine_isolation=marine_iso,
        )
    
    def _get_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """获取六边形邻居"""
        if x & 1:
            offsets = [(0, -1), (1, -1), (-1, 0), (1, 0), (0, 1), (1, 1)]
        else:
            offsets = [(-1, -1), (0, -1), (-1, 0), (1, 0), (-1, 1), (0, 1)]
        
        neighbors = []
        for dx, dy in offsets:
            nx = (x + dx) % self.width
            ny = y + dy
            if 0 <= ny < self.height:
                neighbors.append((nx, ny))
        
        return neighbors
    
    def get_species_on_plate(self, plate_id: int) -> list[int]:
        """获取板块上的物种ID列表"""
        return list(self._plate_species_distribution.get(plate_id, {}).keys())
    
    def get_plate_distribution(self, species_id: int) -> dict[int, float]:
        """获取物种的板块分布"""
        return self._species_plate_distribution.get(species_id, {})
    
    def get_isolation_duration(self, species_id: int) -> int:
        """获取物种隔离时长"""
        history = self._isolation_history.get(species_id)
        if history:
            return history.get("turns_isolated", 0)
        return 0
    
    def get_connectivity_info(self, plate_a: int, plate_b: int) -> dict:
        """获取两个板块之间的连通性信息"""
        key = (min(plate_a, plate_b), max(plate_a, plate_b))
        return self._plate_connectivity.get(key, {
            "land_connected": False,
            "sea_connected": False,
        })
