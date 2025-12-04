"""
基于 Embedding 的猎物亲和度计算服务

【设计理念】
不使用硬编码规则，而是让 embedding 模型从物种描述中自然学习食性关系。
通过构建"捕食特征文本"和"可食用特征文本"，计算语义匹配度。

【核心组件】
1. 捕食者需求文本构建 - 描述消费者的食物需求
2. 猎物特征文本构建 - 描述生物作为食物的特征
3. 矩阵化批量计算 - 高效计算所有捕食者-猎物对的亲和度
4. 辅助特征评分 - 营养级、栖息地、地块重叠等软约束

【使用方式】
```python
affinity_service = PreyAffinityService(embedding_service)
affinity_matrix = affinity_service.compute_prey_selection_matrix(
    predators, prey_candidates, species_tiles
)
```
"""

import logging
import math
from typing import TYPE_CHECKING, Sequence

import numpy as np

if TYPE_CHECKING:
    from ...models.species import Species
    from ..system.embedding import EmbeddingService

logger = logging.getLogger(__name__)


# ==================== 栖息地亲和度表 ====================
# (捕食者栖息地, 猎物栖息地) -> 物理可达性分数 [0, 1]
# 0 = 完全不可达（陆生吃不到深海生物）
# 1 = 完全可达（同栖息地）
HABITAT_AFFINITY: dict[tuple[str, str], float] = {
    # 陆生捕食者
    ("terrestrial", "terrestrial"): 1.0,
    ("terrestrial", "coastal"): 0.3,
    ("terrestrial", "amphibious"): 0.5,
    ("terrestrial", "freshwater"): 0.1,  # 岸边可能接触
    ("terrestrial", "marine"): 0.0,
    ("terrestrial", "deep_sea"): 0.0,
    ("terrestrial", "hydrothermal"): 0.0,
    ("terrestrial", "aerial"): 0.4,  # 可以抓飞行动物
    
    # 海洋捕食者
    ("marine", "marine"): 1.0,
    ("marine", "coastal"): 0.8,
    ("marine", "deep_sea"): 0.3,
    ("marine", "hydrothermal"): 0.2,
    ("marine", "freshwater"): 0.0,
    ("marine", "terrestrial"): 0.0,
    ("marine", "amphibious"): 0.3,
    ("marine", "aerial"): 0.1,  # 跃出水面捕食
    
    # 淡水捕食者
    ("freshwater", "freshwater"): 1.0,
    ("freshwater", "coastal"): 0.2,
    ("freshwater", "amphibious"): 0.8,
    ("freshwater", "terrestrial"): 0.1,
    ("freshwater", "marine"): 0.0,
    ("freshwater", "deep_sea"): 0.0,
    ("freshwater", "aerial"): 0.1,
    
    # 海岸捕食者（过渡区）
    ("coastal", "coastal"): 1.0,
    ("coastal", "marine"): 0.9,
    ("coastal", "terrestrial"): 0.7,
    ("coastal", "freshwater"): 0.3,
    ("coastal", "amphibious"): 0.8,
    ("coastal", "aerial"): 0.3,
    ("coastal", "deep_sea"): 0.1,
    
    # 两栖捕食者
    ("amphibious", "amphibious"): 1.0,
    ("amphibious", "freshwater"): 0.9,
    ("amphibious", "terrestrial"): 0.8,
    ("amphibious", "coastal"): 0.6,
    ("amphibious", "marine"): 0.2,
    ("amphibious", "aerial"): 0.4,
    
    # 深海捕食者
    ("deep_sea", "deep_sea"): 1.0,
    ("deep_sea", "marine"): 0.5,
    ("deep_sea", "hydrothermal"): 0.8,
    ("deep_sea", "coastal"): 0.1,
    ("deep_sea", "freshwater"): 0.0,
    ("deep_sea", "terrestrial"): 0.0,
    
    # 热泉捕食者
    ("hydrothermal", "hydrothermal"): 1.0,
    ("hydrothermal", "deep_sea"): 0.7,
    ("hydrothermal", "marine"): 0.3,
    
    # 空中捕食者
    ("aerial", "aerial"): 1.0,
    ("aerial", "terrestrial"): 0.9,
    ("aerial", "coastal"): 0.7,
    ("aerial", "freshwater"): 0.5,
    ("aerial", "marine"): 0.3,
    ("aerial", "amphibious"): 0.6,
}


