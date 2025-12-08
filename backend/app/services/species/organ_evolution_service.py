"""器官演化服务 - 自由器官演化系统

基于语义聚合的器官演化机制：
1. LLM 生成的器官概念通过 Embedding 与胚芽池比对
2. 语义相似（>阈值）则合并到现有胚芽，累加能量
3. 能量达到阈值时标记为成熟，下次分化时 LLM 将其升级
4. LLM 自由决定升级方向，同一胚芽可演化成不同器官

生物学基础：
- 表型可塑性的遗传同化：反复出现的特征最终固定
- 平行演化：相似压力下演化出相似结构
- 量变到质变：小突变累积后产生质的飞跃
- 发育约束：高级物种的发育程序抑制原始形态的重现
- 功能整合：同功能器官倾向于整合而非冗余共存
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from ...models.species import Species
    from ...services.system.embedding import EmbeddingService

logger = logging.getLogger(__name__)


# ============================================================
# 语义锚点定义（纯 Embedding 方式，无关键词）
# ============================================================
# 每个锚点用完整的自然语言描述来定义语义空间
# 通过 embedding 相似度判断，而非关键词匹配

# 功能类别语义锚点
FUNCTIONAL_CATEGORY_ANCHORS = {
    # 感知系统
    "vision": "视觉感知器官，用于接收光线和图像，包括各种形式的眼睛、感光结构、视网膜等光学感受器",
    "hearing": "听觉感知器官，用于接收声波和振动，包括耳朵、听觉毛、鼓膜等声波感受结构",
    "chemosense": "化学感知器官，用于感知气味和味道，包括嗅觉、味觉、化学感受器、触角的化学感应功能",
    "touch": "触觉感知器官，用于感知压力、温度和物理接触，包括触觉感受器、机械感受器、体表感觉神经",
    "electric": "电感知器官，用于感知电场和电流，包括侧线系统、电感受器、罗伦氏壶腹等电场探测器",
    
    # 运动系统
    "locomotion_aquatic": "水生运动器官，用于在水中游泳和移动，包括鳍、鞭毛、纤毛、喷水推进等水中推进结构",
    "locomotion_terrestrial": "陆生运动器官，用于在陆地上行走和爬行，包括肢体、腿、足、肌肉骨骼系统等陆地运动结构",
    "locomotion_aerial": "空中运动器官，用于飞行和滑翔，包括翅膀、翼膜、飞行肌等空中运动结构",
    
    # 呼吸系统
    "respiration": "呼吸器官，用于气体交换和获取氧气，包括鳃、肺、气管、气囊、皮肤呼吸等气体交换结构",
    
    # 消化系统
    "digestion": "消化器官，用于摄取和分解食物，包括口腔、胃、肠道、消化腺、食道等消化吸收结构",
    
    # 循环系统
    "circulation": "循环器官，用于输送血液和营养，包括心脏、血管、血液、淋巴系统等体液循环结构",
    
    # 防御系统
    "defense_passive": "被动防御器官，提供物理保护屏障，包括外壳、甲壳、鳞片、角质层、外骨骼等保护性覆盖物",
    "defense_active": "主动防御器官，用于主动攻击或震慑，包括毒刺、毒腺、放电器官、防御性棘刺等攻击性结构",
    
    # 代谢系统
    "metabolism": "代谢器官，用于能量转化和废物处理，包括肝脏、肾脏、排泄系统、解毒器官等代谢调节结构",
    
    # 生殖系统
    "reproduction": "生殖器官，用于繁殖和产生后代，包括卵巢、精巢、子宫、生殖管道等繁殖相关结构",
    
    # 光合/能量
    "photosynthesis": "光合器官，用于光合作用和能量固定，包括叶绿体、色素体、光合膜等光能转化结构",
}

# 复杂度等级语义锚点
COMPLEXITY_LEVEL_ANCHORS = {
    0: {
        "name": "分子级",
        "anchor": "分子级别的生物结构，如蛋白质、色素分子、受体分子、简单的纤毛或鞭毛等最基础的分子机器",
        "threshold_multiplier": 0.5,
        "min_body_size_cm": 0.0,
        "min_trophic": 0.0,
    },
    1: {
        "name": "细胞级",
        "anchor": "单个特化细胞水平的结构，如感光细胞、分泌细胞、收缩细胞、神经元等独立功能的细胞",
        "threshold_multiplier": 0.7,
        "min_body_size_cm": 0.0,
        "min_trophic": 0.0,
    },
    2: {
        "name": "组织级",
        "anchor": "由同类细胞组成的组织结构，如肌肉组织、上皮组织、神经组织、感光组织等细胞层面的集合",
        "threshold_multiplier": 1.0,
        "min_body_size_cm": 0.001,
        "min_trophic": 1.0,
    },
    3: {
        "name": "简单器官",
        "anchor": "初级或原始的简单器官，如眼点、简单触手、原始消化腔、基础的感觉器等早期演化阶段的器官",
        "threshold_multiplier": 1.5,
        "min_body_size_cm": 0.01,
        "min_trophic": 1.5,
    },
    4: {
        "name": "复杂器官",
        "anchor": "发达且特化的复杂器官，如眼杯、复杂消化道、鳃、特化的附肢等具有多种组织配合的功能单元",
        "threshold_multiplier": 2.5,
        "min_body_size_cm": 0.1,
        "min_trophic": 2.0,
    },
    5: {
        "name": "器官系统",
        "anchor": "高度整合的器官系统，如复眼、透镜眼、循环系统、完整的神经系统等多器官协调工作的复杂系统",
        "threshold_multiplier": 4.0,
        "min_body_size_cm": 1.0,
        "min_trophic": 2.5,
    },
}

# 环境压力语义锚点
PRESSURE_ANCHORS = {
    "predation": "捕食压力，来自捕食者的威胁，需要逃避追捕、防御攻击、快速反应等生存技能",
    "competition": "竞争压力，来自同种或异种的资源竞争，需要争夺食物、领地、配偶等生态位竞争",
    "starvation": "食物匮乏压力，食物稀缺或难以获取，需要提高觅食效率、储存能量、降低代谢",
    "oxygen_low": "低氧压力，环境氧气不足，需要提高呼吸效率、适应缺氧环境",
    "temperature_fluctuation": "温度波动压力，环境温度剧烈变化，需要体温调节、耐热耐寒适应",
    "light_limitation": "光照不足压力，环境光线微弱，需要增强感光能力或适应黑暗",
    "salinity": "盐度压力，环境盐分变化，需要调节渗透压和离子平衡",
    "desiccation": "干燥压力，面临脱水威胁，需要保水能力和耐旱适应",
    "toxin": "毒素压力，环境中存在有毒物质，需要解毒能力和毒素耐受",
    "pathogens": "病原压力，面临病原体感染威胁，需要免疫防御能力",
}


# ============================================================
# 语义锚点缓存（利用 L1/L2 缓存避免重复请求）
# ============================================================

class SemanticAnchorCache:
    """语义锚点 Embedding 缓存
    
    【设计原理】
    - 预先计算所有锚点描述的 embedding 并缓存
    - 利用 EmbeddingService 的内置 L1（内存）/ L2（磁盘）缓存
    - 批量生成减少 API 调用
    - 缓存键基于锚点文本的哈希，模型变更会自动失效
    
    【缓存层级】
    - L1: EmbeddingService._memory_cache（内存，最多10000条）
    - L2: EmbeddingService 磁盘缓存（持久化）
    - 本类只负责组织批量调用，实际缓存由 EmbeddingService 处理
    """
    
    def __init__(self):
        self._category_embeddings: dict[str, list[float]] = {}
        self._complexity_embeddings: dict[int, list[float]] = {}
        self._pressure_embeddings: dict[str, list[float]] = {}
        self._initialized = False
        self._embedding_service: "EmbeddingService | None" = None
    
    def initialize(self, embedding_service: "EmbeddingService") -> None:
        """初始化所有锚点的 embedding（批量请求，利用缓存）"""
        if self._initialized and self._embedding_service is embedding_service:
            return
        
        self._embedding_service = embedding_service
        
        if not embedding_service:
            logger.warning("[SemanticAnchorCache] 无 embedding 服务，锚点缓存跳过")
            return
        
        # 收集所有需要 embedding 的文本
        texts_to_embed = []
        text_to_key = []  # (type, key) 用于映射回结果
        
        # 功能类别锚点
        for cat, anchor in FUNCTIONAL_CATEGORY_ANCHORS.items():
            texts_to_embed.append(anchor)
            text_to_key.append(("category", cat))
        
        # 复杂度锚点
        for level, data in COMPLEXITY_LEVEL_ANCHORS.items():
            texts_to_embed.append(data["anchor"])
            text_to_key.append(("complexity", level))
        
        # 压力锚点
        for pressure, anchor in PRESSURE_ANCHORS.items():
            texts_to_embed.append(anchor)
            text_to_key.append(("pressure", pressure))
        
        # 批量生成 embedding（EmbeddingService 会自动使用缓存）
        try:
            embeddings = embedding_service.embed(texts_to_embed)
            
            for i, (emb_type, key) in enumerate(text_to_key):
                if emb_type == "category":
                    self._category_embeddings[key] = embeddings[i]
                elif emb_type == "complexity":
                    self._complexity_embeddings[key] = embeddings[i]
                elif emb_type == "pressure":
                    self._pressure_embeddings[key] = embeddings[i]
            
            self._initialized = True
            logger.info(
                f"[SemanticAnchorCache] 初始化完成: "
                f"{len(self._category_embeddings)} 类别, "
                f"{len(self._complexity_embeddings)} 复杂度, "
                f"{len(self._pressure_embeddings)} 压力"
            )
        except Exception as e:
            logger.warning(f"[SemanticAnchorCache] 初始化失败: {e}")
    
    def infer_functional_category(
        self, 
        organ_embedding: list[float],
        threshold: float = 0.5
    ) -> str | None:
        """通过 embedding 相似度推断功能类别
        
        Args:
            organ_embedding: 器官的 embedding 向量
            threshold: 最低相似度阈值
            
        Returns:
            最匹配的功能类别，或 None（无匹配）
        """
        if not self._category_embeddings or not organ_embedding:
            return None
        
        best_category = None
        best_similarity = threshold
        
        for cat, cat_emb in self._category_embeddings.items():
            sim = cosine_similarity(organ_embedding, cat_emb)
            if sim > best_similarity:
                best_similarity = sim
                best_category = cat
        
        return best_category
    
    def infer_complexity_level(
        self, 
        organ_embedding: list[float]
    ) -> int:
        """通过 embedding 相似度推断复杂度等级
        
        Args:
            organ_embedding: 器官的 embedding 向量
            
        Returns:
            复杂度等级 (0-5)，默认 2
        """
        if not self._complexity_embeddings or not organ_embedding:
            return 2  # 默认组织级
        
        best_level = 2
        best_similarity = 0.0
        
        for level, level_emb in self._complexity_embeddings.items():
            sim = cosine_similarity(organ_embedding, level_emb)
            if sim > best_similarity:
                best_similarity = sim
                best_level = level
        
        return best_level
    
    def infer_pressure(
        self, 
        organ_embedding: list[float],
        threshold: float = 0.4
    ) -> str:
        """通过 embedding 相似度推断关联压力
        
        Args:
            organ_embedding: 器官的 embedding 向量
            threshold: 最低相似度阈值
            
        Returns:
            最匹配的压力类型，默认 "competition"
        """
        if not self._pressure_embeddings or not organ_embedding:
            return "competition"
        
        best_pressure = "competition"
        best_similarity = threshold
        
        for pressure, pressure_emb in self._pressure_embeddings.items():
            sim = cosine_similarity(organ_embedding, pressure_emb)
            if sim > best_similarity:
                best_similarity = sim
                best_pressure = pressure
        
        return best_pressure
    
    def get_category_embedding(self, category: str) -> list[float] | None:
        """获取指定类别的 embedding"""
        return self._category_embeddings.get(category)
    
    def get_complexity_embedding(self, level: int) -> list[float] | None:
        """获取指定复杂度的 embedding"""
        return self._complexity_embeddings.get(level)
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized


# 模块级锚点缓存实例
_semantic_anchor_cache = SemanticAnchorCache()


def get_semantic_anchor_cache() -> SemanticAnchorCache:
    """获取语义锚点缓存实例"""
    return _semantic_anchor_cache


# ============================================================
# 配置加载
# ============================================================

def _load_organ_evolution_config():
    """从 settings.json 加载器官演化配置"""
    try:
        from ...core.config import PROJECT_ROOT
        from ...repositories.environment_repository import environment_repository
        ui_cfg = environment_repository.load_ui_config(PROJECT_ROOT / "data/settings.json")
        return ui_cfg.organ_evolution
    except Exception:
        return None


class OrganEvolutionConfigAdapter:
    """器官演化配置适配器 - 从 UIConfig 或默认值读取"""
    
    def __init__(self):
        self._config = None
    
    @property
    def config(self):
        if self._config is None:
            self._config = _load_organ_evolution_config()
        return self._config
    
    @property
    def MERGE_THRESHOLD(self) -> float:
        return self.config.merge_threshold if self.config else 0.82
    
    @property
    def BASE_ENERGY(self) -> float:
        return self.config.base_energy if self.config else 1.0
    
    @property
    def SIMILARITY_BONUS(self) -> float:
        return self.config.similarity_bonus if self.config else 0.5
    
    @property
    def PRESSURE_MATCH_BONUS(self) -> float:
        return self.config.pressure_match_bonus if self.config else 1.3
    
    @property
    def DECAY_PER_TURN(self) -> float:
        return self.config.decay_per_turn if self.config else 0.03
    
    @property
    def DEFAULT_MATURITY_THRESHOLD(self) -> float:
        return self.config.default_maturity_threshold if self.config else 5.0
    
    @property
    def TIER_THRESHOLD_MULTIPLIER(self) -> float:
        return self.config.tier_threshold_multiplier if self.config else 1.5
    
    @property
    def MAX_CONTRIBUTIONS_STORED(self) -> int:
        return self.config.max_contributions_stored if self.config else 5
    
    # ========== 新增：功能整合相关配置 ==========
    
    @property
    def ENABLE_FUNCTIONAL_INTEGRATION(self) -> bool:
        """启用功能类别整合（发育约束）"""
        return getattr(self.config, 'enable_functional_integration', True) if self.config else True
    
    @property
    def FUNCTIONAL_INTEGRATION_THRESHOLD(self) -> float:
        """功能整合的相似度阈值"""
        return getattr(self.config, 'functional_integration_threshold', 0.75) if self.config else 0.75
    
    # ========== 新增：复杂度约束相关配置 ==========
    
    @property
    def ENABLE_COMPLEXITY_CONSTRAINTS(self) -> bool:
        """启用器官复杂度约束"""
        return getattr(self.config, 'enable_complexity_constraints', True) if self.config else True
    
    @property
    def COMPLEXITY_UPGRADE_BONUS(self) -> float:
        """复杂度升级时的能量加成"""
        return getattr(self.config, 'complexity_upgrade_bonus', 0.5) if self.config else 0.5
    
    # ========== 新增：自然衰减清理配置 ==========
    
    @property
    def DECAY_START_TURNS(self) -> int:
        """开始衰减的未更新回合数"""
        return getattr(self.config, 'decay_start_turns', 5) if self.config else 5
    
    @property
    def CLEANUP_ENERGY_THRESHOLD(self) -> float:
        """清理胚芽的能量阈值"""
        return getattr(self.config, 'cleanup_energy_threshold', 0.1) if self.config else 0.1
    
    @property
    def CLEANUP_AGE_THRESHOLD(self) -> int:
        """清理胚芽的最小存活回合数"""
        return getattr(self.config, 'cleanup_age_threshold', 10) if self.config else 10


# ============================================================
# 辅助函数
# ============================================================

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """计算余弦相似度"""
    if not vec_a or not vec_b:
        return 0.0
    try:
        a = np.array(vec_a, dtype=float)
        b = np.array(vec_b, dtype=float)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    except Exception:
        return 0.0


def weighted_average_embedding(
    emb_a: list[float], 
    emb_b: list[float], 
    weight_a: float = 0.7
) -> list[float]:
    """加权平均两个 embedding 向量"""
    if not emb_a:
        return emb_b
    if not emb_b:
        return emb_a
    try:
        a = np.array(emb_a, dtype=float)
        b = np.array(emb_b, dtype=float)
        result = a * weight_a + b * (1 - weight_a)
        return result.tolist()
    except Exception:
        return emb_a


def generate_rudiment_id() -> str:
    """生成胚芽唯一ID"""
    return f"rud_{uuid.uuid4().hex[:8]}"


def generate_organ_id() -> str:
    """生成器官唯一ID"""
    return f"org_{uuid.uuid4().hex[:8]}"


def infer_functional_category_by_embedding(
    organ_embedding: list[float],
    threshold: float = 0.5
) -> str | None:
    """通过 embedding 相似度推断功能类别
    
    【纯语义方式】无关键词检查，完全依赖 embedding 相似度
    
    Args:
        organ_embedding: 器官的 embedding 向量
        threshold: 最低相似度阈值
        
    Returns:
        功能类别名称，或 None（无匹配）
    """
    cache = get_semantic_anchor_cache()
    return cache.infer_functional_category(organ_embedding, threshold)


def infer_complexity_level_by_embedding(organ_embedding: list[float]) -> int:
    """通过 embedding 相似度推断复杂度等级
    
    【纯语义方式】无关键词检查，完全依赖 embedding 相似度
    
    Args:
        organ_embedding: 器官的 embedding 向量
        
    Returns:
        复杂度等级 (0-5)，默认 2（组织级）
    """
    cache = get_semantic_anchor_cache()
    return cache.infer_complexity_level(organ_embedding)


def infer_pressure_by_embedding(
    organ_embedding: list[float],
    threshold: float = 0.4
) -> str:
    """通过 embedding 相似度推断关联压力
    
    【纯语义方式】无关键词检查，完全依赖 embedding 相似度
    
    Args:
        organ_embedding: 器官的 embedding 向量
        threshold: 最低相似度阈值
        
    Returns:
        压力类型，默认 "competition"
    """
    cache = get_semantic_anchor_cache()
    return cache.infer_pressure(organ_embedding, threshold)


def get_species_max_complexity(species: "Species") -> int:
    """根据物种特征计算可演化的最大器官复杂度
    
    基于：
    - 体型（body_length_cm）
    - 营养级（trophic_level）
    - 当前已有器官的最高复杂度（可突破）
    """
    body_size = species.morphology_stats.get("body_length_cm", 0.1) or 0.1
    trophic = species.trophic_level or 1.0
    
    # 基于体型和营养级计算基础上限
    max_complexity = 0
    for level, config in COMPLEXITY_LEVEL_ANCHORS.items():
        if body_size >= config["min_body_size_cm"] and trophic >= config["min_trophic"]:
            max_complexity = max(max_complexity, level)
    
    # 如果已有更高复杂度的器官，允许继续发展（已突破的不退化）
    for organ in (species.evolved_organs or {}).values():
        organ_complexity = organ.get("complexity_level", 2)
        max_complexity = max(max_complexity, organ_complexity)
    
    return max_complexity


def get_highest_organ_in_category_by_embedding(
    species: "Species", 
    target_category_embedding: list[float],
    category_threshold: float = 0.6
) -> tuple[str | None, dict | None, int]:
    """通过 embedding 相似度获取物种在相似功能类别中最高级的器官
    
    【纯语义方式】不再依赖器官保存的类别标签，
    而是通过 embedding 相似度动态判断功能归属
    
    Args:
        species: 物种对象
        target_category_embedding: 目标功能类别的 embedding
        category_threshold: 功能类别匹配的相似度阈值
    
    Returns:
        (organ_id, organ_data, tier) 或 (None, None, 0)
    """
    if not target_category_embedding:
        return None, None, 0
    
    best_id = None
    best_organ = None
    best_tier = 0
    
    for organ_id, organ in (species.evolved_organs or {}).items():
        organ_emb = organ.get("embedding", [])
        if not organ_emb:
            continue
        
        # 通过 embedding 相似度判断是否属于同一功能类别
        similarity = cosine_similarity(organ_emb, target_category_embedding)
        if similarity >= category_threshold:
            tier = organ.get("tier", 1)
            if tier > best_tier:
                best_tier = tier
                best_id = organ_id
                best_organ = organ
    
    return best_id, best_organ, best_tier


# ============================================================
# 器官演化服务
# ============================================================

class OrganEvolutionService:
    """器官演化服务
    
    核心职责：
    1. 处理 LLM 返回的器官演化数据，更新胚芽池
    2. 检测成熟的胚芽，生成升级上下文
    3. 处理升级结果，创建成熟器官
    
    【语义判断】
    - 所有类别/复杂度/压力的判断均通过 embedding 相似度
    - 无关键词硬编码，保证最大演化自由度
    - 利用 EmbeddingService 的 L1/L2 缓存避免重复请求
    """
    
    def __init__(self, embedding_service: "EmbeddingService | None" = None):
        self.embedding = embedding_service
        self.config = OrganEvolutionConfigAdapter()
        self._anchor_cache = get_semantic_anchor_cache()
        
        # 初始化语义锚点缓存
        if embedding_service:
            self._anchor_cache.initialize(embedding_service)
    
    # ------------------------------------------------------------------ #
    # 主入口：处理分化后的器官演化
    # ------------------------------------------------------------------ #
    
    def process_organ_evolution(
        self,
        species: "Species",
        llm_organs: list[dict],
        turn: int,
        current_pressures: list[str] | None = None
    ) -> dict[str, Any]:
        """处理 LLM 返回的 organ_evolution，更新胚芽池
        
        Args:
            species: 物种对象
            llm_organs: LLM 返回的 organ_evolution 列表
            turn: 当前回合
            current_pressures: 当前环境压力类型列表
            
        Returns:
            处理结果 {
                "merged": [合并到现有胚芽的器官名],
                "created": [新创建的胚芽名],
                "matured": [新成熟的胚芽名],
                "upgraded": [升级完成的器官名]
            }
        """
        result = {
            "merged": [],
            "created": [],
            "matured": [],
            "upgraded": []
        }
        
        if not llm_organs:
            return result
        
        # 确保字段初始化
        if species.organ_rudiments is None:
            species.organ_rudiments = {}
        if species.evolved_organs is None:
            species.evolved_organs = {}
        
        current_pressures = current_pressures or []
        
        for organ_data in llm_organs:
            action = organ_data.get("action", "enhance")
            
            # 处理升级动作
            if action == "upgrade":
                upgrade_result = self._process_upgrade(species, organ_data, turn)
                if upgrade_result:
                    result["upgraded"].append(upgrade_result)
                continue
            
            # 处理普通器官演化（enhance/initiate）
            process_result = self._process_single_organ(
                species, organ_data, turn, current_pressures
            )
            
            if process_result["action"] == "merged":
                result["merged"].append(process_result["name"])
                if process_result.get("is_mature"):
                    result["matured"].append(process_result["name"])
            elif process_result["action"] == "created":
                result["created"].append(process_result["name"])
        
        # 清理过旧的胚芽（能量衰减后过低的）
        self._cleanup_rudiments(species, turn)
        
        return result
    
    def _process_single_organ(
        self,
        species: "Species",
        organ_data: dict,
        turn: int,
        current_pressures: list[str]
    ) -> dict:
        """处理单个器官演化数据
        
        【生物学机制】（全部基于 Embedding，无关键词检查）
        1. 功能类别整合（发育约束）：如果物种已有该功能类别的高级器官，
           新的低级器官会被整合到现有器官的升级能量中
        2. 复杂度约束：根据物种体型/营养级限制可演化的器官复杂度
        3. 语义聚合：相似器官概念合并累积能量
        
        Returns:
            {"action": "merged"|"created"|"integrated", "name": str, "is_mature": bool}
        """
        # 提取器官描述用于 embedding
        structure_name = organ_data.get("structure_name", "")
        description = organ_data.get("description", "")
        organ_desc = f"{structure_name}: {description}" if description else structure_name
        
        if not organ_desc.strip():
            return {"action": "skipped", "name": "", "is_mature": False}
        
        # 【关键】先生成 embedding，后续所有判断都基于此
        new_embedding = self._get_embedding(organ_desc)
        if not new_embedding:
            # 没有 embedding 服务时，使用简单的名称匹配
            return self._fallback_process(species, organ_data, turn, current_pressures)
        
        # ========== 【A+D】功能类别整合检查（基于 Embedding）==========
        if self.config.ENABLE_FUNCTIONAL_INTEGRATION:
            integration_result = self._check_functional_integration_by_embedding(
                species, organ_data, new_embedding, structure_name, turn, current_pressures
            )
            if integration_result:
                return integration_result
        
        # ========== 【B】复杂度约束检查（基于 Embedding）==========
        if self.config.ENABLE_COMPLEXITY_CONSTRAINTS:
            # 使用 embedding 推断复杂度
            new_complexity = infer_complexity_level_by_embedding(new_embedding)
            max_complexity = get_species_max_complexity(species)
            
            if new_complexity > max_complexity:
                # 复杂度超出物种能力，降级处理
                logger.debug(
                    f"[器官演化] {species.common_name} 的 '{structure_name}' "
                    f"复杂度 {new_complexity} 超出上限 {max_complexity}，降级为上限"
                )
                new_complexity = max_complexity
            
            # 保存复杂度信息到 organ_data 供后续使用
            organ_data["_inferred_complexity"] = new_complexity
        
        # 在胚芽池中搜索相似器官
        best_match = None
        best_similarity = 0.0
        
        for rudiment_id, rudiment in species.organ_rudiments.items():
            if rudiment.get("is_mature"):
                continue  # 跳过已成熟的胚芽
            
            rudiment_emb = rudiment.get("embedding", [])
            if not rudiment_emb:
                continue
            
            sim = cosine_similarity(new_embedding, rudiment_emb)
            if sim > best_similarity:
                best_similarity = sim
                best_match = (rudiment_id, rudiment)
        
        # 也检查已成熟器官（可能继续升级）
        for organ_id, organ in species.evolved_organs.items():
            organ_emb = organ.get("embedding", [])
            if not organ_emb:
                continue
            
            sim = cosine_similarity(new_embedding, organ_emb)
            if sim > best_similarity:
                # 成熟器官匹配时，累加升级能量
                self._add_upgrade_energy_by_embedding(
                    species, organ_id, sim, new_embedding, current_pressures
                )
                return {"action": "merged", "name": organ.get("name", ""), "is_mature": False}
        
        # 决定合并还是创建
        if best_match and best_similarity >= self.config.MERGE_THRESHOLD:
            # 合并到现有胚芽
            return self._merge_to_rudiment(
                species, best_match, new_embedding, organ_data, 
                best_similarity, turn, current_pressures
            )
        else:
            # 创建新胚芽（不再有硬性数量限制，依靠自然衰减清理）
            return self._create_rudiment(
                species, organ_data, new_embedding, turn, current_pressures
            )
    
    def _check_functional_integration_by_embedding(
        self,
        species: "Species",
        organ_data: dict,
        new_embedding: list[float],
        structure_name: str,
        turn: int,
        current_pressures: list[str]
    ) -> dict | None:
        """【发育约束】通过 Embedding 检查是否应该整合到现有同功能器官
        
        【纯语义方式】无关键词检查，通过 embedding 相似度：
        1. 判断新器官属于哪个功能类别
        2. 查找物种已有的同类别器官
        3. 比较复杂度决定是整合还是允许创建
        
        这模拟了生物学中的"发育约束"：
        - 高级生物的发育程序已固化，不易产生原始形态
        - 同功能器官倾向于整合而非冗余共存
        
        Returns:
            处理结果字典，或 None（不需要整合，继续正常处理）
        """
        if not self._anchor_cache.is_initialized:
            return None
        
        # 【Embedding】推断新器官的功能类别
        new_category = infer_functional_category_by_embedding(
            new_embedding, 
            threshold=self.config.FUNCTIONAL_INTEGRATION_THRESHOLD
        )
        if not new_category:
            return None  # 无法推断类别，正常处理
        
        # 获取该功能类别的锚点 embedding
        category_embedding = self._anchor_cache.get_category_embedding(new_category)
        if not category_embedding:
            return None
        
        # 【Embedding】检查物种是否已有该类别的成熟器官
        existing_id, existing_organ, existing_tier = get_highest_organ_in_category_by_embedding(
            species, 
            category_embedding,
            category_threshold=self.config.FUNCTIONAL_INTEGRATION_THRESHOLD
        )
        
        if not existing_organ:
            return None  # 没有同类别器官，正常处理
        
        # 【Embedding】推断复杂度
        new_complexity = infer_complexity_level_by_embedding(new_embedding)
        existing_complexity = existing_organ.get("complexity_level", 2)
        
        # 如果新器官复杂度 <= 现有器官，整合到现有器官的升级能量
        if new_complexity <= existing_complexity:
            # 计算整合能量（较低复杂度贡献较少）
            complexity_factor = (new_complexity + 1) / (existing_complexity + 1)
            integration_energy = self.config.BASE_ENERGY * complexity_factor
            
            # 添加到现有器官的升级能量
            existing_organ["upgrade_energy"] = existing_organ.get("upgrade_energy", 0) + integration_energy
            species.evolved_organs[existing_id] = existing_organ
            
            # 检查是否达到升级阈值
            threshold = existing_organ.get("upgrade_threshold", self.config.DEFAULT_MATURITY_THRESHOLD * 2)
            if existing_organ["upgrade_energy"] >= threshold:
                existing_organ["is_ready_for_upgrade"] = True
            
            logger.debug(
                f"[功能整合] {species.common_name}: '{structure_name}' (复杂度{new_complexity}) "
                f"整合到 '{existing_organ.get('name')}' (复杂度{existing_complexity}, Tier{existing_tier})"
            )
            
            return {
                "action": "integrated",
                "name": existing_organ.get("name", ""),
                "is_mature": False,
                "integrated_to": existing_organ.get("name"),
                "energy_contributed": integration_energy
            }
        
        # 如果新器官复杂度更高，可以创建新胚芽（演化突破）
        logger.debug(
            f"[演化突破] {species.common_name}: '{structure_name}' (复杂度{new_complexity}) "
            f"高于现有 '{existing_organ.get('name')}' (复杂度{existing_complexity})，允许创建新胚芽"
        )
        return None
    
    def _merge_to_rudiment(
        self,
        species: "Species",
        match: tuple[str, dict],
        new_embedding: list[float],
        organ_data: dict,
        similarity: float,
        turn: int,
        current_pressures: list[str]
    ) -> dict:
        """合并到现有胚芽"""
        rudiment_id, rudiment = match
        
        # 【Embedding】计算能量贡献
        energy = self._calculate_energy_by_embedding(similarity, new_embedding, current_pressures)
        
        # 更新胚芽
        rudiment["accumulated_energy"] = rudiment.get("accumulated_energy", 0) + energy
        rudiment["embedding"] = weighted_average_embedding(
            rudiment.get("embedding", []), new_embedding, weight_a=0.7
        )
        rudiment["last_updated_turn"] = turn
        
        # 记录贡献（使用 embedding 推断压力）
        inferred_pressure = self._infer_pressure_by_embedding(new_embedding)
        contributions = rudiment.get("recent_contributions", [])
        contributions.append({
            "turn": turn,
            "desc": organ_data.get("structure_name", ""),
            "energy": energy,
            "pressure": inferred_pressure
        })
        # 只保留最近的几条
        rudiment["recent_contributions"] = contributions[-self.config.MAX_CONTRIBUTIONS_STORED:]
        
        # 更新关联压力
        if current_pressures:
            existing_pressures = set(rudiment.get("associated_pressures", []))
            existing_pressures.update(current_pressures[:2])
            rudiment["associated_pressures"] = list(existing_pressures)[:5]
        
        # 检查是否成熟
        threshold = rudiment.get("maturity_threshold", self.config.DEFAULT_MATURITY_THRESHOLD)
        is_mature = rudiment["accumulated_energy"] >= threshold
        if is_mature and not rudiment.get("is_mature"):
            rudiment["is_mature"] = True
            logger.info(
                f"[器官演化] {species.common_name} 的器官胚芽 '{rudiment.get('name')}' "
                f"已成熟 (能量 {rudiment['accumulated_energy']:.1f}/{threshold:.1f})"
            )
        
        species.organ_rudiments[rudiment_id] = rudiment
        
        return {
            "action": "merged",
            "name": rudiment.get("name", ""),
            "is_mature": is_mature
        }
    
    def _create_rudiment(
        self,
        species: "Species",
        organ_data: dict,
        embedding: list[float],
        turn: int,
        current_pressures: list[str]
    ) -> dict:
        """创建新胚芽
        
        【无硬性数量限制】依靠自然衰减清理机制维持平衡
        """
        rudiment_id = generate_rudiment_id()
        name = organ_data.get("structure_name", "未命名器官")
        
        # 【Embedding】推断关联压力
        inferred_pressure = self._infer_pressure_by_embedding(embedding)
        
        new_rudiment = {
            "id": rudiment_id,
            "name": name,
            "description": organ_data.get("description", ""),
            "embedding": embedding,
            "accumulated_energy": self.config.BASE_ENERGY,
            "maturity_threshold": self.config.DEFAULT_MATURITY_THRESHOLD,
            "recent_contributions": [{
                "turn": turn,
                "desc": name,
                "energy": self.config.BASE_ENERGY,
                "pressure": inferred_pressure
            }],
            "associated_pressures": current_pressures[:3] if current_pressures else [],
            "is_mature": False,
            "created_turn": turn,
            "last_updated_turn": turn
        }
        
        species.organ_rudiments[rudiment_id] = new_rudiment
        
        logger.debug(
            f"[器官演化] {species.common_name} 创建新器官胚芽: '{name}'"
        )
        
        return {
            "action": "created",
            "name": name,
            "is_mature": False
        }
    
    def _process_upgrade(
        self,
        species: "Species",
        organ_data: dict,
        turn: int
    ) -> str | None:
        """处理器官升级动作
        
        Args:
            species: 物种对象
            organ_data: LLM 返回的升级数据
            turn: 当前回合
            
        Returns:
            升级后的器官名称，失败返回 None
        """
        source_rudiment = organ_data.get("source_rudiment", "")
        new_name = organ_data.get("new_organ_name", "")
        new_description = organ_data.get("new_description", "")
        parameters = organ_data.get("parameters", {})
        
        if not source_rudiment or not new_name:
            return None
        
        # 查找源胚芽
        source_id = None
        source_data = None
        for rid, rudiment in species.organ_rudiments.items():
            if rudiment.get("name") == source_rudiment or rid == source_rudiment:
                source_id = rid
                source_data = rudiment
                break
        
        if not source_data:
            logger.warning(f"[器官演化] 未找到源胚芽: {source_rudiment}")
            return None
        
        # 创建成熟器官
        organ_id = generate_organ_id()
        evolution_path = [source_data.get("name", source_rudiment)]
        
        # 获取 embedding（复用源胚芽的或重新生成）
        organ_desc = f"{new_name}: {new_description}"
        new_embedding = self._get_embedding(organ_desc)
        if not new_embedding:
            new_embedding = source_data.get("embedding", [])
        
        # 【Embedding】推断复杂度和功能类别
        complexity_level = 2  # 默认组织级
        functional_category = None
        if new_embedding and self._anchor_cache.is_initialized:
            complexity_level = infer_complexity_level_by_embedding(new_embedding)
            functional_category = infer_functional_category_by_embedding(new_embedding)
        
        new_organ = {
            "id": organ_id,
            "name": new_name,
            "description": new_description,
            "embedding": new_embedding,
            "parameters": parameters,
            "tier": 1,
            "complexity_level": complexity_level,  # 保存复杂度用于后续整合判断
            "functional_category": functional_category,  # 保存功能类别
            "evolution_path": evolution_path,
            "upgrade_energy": 0.0,
            "upgrade_threshold": self.config.DEFAULT_MATURITY_THRESHOLD * self.config.TIER_THRESHOLD_MULTIPLIER,
            "source_rudiment_id": source_id,
            "created_turn": turn,
            "last_upgraded_turn": turn
        }
        
        species.evolved_organs[organ_id] = new_organ
        
        # 重置源胚芽（保留用于继续升级，但重置能量）
        source_data["accumulated_energy"] = 0.0
        source_data["is_mature"] = False
        source_data["maturity_threshold"] *= self.config.TIER_THRESHOLD_MULTIPLIER
        source_data["last_updated_turn"] = turn
        species.organ_rudiments[source_id] = source_data
        
        # 同时更新到旧的 organs 字段以保持兼容
        self._sync_to_legacy_organs(species, new_organ, organ_data)
        
        logger.info(
            f"[器官演化] {species.common_name} 器官升级: "
            f"'{source_rudiment}' → '{new_name}' (Tier 1, 复杂度 {complexity_level})"
        )
        
        return new_name
    
    def _sync_to_legacy_organs(
        self, 
        species: "Species", 
        new_organ: dict,
        organ_data: dict
    ) -> None:
        """同步到旧的 organs 字段以保持兼容性
        
        【纯语义方式】通过 Embedding 推断功能类别，无关键词
        """
        # 优先使用 organ_data 中的类别
        category = organ_data.get("functional_category", "")
        
        # 如果没有指定类别，通过 embedding 推断
        if not category or category == "special":
            organ_embedding = new_organ.get("embedding", [])
            if organ_embedding and self._anchor_cache.is_initialized:
                inferred_category = infer_functional_category_by_embedding(
                    organ_embedding, threshold=0.4
                )
                if inferred_category:
                    # 映射到 legacy 类别名
                    category_mapping = {
                        "vision": "sensory",
                        "hearing": "sensory",
                        "chemosense": "sensory",
                        "touch": "sensory",
                        "electric": "sensory",
                        "locomotion_aquatic": "locomotion",
                        "locomotion_terrestrial": "locomotion",
                        "locomotion_aerial": "locomotion",
                        "respiration": "respiratory",
                        "digestion": "digestive",
                        "circulation": "circulatory",
                        "defense_passive": "defense",
                        "defense_active": "defense",
                        "metabolism": "metabolic",
                        "reproduction": "reproductive",
                        "photosynthesis": "photosynthetic",
                    }
                    category = category_mapping.get(inferred_category, "special")
                else:
                    category = "special"
            else:
                category = "special"
        
        if species.organs is None:
            species.organs = {}
        
        species.organs[category] = {
            "type": new_organ["name"],
            "parameters": new_organ.get("parameters", {}),
            "acquired_turn": new_organ.get("created_turn", 0),
            "is_active": True,
            "maturity": 1.0,
            "tier": new_organ.get("tier", 1),
            "evolution_path": new_organ.get("evolution_path", [])
        }
    
    def _add_upgrade_energy_by_embedding(
        self,
        species: "Species",
        organ_id: str,
        similarity: float,
        new_embedding: list[float],
        current_pressures: list[str]
    ) -> None:
        """为已成熟器官添加升级能量（基于 Embedding 判断压力匹配）"""
        organ = species.evolved_organs.get(organ_id)
        if not organ:
            return
        
        energy = self.config.BASE_ENERGY * similarity
        
        # 【Embedding】通过语义相似度判断压力匹配
        if current_pressures and new_embedding:
            inferred_pressure = infer_pressure_by_embedding(new_embedding)
            if inferred_pressure in current_pressures:
                energy *= self.config.PRESSURE_MATCH_BONUS
        
        organ["upgrade_energy"] = organ.get("upgrade_energy", 0) + energy
        
        # 检查是否达到升级阈值
        threshold = organ.get("upgrade_threshold", self.config.DEFAULT_MATURITY_THRESHOLD * 2)
        if organ["upgrade_energy"] >= threshold:
            organ["is_ready_for_upgrade"] = True
    
    # ------------------------------------------------------------------ #
    # 构建成熟器官上下文（用于分化 Prompt）
    # ------------------------------------------------------------------ #
    
    def build_mature_organs_context(self, species: "Species") -> str:
        """构建成熟器官上下文，注入到分化 prompt
        
        Args:
            species: 物种对象
            
        Returns:
            成熟器官的 prompt 上下文字符串
        """
        if not species.organ_rudiments:
            return ""
        
        mature_rudiments = [
            (rid, r) for rid, r in species.organ_rudiments.items() 
            if r.get("is_mature")
        ]
        
        # 也检查需要升级的已成熟器官
        ready_organs = [
            (oid, o) for oid, o in (species.evolved_organs or {}).items()
            if o.get("is_ready_for_upgrade")
        ]
        
        if not mature_rudiments and not ready_organs:
            return ""
        
        lines = ["=== 🔬 待升级器官（请在本次分化中升级）==="]
        
        if mature_rudiments:
            lines.append("\n【新成熟的器官胚芽】")
            for rid, r in mature_rudiments:
                lines.append(f"• {r.get('name', rid)}")
                lines.append(f"  描述：{r.get('description', '无')[:50]}...")
                lines.append(f"  能量：{r.get('accumulated_energy', 0):.1f}/{r.get('maturity_threshold', 5):.1f} ✓")
                
                contributions = r.get("recent_contributions", [])
                if contributions:
                    contrib_names = [c.get("desc", "") for c in contributions[-3:] if c.get("desc")]
                    if contrib_names:
                        lines.append(f"  演化来源：{', '.join(contrib_names)}")
                
                pressures = r.get("associated_pressures", [])
                if pressures:
                    lines.append(f"  关联压力：{', '.join(pressures[:3])}")
                lines.append("")
        
        if ready_organs:
            lines.append("\n【可继续升级的成熟器官】")
            for oid, o in ready_organs:
                tier = o.get("tier", 1)
                lines.append(f"• {o.get('name', oid)} (当前 Tier {tier})")
                lines.append(f"  演化路径：{' → '.join(o.get('evolution_path', []))}")
                lines.append(f"  升级能量：{o.get('upgrade_energy', 0):.1f}/{o.get('upgrade_threshold', 10):.1f} ✓")
                lines.append("")
        
        lines.append("【升级输出格式】")
        lines.append("在 organ_evolution 中添加 action: \"upgrade\" 项：")
        lines.append("{")
        lines.append("  \"action\": \"upgrade\",")
        lines.append("  \"source_rudiment\": \"胚芽名称（必须匹配上方列表）\",")
        lines.append("  \"new_organ_name\": \"升级后的器官名称（自由命名）\",")
        lines.append("  \"new_description\": \"50-80字器官功能描述\",")
        lines.append("  \"parameters\": {\"参数名\": 数值},")
        lines.append("  \"functional_category\": \"功能分类\",")
        lines.append("  \"evolution_rationale\": \"演化机制解释\"")
        lines.append("}")
        lines.append("")
        lines.append("【升级方向自由度】")
        lines.append("同一器官胚芽可根据环境演化成不同器官：")
        lines.append("- 深海 + 光感受细胞 → 生物发光探测器 / 压力感应器")
        lines.append("- 浅海 + 光感受细胞 → 凹陷眼杯 / 色觉感应器")
        lines.append("- 捕食压力 + 光感受细胞 → 广角复眼 / 动态追踪器")
        lines.append("你可以完全自由地决定升级方向，只需符合物种生态位和环境压力。")
        
        return "\n".join(lines)
    
    # ------------------------------------------------------------------ #
    # 每回合维护
    # ------------------------------------------------------------------ #
    
    def decay_rudiments(self, species: "Species", turn: int) -> None:
        """每回合衰减胚芽能量（用于清理长期未更新的胚芽）"""
        if not species.organ_rudiments:
            return
        
        for rid, rudiment in list(species.organ_rudiments.items()):
            if rudiment.get("is_mature"):
                continue  # 成熟的不衰减
            
            last_update = rudiment.get("last_updated_turn", 0)
            turns_since_update = turn - last_update
            
            if turns_since_update > 3:  # 超过3回合未更新才开始衰减
                decay = self.config.DECAY_PER_TURN * (turns_since_update - 3)
                rudiment["accumulated_energy"] = max(
                    0, rudiment.get("accumulated_energy", 0) - decay
                )
    
    def _cleanup_rudiments(self, species: "Species", turn: int) -> None:
        """清理能量过低的胚芽"""
        if not species.organ_rudiments:
            return
        
        to_remove = []
        for rid, rudiment in species.organ_rudiments.items():
            # 保留成熟的胚芽
            if rudiment.get("is_mature"):
                continue
            # 移除能量为0且创建超过5回合的胚芽
            if rudiment.get("accumulated_energy", 0) <= 0:
                created = rudiment.get("created_turn", 0)
                if turn - created > 5:
                    to_remove.append(rid)
        
        for rid in to_remove:
            name = species.organ_rudiments[rid].get("name", rid)
            del species.organ_rudiments[rid]
            logger.debug(f"[器官演化] 清理休眠胚芽: {name}")
    
    
    # ------------------------------------------------------------------ #
    # 辅助方法
    # ------------------------------------------------------------------ #
    
    def _get_embedding(self, text: str) -> list[float] | None:
        """获取文本的 embedding 向量"""
        if not self.embedding or not text.strip():
            return None
        try:
            return self.embedding.embed_single(text)
        except Exception as e:
            logger.warning(f"[器官演化] Embedding 生成失败: {e}")
            return None
    
    def _calculate_energy_by_embedding(
        self,
        similarity: float,
        organ_embedding: list[float],
        current_pressures: list[str]
    ) -> float:
        """计算能量贡献（基于 Embedding 判断压力匹配）"""
        energy = self.config.BASE_ENERGY
        energy += similarity * self.config.SIMILARITY_BONUS
        
        # 【Embedding】通过语义相似度检查压力匹配
        if organ_embedding and current_pressures:
            inferred_pressure = infer_pressure_by_embedding(organ_embedding)
            if inferred_pressure in current_pressures:
                energy *= self.config.PRESSURE_MATCH_BONUS
        
        return energy
    
    def _infer_pressure_by_embedding(self, organ_embedding: list[float]) -> str:
        """通过 Embedding 推断关联压力
        
        【纯语义方式】无关键词检查，通过 embedding 与压力锚点的相似度判断
        """
        if not organ_embedding:
            return "competition"
        
        return infer_pressure_by_embedding(organ_embedding)
    
    def _fallback_process(
        self,
        species: "Species",
        organ_data: dict,
        turn: int,
        current_pressures: list[str]
    ) -> dict:
        """无 embedding 服务时的回退处理（简单名称匹配）
        
        【注意】这是降级方案，仅在 embedding 服务不可用时使用
        建议始终配置 embedding 服务以获得最佳效果
        """
        from difflib import SequenceMatcher
        
        name = organ_data.get("structure_name", "")
        if not name:
            return {"action": "skipped", "name": "", "is_mature": False}
        
        # 简单的名称相似度匹配
        best_match = None
        best_ratio = 0.0
        
        for rid, rudiment in species.organ_rudiments.items():
            if rudiment.get("is_mature"):
                continue
            rudiment_name = rudiment.get("name", "")
            ratio = SequenceMatcher(None, name, rudiment_name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = (rid, rudiment)
        
        if best_match and best_ratio >= 0.6:  # 名称相似度阈值较低
            rudiment_id, rudiment = best_match
            energy = self.config.BASE_ENERGY * (0.5 + best_ratio * 0.5)
            rudiment["accumulated_energy"] = rudiment.get("accumulated_energy", 0) + energy
            rudiment["last_updated_turn"] = turn
            
            # 记录贡献
            contributions = rudiment.get("recent_contributions", [])
            contributions.append({"turn": turn, "desc": name, "energy": energy})
            rudiment["recent_contributions"] = contributions[-self.config.MAX_CONTRIBUTIONS_STORED:]
            
            # 检查成熟
            threshold = rudiment.get("maturity_threshold", self.config.DEFAULT_MATURITY_THRESHOLD)
            is_mature = rudiment["accumulated_energy"] >= threshold
            if is_mature:
                rudiment["is_mature"] = True
            
            species.organ_rudiments[rudiment_id] = rudiment
            return {"action": "merged", "name": rudiment.get("name", ""), "is_mature": is_mature}
        else:
            # 创建新胚芽（无 embedding，无硬性数量限制）
            rudiment_id = generate_rudiment_id()
            new_rudiment = {
                "id": rudiment_id,
                "name": name,
                "description": organ_data.get("description", ""),
                "embedding": [],
                "accumulated_energy": self.config.BASE_ENERGY,
                "maturity_threshold": self.config.DEFAULT_MATURITY_THRESHOLD,
                "recent_contributions": [{"turn": turn, "desc": name}],
                "associated_pressures": current_pressures[:3] if current_pressures else [],
                "is_mature": False,
                "created_turn": turn,
                "last_updated_turn": turn
            }
            species.organ_rudiments[rudiment_id] = new_rudiment
            return {"action": "created", "name": name, "is_mature": False}


# 模块级单例（可选）
_organ_evolution_service: OrganEvolutionService | None = None


def get_organ_evolution_service(
    embedding_service: "EmbeddingService | None" = None
) -> OrganEvolutionService:
    """获取器官演化服务实例"""
    global _organ_evolution_service
    if _organ_evolution_service is None:
        _organ_evolution_service = OrganEvolutionService(embedding_service)
    elif embedding_service and not _organ_evolution_service.embedding:
        # 后期设置 embedding 服务时，同时初始化锚点缓存
        _organ_evolution_service.embedding = embedding_service
        _organ_evolution_service._anchor_cache.initialize(embedding_service)
    return _organ_evolution_service