def get_habitat_affinity(pred_habitat: str, prey_habitat: str) -> float:
    """获取栖息地亲和度，未定义的组合返回默认值"""
    key = (pred_habitat or "terrestrial", prey_habitat or "terrestrial")
    if key in HABITAT_AFFINITY:
        return HABITAT_AFFINITY[key]
    # 反向查找
    reverse_key = (prey_habitat or "terrestrial", pred_habitat or "terrestrial")
    if reverse_key in HABITAT_AFFINITY:
        return HABITAT_AFFINITY[reverse_key] * 0.5  # 反向略低
    return 0.3  # 默认中等


class PreyAffinityService:
    """基于 Embedding 的猎物亲和度计算服务
    
    结合语义相似度和结构化特征，计算捕食者-猎物的匹配度。
    """
    
    # 默认权重配置
    DEFAULT_WEIGHTS = {
        "embedding_affinity": 0.35,  # 语义匹配（核心）
        "trophic_fit": 0.25,         # 营养级匹配
        "habitat_overlap": 0.15,     # 栖息地可达性
        "tile_overlap": 0.15,        # 地块重叠
        "size_fit": 0.10,            # 体型匹配
    }
    
    def __init__(
        self, 
        embedding_service: 'EmbeddingService | None' = None,
        weights: dict[str, float] | None = None,
    ):
        self.embeddings = embedding_service
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        
        # 缓存
        self._predator_text_cache: dict[str, str] = {}
        self._prey_text_cache: dict[str, str] = {}
        self._embedding_cache: dict[str, np.ndarray] = {}
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._predator_text_cache.clear()
        self._prey_text_cache.clear()
        self._embedding_cache.clear()
    
    # ==================== 文本构建 ====================
    
    def build_predator_demand_text(self, species: 'Species') -> str:
        """构建捕食者的食物需求描述文本
        
        这段文本将用于 embedding，描述该物种"想吃什么"。
        """
        lineage = species.lineage_code
        if lineage in self._predator_text_cache:
            return self._predator_text_cache[lineage]
        
        parts = []
        
        # 1. 基础信息
        diet_type = getattr(species, 'diet_type', 'omnivore') or 'omnivore'
        habitat_type = getattr(species, 'habitat_type', 'terrestrial') or 'terrestrial'
        trophic = getattr(species, 'trophic_level', 2.0) or 2.0
        
        # 食性中文描述
        diet_names = {
            "herbivore": "草食性",
            "carnivore": "肉食性",
            "omnivore": "杂食性",
            "detritivore": "腐食性",
            "autotroph": "自养",
        }
        diet_cn = diet_names.get(diet_type, "杂食性")
        
        # 栖息地中文描述
        habitat_names = {
            "terrestrial": "陆地",
            "marine": "海洋",
            "freshwater": "淡水",
            "coastal": "海岸",
            "amphibious": "两栖",
            "deep_sea": "深海",
            "hydrothermal": "热泉",
            "aerial": "空中",
        }
        habitat_cn = habitat_names.get(habitat_type, "陆地")
        
        parts.append(f"这是一种{habitat_cn}栖息的{diet_cn}动物")
        parts.append(f"营养级T{trophic:.1f}")
        
        # 2. 食性特征描述
        if diet_type == "herbivore":
            if habitat_type in ["marine", "freshwater", "deep_sea"]:
                parts.append("以水生植物、藻类、浮游植物为食")
            elif habitat_type == "coastal":
                parts.append("以沿海植物、海藻、潮间带藻类为食")
            else:
                parts.append("以陆生植物、草本、灌木、树叶为食")
        elif diet_type == "carnivore":
            parts.append("以其他动物为食，捕食猎物")
        elif diet_type == "omnivore":
            parts.append("既吃植物也吃动物，食性广泛")
        elif diet_type == "detritivore":
            parts.append("以有机碎屑、死亡生物为食")
        
        # 3. 已知猎物偏好
        prey_species = getattr(species, 'prey_species', []) or []
        if prey_species:
            parts.append(f"已知食用物种: {', '.join(prey_species[:5])}")
        
        # 4. 描述摘要（截取食性相关部分）
        description = species.description or ""
        if description:
            # 提取前150字符
            parts.append(f"描述: {description[:150]}")
        
        text = ". ".join(parts)
        self._predator_text_cache[lineage] = text
        return text
    
    def build_prey_feature_text(self, species: 'Species') -> str:
        """构建猎物的可食用特征描述文本
        
        这段文本将用于 embedding，描述该物种"作为食物的特征"。
        """
        lineage = species.lineage_code
        if lineage in self._prey_text_cache:
            return self._prey_text_cache[lineage]
        
        parts = []
        
        diet_type = getattr(species, 'diet_type', 'omnivore') or 'omnivore'
        habitat_type = getattr(species, 'habitat_type', 'terrestrial') or 'terrestrial'
        trophic = getattr(species, 'trophic_level', 1.0) or 1.0
        growth_form = getattr(species, 'growth_form', '') or ''
        
        # 栖息地中文描述
        habitat_names = {
            "terrestrial": "陆地",
            "marine": "海洋",
            "freshwater": "淡水",
            "coastal": "海岸",
            "amphibious": "两栖",
            "deep_sea": "深海",
            "hydrothermal": "热泉",
            "aerial": "空中",
        }
        habitat_cn = habitat_names.get(habitat_type, "陆地")
        
        # 1. 基础特征
        parts.append(f"这是一种{habitat_cn}栖息的生物")
        parts.append(f"营养级T{trophic:.1f}")
        
        # 2. 根据食性类型描述可食用性
        if diet_type == "autotroph":
            # 植物/藻类 - 强调作为食物的特性
            if growth_form == "aquatic":
                parts.append("水生藻类或浮游植物")
                parts.append("适合水生草食动物、滤食动物食用")
            elif growth_form == "moss":
                parts.append("苔藓类植物")
                parts.append("适合小型陆地草食动物食用")
            elif growth_form == "herb":
                parts.append("草本植物")
                parts.append("适合陆地草食动物、食草哺乳动物食用")
            elif growth_form == "shrub":
                parts.append("灌木")
                parts.append("适合中大型陆地草食动物食用")
            elif growth_form == "tree":
                parts.append("乔木")
                parts.append("叶片和果实适合大型草食动物食用")
            else:
                # 根据栖息地推断
                if habitat_type in ["marine", "freshwater", "deep_sea"]:
                    parts.append("水生自养生物，如藻类")
                    parts.append("适合水生草食动物食用")
                else:
                    parts.append("陆生植物")
                    parts.append("适合陆地草食动物食用")
        
        elif diet_type == "herbivore":
            parts.append("草食性动物")
            parts.append("可作为肉食动物的猎物")
            parts.append("通常体型中等，是食物链中间环节")
        
        elif diet_type == "carnivore":
            parts.append("肉食性动物")
            parts.append("可作为更高级肉食动物的猎物")
        
        elif diet_type == "omnivore":
            parts.append("杂食性动物")
            parts.append("可作为肉食动物的猎物")
        
        elif diet_type == "detritivore":
            parts.append("腐食性动物")
            parts.append("可作为某些捕食者的猎物")
        
        # 3. 体型信息
        body_weight = species.morphology_stats.get("body_weight_g", 1.0) or 1.0
        body_length = species.morphology_stats.get("body_length_cm", 1.0) or 1.0
        
        if body_weight < 0.1:
            parts.append("微型生物，适合滤食或微食动物食用")
        elif body_weight < 10:
            parts.append("小型生物，适合小型捕食者食用")
        elif body_weight < 1000:
            parts.append("中型生物")
        elif body_weight < 100000:
            parts.append("大型生物")
        else:
            parts.append("巨型生物")
        
        # 4. 描述摘要
        description = species.description or ""
        if description:
            parts.append(f"描述: {description[:150]}")
        
        text = ". ".join(parts)
        self._prey_text_cache[lineage] = text
        return text
    
    # ==================== 矩阵计算 ====================
    
    def compute_embedding_affinity_matrix(
        self,
        predators: Sequence['Species'],
        prey_candidates: Sequence['Species'],
    ) -> np.ndarray:
        """计算基于 embedding 的捕食者-猎物语义亲和度矩阵
        
        Args:
            predators: 捕食者列表 (消费者, T >= 2.0)
            prey_candidates: 潜在猎物列表
            
        Returns:
            (N_predators, M_prey) 亲和度矩阵, 值域 [0, 1]
        """
        n_pred = len(predators)
        n_prey = len(prey_candidates)
        
        if n_pred == 0 or n_prey == 0:
            return np.zeros((n_pred, n_prey), dtype=np.float32)
        
        if self.embeddings is None:
            logger.warning("[PreyAffinity] 无 embedding 服务，返回默认矩阵")
            return np.full((n_pred, n_prey), 0.5, dtype=np.float32)
        
        try:
            # 1. 构建文本
            predator_texts = [self.build_predator_demand_text(sp) for sp in predators]
            prey_texts = [self.build_prey_feature_text(sp) for sp in prey_candidates]
            
            # 2. 批量获取 embedding
            all_texts = predator_texts + prey_texts
            all_vectors = self.embeddings.embed(all_texts, require_real=False)
            all_vectors = np.array(all_vectors, dtype=np.float32)
            
            pred_vectors = all_vectors[:n_pred]  # (N, D)
            prey_vectors = all_vectors[n_pred:]  # (M, D)
            
            # 3. 归一化
            pred_norm = np.linalg.norm(pred_vectors, axis=1, keepdims=True)
            prey_norm = np.linalg.norm(prey_vectors, axis=1, keepdims=True)
            pred_norm[pred_norm == 0] = 1.0
            prey_norm[prey_norm == 0] = 1.0
            
            pred_normalized = pred_vectors / pred_norm
            prey_normalized = prey_vectors / prey_norm
            
            # 4. 计算余弦相似度矩阵
            affinity_matrix = pred_normalized @ prey_normalized.T  # (N, M)
            
            # 5. 映射到 [0, 1]（余弦相似度原始范围是 [-1, 1]）
            affinity_matrix = (affinity_matrix + 1) / 2
            
            logger.debug(f"[PreyAffinity] Embedding亲和度矩阵: {n_pred}x{n_prey}")
            return affinity_matrix.astype(np.float32)
            
        except Exception as e:
            logger.warning(f"[PreyAffinity] Embedding计算失败: {e}, 返回默认矩阵")
            return np.full((n_pred, n_prey), 0.5, dtype=np.float32)
    
    def compute_trophic_fit_matrix(
        self,
        predators: Sequence['Species'],
        prey_candidates: Sequence['Species'],
    ) -> np.ndarray:
        """计算营养级匹配度矩阵
        
        最佳猎物: 比捕食者低 0.5-1.5 级
        使用高斯核评分，中心在差距 1.0
        """
        n_pred = len(predators)
        n_prey = len(prey_candidates)
        
        if n_pred == 0 or n_prey == 0:
            return np.zeros((n_pred, n_prey), dtype=np.float32)
        
        # 获取营养级
        pred_trophic = np.array([
            getattr(sp, 'trophic_level', 2.0) or 2.0 
            for sp in predators
        ], dtype=np.float32)  # (N,)
        
        prey_trophic = np.array([
            getattr(sp, 'trophic_level', 1.0) or 1.0 
            for sp in prey_candidates
        ], dtype=np.float32)  # (M,)
        
        # 计算差距矩阵
        trophic_diff = pred_trophic[:, np.newaxis] - prey_trophic[np.newaxis, :]  # (N, M)
        
        # 高斯核: 最佳差距 1.0，方差 0.5
        # 差距为 1.0 时得分最高，差距为 0 或 2+ 时得分低
        trophic_fit = np.exp(-((trophic_diff - 1.0) ** 2) / (2 * 0.5 ** 2))
        
        # 负差距（猎物营养级比捕食者高）额外惩罚
        trophic_fit = np.where(trophic_diff < 0.3, trophic_fit * 0.1, trophic_fit)
        
        return np.clip(trophic_fit, 0, 1).astype(np.float32)
    
    def compute_habitat_overlap_matrix(
        self,
        predators: Sequence['Species'],
        prey_candidates: Sequence['Species'],
    ) -> np.ndarray:
        """计算栖息地可达性矩阵
        
        基于预定义的栖息地亲和度表
        """
        n_pred = len(predators)
        n_prey = len(prey_candidates)
        
        if n_pred == 0 or n_prey == 0:
            return np.zeros((n_pred, n_prey), dtype=np.float32)
        
        habitat_overlap = np.zeros((n_pred, n_prey), dtype=np.float32)
        
        for i, pred in enumerate(predators):
            pred_habitat = getattr(pred, 'habitat_type', 'terrestrial') or 'terrestrial'
            for j, prey in enumerate(prey_candidates):
                prey_habitat = getattr(prey, 'habitat_type', 'terrestrial') or 'terrestrial'
                habitat_overlap[i, j] = get_habitat_affinity(pred_habitat, prey_habitat)
        
        return habitat_overlap
    
    def compute_tile_overlap_matrix(
        self,
        predators: Sequence['Species'],
        prey_candidates: Sequence['Species'],
        species_tiles: dict[str, set[int]] | None = None,
    ) -> np.ndarray:
        """计算地块重叠度矩阵
        
        Jaccard 相似度: |A ∩ B| / |A ∪ B|
        """
        n_pred = len(predators)
        n_prey = len(prey_candidates)
        
        if n_pred == 0 or n_prey == 0 or not species_tiles:
            return np.zeros((n_pred, n_prey), dtype=np.float32)
        
        tile_overlap = np.zeros((n_pred, n_prey), dtype=np.float32)
        
        for i, pred in enumerate(predators):
            pred_tiles = species_tiles.get(pred.lineage_code, set())
            if not pred_tiles:
                continue
            for j, prey in enumerate(prey_candidates):
                prey_tiles = species_tiles.get(prey.lineage_code, set())
                if not prey_tiles:
                    continue
                intersection = len(pred_tiles & prey_tiles)
                union = len(pred_tiles | prey_tiles)
                if union > 0:
                    tile_overlap[i, j] = intersection / union
        
        return tile_overlap
    
    def compute_size_fit_matrix(
        self,
        predators: Sequence['Species'],
        prey_candidates: Sequence['Species'],
    ) -> np.ndarray:
        """计算体型匹配度矩阵
        
        最佳体型比例: 捕食者是猎物的 2-10 倍
        使用对数空间的高斯核
        """
        n_pred = len(predators)
        n_prey = len(prey_candidates)
        
        if n_pred == 0 or n_prey == 0:
            return np.zeros((n_pred, n_prey), dtype=np.float32)
        
        # 获取体长（cm）
        pred_size = np.array([
            sp.morphology_stats.get("body_length_cm", 1.0) or 1.0
            for sp in predators
        ], dtype=np.float32)  # (N,)
        
        prey_size = np.array([
            sp.morphology_stats.get("body_length_cm", 1.0) or 1.0
            for sp in prey_candidates
        ], dtype=np.float32)  # (M,)
        
        # 防止除零
        prey_size = np.maximum(prey_size, 0.001)
        
        # 计算体型比例
        size_ratio = pred_size[:, np.newaxis] / prey_size[np.newaxis, :]  # (N, M)
        
        # 对数空间: log10(ratio)
        # 最佳比例 ~5倍 -> log10(5) ≈ 0.7
        log_ratio = np.log10(size_ratio + 0.01)
        
        # 高斯核: 中心 0.5 (约3倍), 方差 0.8
        size_fit = np.exp(-((log_ratio - 0.5) ** 2) / (2 * 0.8 ** 2))
        
        return np.clip(size_fit, 0, 1).astype(np.float32)
    
    def compute_prey_selection_matrix(
        self,
        predators: Sequence['Species'],
        prey_candidates: Sequence['Species'],
        species_tiles: dict[str, set[int]] | None = None,
        weights: dict[str, float] | None = None,
    ) -> np.ndarray:
        """计算综合猎物选择评分矩阵
        
        Args:
            predators: 捕食者列表
            prey_candidates: 潜在猎物列表
            species_tiles: {lineage_code: set(tile_ids)} 物种→地块映射
            weights: 各维度权重，默认使用 self.weights
            
        Returns:
            (N_predators, M_prey) 综合评分矩阵, 值域 [0, 1]
        """
        w = weights or self.weights
        
        n_pred = len(predators)
        n_prey = len(prey_candidates)
        
        if n_pred == 0 or n_prey == 0:
            return np.zeros((n_pred, n_prey), dtype=np.float32)
        
        logger.debug(f"[PreyAffinity] 计算猎物选择矩阵: {n_pred} 捕食者 x {n_prey} 猎物")
        
        # 1. Embedding 语义亲和度
        embedding_affinity = self.compute_embedding_affinity_matrix(predators, prey_candidates)
        
        # 2. 营养级匹配度
        trophic_fit = self.compute_trophic_fit_matrix(predators, prey_candidates)
        
        # 3. 栖息地可达性
        habitat_overlap = self.compute_habitat_overlap_matrix(predators, prey_candidates)
        
        # 4. 地块重叠度
        tile_overlap = self.compute_tile_overlap_matrix(predators, prey_candidates, species_tiles)
        
        # 5. 体型匹配度
        size_fit = self.compute_size_fit_matrix(predators, prey_candidates)
        
        # 6. 加权综合
        total_score = (
            embedding_affinity * w.get("embedding_affinity", 0.35) +
            trophic_fit * w.get("trophic_fit", 0.25) +
            habitat_overlap * w.get("habitat_overlap", 0.15) +
            tile_overlap * w.get("tile_overlap", 0.15) +
            size_fit * w.get("size_fit", 0.10)
        )
        
        return np.clip(total_score, 0, 1).astype(np.float32)
    
    # ==================== 便捷方法 ====================
    
    def get_best_prey(
        self,
        predator: 'Species',
        all_species: Sequence['Species'],
        species_tiles: dict[str, set[int]] | None = None,
        top_k: int = 5,
        min_score: float = 0.2,
    ) -> list[tuple[str, float]]:
        """获取单个捕食者的最佳猎物列表
        
        Args:
            predator: 捕食者物种
            all_species: 所有物种
            species_tiles: 物种→地块映射
            top_k: 返回前K个
            min_score: 最低分数阈值
            
        Returns:
            [(prey_code, score), ...] 按分数降序
        """
        # 过滤出潜在猎物（营养级低于捕食者）
        pred_trophic = getattr(predator, 'trophic_level', 2.0) or 2.0
        prey_candidates = [
            sp for sp in all_species
            if sp.lineage_code != predator.lineage_code
            and sp.status == "alive"
            and (getattr(sp, 'trophic_level', 1.0) or 1.0) < pred_trophic
        ]
        
        if not prey_candidates:
            return []
        
        # 计算选择矩阵
        selection_matrix = self.compute_prey_selection_matrix(
            [predator], prey_candidates, species_tiles
        )
        
        scores = selection_matrix[0]  # (M,)
        
        # 排序并过滤
        results = []
        for i, prey in enumerate(prey_candidates):
            if scores[i] >= min_score:
                results.append((prey.lineage_code, float(scores[i])))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def compute_effective_prey_biomass(
        self,
        predator: 'Species',
        prey_candidates: Sequence['Species'],
        prey_selection_scores: np.ndarray,
        prey_biomass_by_tile: dict[str, dict[int, float]],
        tile_id: int,
    ) -> float:
        """计算捕食者在指定地块的有效猎物生物量
        
        有效猎物生物量 = Σ (猎物生物量 × 选择亲和度)
        
        Args:
            predator: 捕食者
            prey_candidates: 猎物列表（与 prey_selection_scores 对应）
            prey_selection_scores: 该捕食者对各猎物的选择分数 (M,)
            prey_biomass_by_tile: {lineage_code: {tile_id: biomass}}
            tile_id: 目标地块
            
        Returns:
            有效猎物生物量 (kg)
        """
        effective_biomass = 0.0
        
        for j, prey in enumerate(prey_candidates):
            prey_code = prey.lineage_code
            affinity = prey_selection_scores[j]
            
            # 获取该猎物在该地块的生物量
            tile_biomass = prey_biomass_by_tile.get(prey_code, {}).get(tile_id, 0)
            
            # 加权累加
            effective_biomass += tile_biomass * affinity
        
        return effective_biomass


# ==================== 工厂函数 ====================

_prey_affinity_service: PreyAffinityService | None = None


def get_prey_affinity_service(
    embedding_service: 'EmbeddingService | None' = None,
    force_new: bool = False,
) -> PreyAffinityService:
    """获取猎物亲和度服务单例
    
    如果没有传入 embedding_service，会尝试从 suitability_service 获取。
    """
    global _prey_affinity_service
    
    # 如果没有传入 embedding_service，尝试从其他服务获取
    if embedding_service is None:
        try:
            from ..geo.suitability_service import get_suitability_service
            suit_service = get_suitability_service()
            if suit_service.embeddings is not None:
                embedding_service = suit_service.embeddings
        except Exception:
            pass
    
    if _prey_affinity_service is None or force_new:
        _prey_affinity_service = PreyAffinityService(embedding_service)
    elif embedding_service is not None and _prey_affinity_service.embeddings is None:
        _prey_affinity_service.embeddings = embedding_service
    
    return _prey_affinity_service

