"""Trait配置和验证工具"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ==================== 地质时代配置 ====================
# 游戏从28亿年前开始，每回合50万年
# 时代上限会随回合数**渐进式增长**，体现生物复杂度的演化
# 
# 设计理念：
# - 早期时代（太古宙）：上限较低，生物简单
# - 随时代推进：上限不断提升，允许更复杂的生物
# - 5600回合后：继续按公式增长，无上限限制

# 基础上限（太古宙起点，所有物种从这里开始）
ERA_BASE_LIMITS = {
    "single": 5,   # 单属性基础上限
    "total": 25,   # 属性总和基础上限
}

# 每100回合的增长量（渐进式增长）
ERA_GROWTH_PER_100_TURNS = {
    "single": 0.25,  # 每100回合单属性上限+0.25
    "total": 1.5,    # 每100回合总和上限+1.5
}

# 地质时代定义（主要用于描述和里程碑）
GEOLOGICAL_ERAS = {
    # 太古宙末期（28-25亿年前）：原始单细胞时代
    "archean": {
        "start_turn": 0,
        "end_turn": 600,  # 0-600回合（3亿年）
        "name": "太古宙",
        "name_en": "Archean",
        "description": "原始生命时代，只有简单的原核生物",
        "milestone": "生命起源",
    },
    # 元古宙早期（25-18亿年前）：真核生物出现
    "proterozoic_early": {
        "start_turn": 600,
        "end_turn": 2000,  # 600-2000回合（7亿年）
        "name": "元古宙早期",
        "name_en": "Early Proterozoic", 
        "description": "真核生物和光合作用出现，大氧化事件",
        "milestone": "真核生物",
    },
    # 元古宙中期（18-10亿年前）：多细胞生物萌芽
    "proterozoic_middle": {
        "start_turn": 2000,
        "end_turn": 3600,  # 2000-3600回合（8亿年）
        "name": "元古宙中期",
        "name_en": "Middle Proterozoic",
        "description": "多细胞生物开始出现，真核藻类繁盛",
        "milestone": "多细胞生物",
    },
    # 元古宙晚期（10-5.4亿年前）：埃迪卡拉纪生物群
    "proterozoic_late": {
        "start_turn": 3600,
        "end_turn": 4720,  # 3600-4720回合（5.6亿年）
        "name": "元古宙晚期",
        "name_en": "Late Proterozoic",
        "description": "埃迪卡拉生物群，软体动物兴起",
        "milestone": "动物起源",
    },
    # 古生代早期（5.4-4亿年前）：寒武纪大爆发
    "paleozoic_early": {
        "start_turn": 4720,
        "end_turn": 5000,  # 4720-5000回合（1.4亿年）
        "name": "古生代早期",
        "name_en": "Early Paleozoic",
        "description": "寒武纪大爆发，三叶虫时代，脊椎动物出现",
        "milestone": "寒武纪大爆发",
    },
    # 古生代中期（4-3亿年前）：鱼类时代，登陆开始
    "paleozoic_middle": {
        "start_turn": 5000,
        "end_turn": 5200,  # 5000-5200回合（1亿年）
        "name": "古生代中期",
        "name_en": "Middle Paleozoic",
        "description": "鱼类时代，植物和动物开始登陆",
        "milestone": "生物登陆",
    },
    # 古生代晚期（3-2.5亿年前）：两栖类和早期爬行类
    "paleozoic_late": {
        "start_turn": 5200,
        "end_turn": 5300,  # 5200-5300回合（0.5亿年）
        "name": "古生代晚期",
        "name_en": "Late Paleozoic",
        "description": "石炭纪森林，两栖类繁盛，早期爬行类出现",
        "milestone": "羊膜卵演化",
    },
    # 中生代（2.5-0.66亿年前）：恐龙时代
    "mesozoic": {
        "start_turn": 5300,
        "end_turn": 5532,  # 5300-5532回合（1.84亿年）
        "name": "中生代",
        "name_en": "Mesozoic",
        "description": "恐龙时代，哺乳类和鸟类出现",
        "milestone": "恐龙统治",
    },
    # 新生代（0.66亿年前-现在）：哺乳类时代
    "cenozoic": {
        "start_turn": 5532,
        "end_turn": 5600,  # 5532-5600回合（0.66亿年）
        "name": "新生代",
        "name_en": "Cenozoic",
        "description": "哺乳类辐射演化，智慧生命出现",
        "milestone": "哺乳类时代",
    },
    # 超越新生代（5600回合后）：未来演化
    "future": {
        "start_turn": 5600,
        "end_turn": 99999,  # 无上限
        "name": "未来纪",
        "name_en": "Future",
        "description": "超越已知历史，生物继续演化",
        "milestone": "无限可能",
    },
}


def get_current_era(turn_index: int) -> dict:
    """根据回合数获取当前地质时代信息
    
    Args:
        turn_index: 当前回合数
        
    Returns:
        时代配置字典
    """
    for era_id, era in GEOLOGICAL_ERAS.items():
        if era["start_turn"] <= turn_index < era["end_turn"]:
            return {"id": era_id, **era}
    # 超出定义范围，返回未来纪
    return {"id": "future", **GEOLOGICAL_ERAS["future"]}


def get_era_progress(turn_index: int) -> float:
    """获取当前时代的进度（0.0-1.0）
    
    用于显示时代进度
    """
    era = get_current_era(turn_index)
    duration = era["end_turn"] - era["start_turn"]
    if duration <= 0 or duration > 10000:  # 未来纪没有固定结束
        return 0.0
    progress = (turn_index - era["start_turn"]) / duration
    return min(1.0, max(0.0, progress))


def calculate_era_limits(turn_index: int) -> dict:
    """根据回合数计算当前的属性上限（渐进式增长）
    
    核心公式：
    - 单属性上限 = 基础值 + (回合数 / 100) × 每100回合增长量
    - 总和上限 = 基础值 + (回合数 / 100) × 每100回合增长量
    
    Args:
        turn_index: 当前回合数
        
    Returns:
        {"single": 单属性上限, "total": 总和上限}
    """
    # 计算增长量
    growth_factor = turn_index / 100.0
    
    single_limit = ERA_BASE_LIMITS["single"] + growth_factor * ERA_GROWTH_PER_100_TURNS["single"]
    total_limit = ERA_BASE_LIMITS["total"] + growth_factor * ERA_GROWTH_PER_100_TURNS["total"]
    
    # 取整（向下取整，确保不会超标）
    return {
        "single": int(single_limit),
        "total": int(total_limit),
    }


class TraitConfig:
    """统一的trait配置管理"""
    
    STANDARD_TRAITS = {
        "耐寒性": 5.0,
        "耐热性": 5.0,
        "耐旱性": 5.0,
        "耐盐性": 5.0,
        "光照需求": 5.0,
        "运动能力": 5.0,
        "繁殖速度": 5.0,
        "社会性": 3.0,
        "攻击性": 3.0,
        "防御性": 3.0,
    }
    
    # 基础营养级上限（不考虑时代修正）
    TROPHIC_LIMITS_BASE = {
        1.0: {"base": 5, "specialized": 8, "total": 30},
        2.0: {"base": 7, "specialized": 10, "total": 50},
        3.0: {"base": 9, "specialized": 12, "total": 80},
        4.0: {"base": 12, "specialized": 14, "total": 105},
        5.0: {"base": 14, "specialized": 15, "total": 135},
    }
    
    # 兼容旧代码
    TROPHIC_LIMITS = TROPHIC_LIMITS_BASE
    
    # 特质到压力类型的映射
    # 格式: { 特质名: (压力类型, 触发方向) }
    # 触发方向: "cold"=负值触发, "hot"=正值触发, "high"=高值触发, "low"=低值触发
    # 
    # 【生物学依据】
    # 物种在特定环境压力下，会通过自然选择发展出相应的适应性特质
    # 
    TRAIT_PRESSURE_MAPPING = {
        # ========== 温度相关 ==========
        "耐寒性": ("temperature", "cold"),    # 低温环境选择耐寒个体
        "耐热性": ("temperature", "hot"),     # 高温环境选择耐热个体
        "耐极寒": ("temperature", "cold"),    # 极端低温适应
        "温度适应范围": ("temperature", "high"),  # 温度波动大时扩展适应范围
        
        # ========== 水分相关 ==========
        "耐旱性": ("drought", "high"),        # 干旱环境选择节水个体
        "耐湿性": ("humidity", "high"),       # 潮湿环境适应
        "耐涝性": ("flood", "high"),          # 洪水环境适应
        "保水能力": ("drought", "high"),      # 干旱压力下增强保水
        
        # ========== 盐度相关 ==========
        "耐盐性": ("salinity_change", "high"), # 盐度变化时的渗透调节
        "渗透调节": ("salinity_change", "high"),  # 渗透压调节能力
        "广盐性": ("salinity_change", "high"),    # 盐度适应范围广
        
        # ========== 压力/深度相关 ==========
        "耐高压": ("pressure", "high"),       # 深海高压适应
        "耐低压": ("altitude_change", "high"), # 高海拔低压适应
        
        # ========== 光照相关 ==========
        "光照需求": ("light_reduction", "high"),  # 光照减少时降低依赖
        "弱光适应": ("light_reduction", "high"),  # 弱光环境下的视觉/光合适应
        "暗视觉": ("light_reduction", "high"),    # 黑暗环境适应
        
        # ========== 酸碱相关 ==========
        "耐酸性": ("acidity", "high"),        # 酸性环境适应
        "耐碱性": ("alkalinity", "high"),     # 碱性环境适应
        "耐酸碱性": ("acidity", "high"),      # pH耐受范围广
        "钙化能力": ("carbonate_stress", "high"),  # 酸化条件下维持壳体
        
        # ========== 氧气相关 ==========
        "氧气需求": ("oxygen", "low"),        # 低氧时降低代谢需求
        "耐缺氧": ("oxygen", "low"),          # 缺氧环境适应
        "高效呼吸": ("oxygen", "low"),        # 低氧时提高氧气利用效率
        "厌氧代谢": ("oxygen", "low"),        # 无氧呼吸能力
        
        # ========== 毒素/化学相关 ==========
        "耐毒性": ("toxin_level", "high"),    # 毒素耐受
        "解毒能力": ("sulfide", "high"),      # 硫化物等毒素解毒
        "抗紫外线": ("uv_radiation", "high"), # UV辐射防护
        "黑色素沉着": ("uv_radiation", "high"),  # 紫外防护适应
        
        # ========== 资源/食物相关 ==========
        "资源利用效率": ("resource_decline", "high"),  # 资源匮乏时提高效率
        "杂食性": ("resource_decline", "high"),  # 食物短缺时扩展食谱
        "储能能力": ("resource_decline", "high"),  # 储存脂肪应对饥荒
        "饥饿耐受": ("starvation_risk", "high"),  # 长期饥饿耐受
        
        # ========== 竞争/社会相关 ==========
        "竞争能力": ("competition", "high"),  # 竞争压力下增强竞争力
        "领地性": ("niche_displacement", "high"),  # 入侵压力下保卫领地
        "社会性": ("competition", "high"),    # 竞争压力下可能增强合作
        
        # ========== 捕食/防御相关 ==========
        "攻击性": ("predator", "high"),       # 捕食压力下增加攻击性
        "防御性": ("predator", "high"),       # 捕食压力下增强防御
        "警觉性": ("predator", "high"),       # 捕食压力下提高警觉
        "伪装能力": ("predator", "high"),     # 躲避捕食者
        "毒腺": ("predator", "high"),         # 化学防御
        
        # ========== 运动/迁徙相关 ==========
        "运动能力": ("predator", "high"),     # 逃避捕食者
        "迁徙能力": ("habitat_fragmentation", "high"),  # 栖息地破碎时迁徙
        "挖掘能力": ("wildfire", "high"),     # 火灾时躲避地下
        
        # ========== 疾病/免疫相关 ==========
        "免疫力": ("disease", "high"),        # 疾病压力下增强免疫
        "抗病性": ("disease", "high"),        # 特定病原体抗性
        "自我隔离": ("disease", "high"),      # 避免传染的行为
        
        # ========== 繁殖相关 ==========
        "繁殖速度": ("mortality_spike", "high"),  # 高死亡率时加速繁殖（r-策略）
        "后代存活率": ("resource_decline", "high"),  # 资源匮乏时提高育幼投资
        "繁殖季节灵活性": ("seasonality", "high"),  # 季节变化时调整繁殖期
        
        # ========== 火灾适应 ==========
        "耐火性": ("wildfire", "high"),       # 火灾环境适应
        "火后萌发": ("wildfire", "high"),     # 火灾后的恢复能力
    }
    
    # 新增：按栖息地类型分组的特质优先级
    # 不同栖息地类型的物种面对同一压力时，优先发展不同特质
    HABITAT_TRAIT_PRIORITY = {
        "marine": ["耐盐性", "渗透调节", "耐高压", "钙化能力", "耐缺氧"],
        "deep_sea": ["耐高压", "暗视觉", "耐缺氧", "耐寒性", "储能能力"],
        "coastal": ["耐盐性", "耐涝性", "广盐性", "迁徙能力", "耐热性"],
        "terrestrial": ["耐旱性", "耐热性", "耐寒性", "运动能力", "竞争能力"],
        "freshwater": ["渗透调节", "耐缺氧", "耐涝性", "温度适应范围", "保水能力"],
        "aerial": ["运动能力", "迁徙能力", "耐寒性", "高效呼吸", "温度适应范围"],
        "amphibious": ["耐旱性", "耐湿性", "温度适应范围", "渗透调节", "防御性"],
    }
    
    # 压力类型描述（用于生成叙事）
    # 【优化】扩展以支持更多压力场景
    PRESSURE_DESCRIPTIONS = {
        # 气候相关
        "temperature": {"hot": "高温环境", "cold": "寒冷环境"},
        "drought": {"high": "干旱环境"},
        "humidity": {"high": "潮湿环境"},
        "flood": {"high": "洪水/涝害"},
        "storm_damage": {"high": "风暴破坏"},
        "seasonality": {"high": "季节性剧变"},
        
        # 地质相关
        "volcanic": {"high": "火山活动"},
        "tectonic": {"high": "地壳运动"},
        "sea_level": {"high": "海平面上升", "low": "海平面下降"},
        "altitude_change": {"high": "海拔剧变"},
        "habitat_fragmentation": {"high": "栖息地破碎化"},
        "erosion": {"high": "严重侵蚀"},
        
        # 海洋相关
        "salinity_change": {"high": "盐度变化"},
        "upwelling_change": {"high": "上升流变化"},
        "carbonate_stress": {"high": "碳酸盐胁迫"},
        
        # 化学/大气相关
        "acidity": {"high": "酸性环境"},
        "oxygen": {"low": "低氧环境", "high": "富氧环境"},
        "sulfide": {"high": "硫化物毒害"},
        "uv_radiation": {"high": "紫外辐射增强"},
        "toxin_level": {"high": "毒素污染"},
        
        # 生态相关
        "predator": {"high": "捕食压力"},
        "competition": {"high": "种间竞争"},
        "niche_displacement": {"high": "生态位被侵占"},
        "disease": {"high": "疾病流行"},
        "resource_decline": {"high": "资源匮乏"},
        "resource_boost": {"high": "资源丰富期"},
        "starvation_risk": {"high": "饥荒威胁"},
        
        # 火灾相关
        "wildfire": {"high": "野火肆虐"},
        "wildfire_risk": {"high": "火灾风险"},
        
        # 其他
        "light_reduction": {"high": "光照不足"},
        "mortality_spike": {"high": "死亡率骤增"},
        "habitat_loss": {"high": "栖息地丧失"},
    }
    
    TRAIT_DESCRIPTIONS = {
        # 温度相关
        "耐寒性": "抵抗低温能力，如抗冻蛋白、厚毛皮",
        "耐热性": "抵抗高温能力，如高效散热、热休克蛋白",
        "耐极寒": "极端低温环境适应，如南极鱼类的抗冻血液",
        "温度适应范围": "对温度变化的耐受范围",
        
        # 水分相关
        "耐旱性": "抵抗干旱能力，如骆驼的储水机制",
        "耐湿性": "潮湿环境适应能力",
        "耐涝性": "洪水/淹没环境的耐受力",
        "保水能力": "减少水分流失的能力",
        
        # 盐度相关
        "耐盐性": "抵抗盐度变化能力，如渗透压调节",
        "渗透调节": "体液渗透压的调节能力",
        "广盐性": "适应多种盐度环境的能力",
        
        # 压力/深度相关
        "耐高压": "深海高压环境适应",
        "耐低压": "高海拔低压环境适应",
        
        # 光照相关
        "光照需求": "对光照的依赖程度",
        "弱光适应": "在弱光条件下生存的能力",
        "暗视觉": "黑暗环境中的视觉能力",
        
        # 酸碱相关
        "耐酸性": "酸性环境耐受能力",
        "耐碱性": "碱性环境耐受能力",
        "耐酸碱性": "酸碱环境综合耐受能力",
        "钙化能力": "在酸化条件下维持钙质壳体的能力",
        
        # 氧气相关
        "氧气需求": "对氧气的依赖程度",
        "耐缺氧": "低氧环境的耐受能力",
        "高效呼吸": "氧气利用效率",
        "厌氧代谢": "无氧呼吸的能力",
        
        # 毒素/化学相关
        "耐毒性": "对环境毒素的耐受能力",
        "解毒能力": "代谢分解毒素的能力",
        "抗紫外线": "抵抗紫外辐射的能力",
        "黑色素沉着": "通过色素保护免受UV伤害",
        
        # 资源相关
        "资源利用效率": "对食物资源的利用效率",
        "杂食性": "食物来源的多样性",
        "储能能力": "储存能量（如脂肪）的能力",
        "饥饿耐受": "长期饥饿状态的耐受力",
        
        # 运动相关
        "运动能力": "移动和游动能力",
        "迁徙能力": "长距离迁移的能力",
        "挖掘能力": "挖洞穴居的能力",
        
        # 社会/竞争相关
        "社会性": "群居和社会互动倾向",
        "攻击性": "主动攻击倾向",
        "防御性": "防御和逃避能力",
        "警觉性": "对威胁的警觉程度",
        "竞争能力": "资源竞争的综合能力",
        "领地性": "保卫领地的倾向和能力",
        "伪装能力": "隐蔽自身的能力",
        "毒腺": "化学防御能力",
        
        # 繁殖相关
        "繁殖速度": "繁殖效率和速度",
        "后代存活率": "后代的生存概率",
        "繁殖季节灵活性": "繁殖时间的可调节性",
        
        # 疾病/免疫相关
        "免疫力": "抵抗病原体的能力",
        "抗病性": "对特定疾病的抵抗力",
        
        # 火灾适应
        "耐火性": "对火灾的耐受能力",
        "火后萌发": "火灾后恢复的能力",
    }
    
    @classmethod
    def get_default_traits(cls) -> dict[str, float]:
        """获取默认trait集合"""
        return dict(cls.STANDARD_TRAITS)
    
    @classmethod
    def validate_trait(cls, trait_name: str, value: float) -> bool:
        """验证trait值是否合法"""
        if not isinstance(value, (int, float)):
            return False
        if value < 0.0 or value > 15.0:
            return False
        return True
    
    @classmethod
    def clamp_trait(cls, value: float) -> float:
        """限制trait值到有效范围"""
        return max(0.0, min(15.0, float(value)))
    
    @classmethod
    def get_pressure_mapping(cls, trait_name: str) -> tuple[str, str] | None:
        """获取trait对应的压力类型"""
        return cls.TRAIT_PRESSURE_MAPPING.get(trait_name)
    
    @classmethod
    def get_trait_description(cls, trait_name: str) -> str:
        """获取trait描述"""
        return cls.TRAIT_DESCRIPTIONS.get(trait_name, "未知特质")
    
    @classmethod
    def merge_traits(cls, base_traits: dict[str, float], new_traits: dict[str, float]) -> dict[str, float]:
        """合并trait字典，确保基础trait存在"""
        merged = cls.get_default_traits()
        merged.update(base_traits)
        merged.update(new_traits)
        
        for trait_name in merged:
            merged[trait_name] = cls.clamp_trait(merged[trait_name])
        
        return merged
    
    @classmethod
    def inherit_traits(cls, parent_traits: dict[str, float], variation: float = 0.1) -> dict[str, float]:
        """从父代继承trait，带小幅度变异
        
        Args:
            parent_traits: 父代traits
            variation: 变异幅度 (0.1 = ±10%)
        """
        import random
        
        inherited = {}
        for trait_name, value in parent_traits.items():
            delta = random.uniform(-variation, variation) * value
            inherited[trait_name] = cls.clamp_trait(value + delta)
        
        return inherited
    
    @classmethod
    def get_trophic_limits(cls, trophic_level: float, turn_index: int = None) -> dict:
        """获取属性上限（营养级 + 时代双重增长）
        
        计算逻辑：
        1. 时代上限 = 基础值 + 回合数带来的增长（所有物种共享）
        2. 营养级加成 = 高营养级获得额外加成（捕食者更强）
        3. 最终上限 = 时代上限 + 营养级加成
        
        Args:
            trophic_level: 营养级（1.0-5.0+）
            turn_index: 当前回合数（如果提供，会应用时代增长）
            
        Returns:
            {"base": 基础上限, "specialized": 特化上限, "total": 总和上限, 
             "era_name": 时代名称, "era_progress": 时代进度}
        """
        # 1. 计算时代基础上限
        if turn_index is None:
            turn_index = 0
        
        era_limits = calculate_era_limits(turn_index)
        era = get_current_era(turn_index)
        era_progress = get_era_progress(turn_index)
        
        # 2. 计算营养级加成
        # 高营养级的捕食者可以比同时代的低营养级生物更强
        # 每提升1个营养级，单属性+1，总和+8
        trophic_bonus_single = int((trophic_level - 1.0) * 1.5)
        trophic_bonus_total = int((trophic_level - 1.0) * 10)
        
        # 3. 计算最终上限
        final_single = era_limits["single"] + trophic_bonus_single
        final_total = era_limits["total"] + trophic_bonus_total
        
        # base 是普通属性的建议上限（specialized 的 60%）
        final_base = int(final_single * 0.6)
        
        adjusted_limits = {
            "base": max(3, final_base),
            "specialized": max(5, final_single),
            "total": max(20, final_total),
            "era_name": era["name"],
            "era_id": era["id"],
            "era_progress": era_progress,
            "era_description": era["description"],
            # 额外信息
            "era_single_base": era_limits["single"],
            "era_total_base": era_limits["total"],
            "trophic_bonus_single": trophic_bonus_single,
            "trophic_bonus_total": trophic_bonus_total,
        }
        
        return adjusted_limits
    
    @classmethod
    def validate_traits_with_trophic(
        cls,
        traits: dict[str, float],
        trophic_level: float,
        turn_index: int = None
    ) -> tuple[bool, str]:
        """验证traits是否符合营养级和时代限制
        
        Args:
            traits: 待验证的traits字典
            trophic_level: 营养级
            turn_index: 当前回合数（可选，用于时代修正）
            
        Returns:
            (是否通过, 错误信息)
        """
        limits = cls.get_trophic_limits(trophic_level, turn_index)
        
        total = sum(traits.values())
        if total > limits["total"]:
            era_info = f"（{limits.get('era_name', '未知')}时代）" if turn_index else ""
            return False, f"属性总和{total:.1f}超过{era_info}上限{limits['total']}"
        
        above_specialized = [(k, v) for k, v in traits.items() if v > limits["specialized"]]
        if above_specialized:
            return False, f"属性{above_specialized[0][0]}={above_specialized[0][1]:.1f}超过特化上限{limits['specialized']}"
        
        above_base_count = sum(1 for v in traits.values() if v > limits["base"])
        if above_base_count > 2:
            return False, f"{above_base_count}个属性超过基础上限{limits['base']}，最多允许2个特化"
        
        return True, ""
    
    @classmethod
    def clamp_traits_to_trophic(
        cls,
        traits: dict[str, float],
        trophic_level: float,
        turn_index: int = None
    ) -> dict[str, float]:
        """将traits限制到营养级和时代允许的范围内
        
        Args:
            traits: 原始traits
            trophic_level: 营养级
            turn_index: 当前回合数（可选，用于时代修正）
            
        Returns:
            调整后的traits
        """
        limits = cls.get_trophic_limits(trophic_level, turn_index)
        adjusted = {}
        
        for trait_name, value in traits.items():
            clamped = min(value, limits["specialized"])
            adjusted[trait_name] = max(0.0, clamped)
        
        total = sum(adjusted.values())
        if total > limits["total"]:
            scale_factor = limits["total"] / total
            for trait_name in adjusted:
                adjusted[trait_name] = round(adjusted[trait_name] * scale_factor, 2)
        
        return adjusted
    
    @classmethod
    def get_era_limits_summary(cls, turn_index: int, trophic_level: float = 2.0) -> str:
        """获取时代上限的文字摘要（用于prompt）
        
        Args:
            turn_index: 当前回合数
            trophic_level: 营养级（默认2.0作为参考）
            
        Returns:
            格式化的时代上限说明
        """
        limits = cls.get_trophic_limits(trophic_level, turn_index)
        era = get_current_era(turn_index)
        progress = get_era_progress(turn_index)
        
        # 计算游戏内时间
        years_passed = turn_index * 500_000
        years_ago = 2_800_000_000 - years_passed
        
        if years_ago >= 1_000_000_000:
            time_str = f"{years_ago / 1_000_000_000:.1f}亿年前"
        elif years_ago >= 10_000_000:
            time_str = f"{years_ago / 100_000_000:.1f}亿年前"
        elif years_ago >= 1_000_000:
            time_str = f"{years_ago / 10_000:.0f}万年前"
        elif years_ago > 0:
            time_str = f"{years_ago:.0f}年前"
        else:
            time_str = "现代"
        
        # 显示增长信息
        era_base = limits.get('era_single_base', limits['specialized'])
        trophic_bonus = limits.get('trophic_bonus_single', 0)
        
        return (
            f"【当前时代】{era['name']}（{time_str}，回合{turn_index}）\n"
            f"里程碑：{era.get('milestone', '未知')}\n"
            f"时代特征：{era['description']}\n"
            f"时代基础上限：单属性≤{era_base}，总和≤{limits.get('era_total_base', limits['total'])}\n"
            f"营养级T{trophic_level:.1f}加成：单属性+{trophic_bonus}，总和+{limits.get('trophic_bonus_total', 0)}\n"
            f"【最终上限】单属性≤{limits['specialized']}，总和≤{limits['total']}"
        )


class PlantTraitConfig:
    """植物特质配置（仅用于营养级 < 2.0 的生产者）
    
    【设计原则】
    - 植物不需要动物特质（运动能力、攻击性等）
    - 植物有专属特质（光合效率、根系发达度等）
    - 当检测到植物时，部分动物特质会被映射/替换
    """
    
    # 植物专属特质（默认值）
    PLANT_TRAITS = {
        # 光合与代谢
        "光合效率": 5.0,       # 光能转化效率
        "固碳能力": 5.0,       # CO2固定效率
        
        # 水分与养分
        "根系发达度": 0.0,     # 0=无根(水生), 10=发达根系(陆生)
        "保水能力": 3.0,       # 水分保持能力（登陆必需）
        "养分吸收": 5.0,       # 土壤养分利用效率
        
        # 结构与繁殖
        "多细胞程度": 1.0,     # 1=单细胞, 10=复杂组织分化
        "木质化程度": 0.0,     # 0=无, 10=完全木质化（成为树木必需>=7）
        "种子化程度": 0.0,     # 0=孢子繁殖, 10=完全种子繁殖
        "散布能力": 3.0,       # 孢子/种子传播范围
        
        # 防御与适应
        "化学防御": 3.0,       # 毒素、单宁等
        "物理防御": 3.0,       # 刺、硬壳等
    }
    
    # 动物特质到植物特质的映射
    # 当处理植物时，这些动物特质会被替换为对应的植物特质
    ANIMAL_TO_PLANT_MAPPING = {
        "运动能力": "光合效率",
        "攻击性": "化学防御",
        "社会性": "散布能力",
        "防御性": "物理防御",
    }
    
    # 植物到动物的反向映射
    PLANT_TO_ANIMAL_MAPPING = {v: k for k, v in ANIMAL_TO_PLANT_MAPPING.items()}
    
    # 共享特质（动植物通用）
    SHARED_TRAITS = [
        "耐寒性", "耐热性", "耐旱性", "耐盐性",
        "光照需求", "繁殖速度",
    ]
    
    # 植物演化阶段名称
    LIFE_FORM_STAGE_NAMES = {
        0: "原核光合生物",
        1: "单细胞真核藻类",
        2: "群体/丝状藻类",
        3: "苔藓类植物",
        4: "蕨类植物",
        5: "裸子植物",
        6: "被子植物",
    }
    
    # 生长形式
    GROWTH_FORMS = ["aquatic", "moss", "herb", "shrub", "tree"]
    
    # 生长形式与阶段的约束
    GROWTH_FORM_STAGE_CONSTRAINTS = {
        "aquatic": [0, 1, 2],           # 水生：阶段0-2
        "moss": [3],                     # 苔藓：阶段3
        "herb": [4, 5, 6],               # 草本：阶段4-6
        "shrub": [5, 6],                 # 灌木：阶段5-6
        "tree": [5, 6],                  # 乔木：阶段5-6（需木质化>=7）
    }
    
    # 【新增】植物特质到压力类型的映射
    # 格式: { 特质名: (压力类型, 触发方向) }
    # 用于渐进演化中植物特质的自动调整
    PLANT_TRAIT_PRESSURE_MAPPING = {
        # ========== 光合与代谢 ==========
        "光合效率": ("light_reduction", "high"),     # 弱光环境提升光合效率
        "固碳能力": ("co2_level", "high"),           # 高CO2环境提升固碳
        
        # ========== 水分与养分 ==========
        "根系发达度": ("drought", "high"),           # 干旱促进根系发展
        "保水能力": ("drought", "high"),             # 干旱提升保水能力
        "养分吸收": ("nutrient_poor", "high"),       # 贫瘠环境提升养分吸收
        
        # ========== 结构发育 ==========
        "多细胞程度": ("competition", "high"),       # 竞争促进复杂化
        "木质化程度": ("drought", "high"),           # 干旱促进木质化（更好的水分运输）
        "种子化程度": ("drought", "high"),           # 干旱促进种子化（脱水繁殖）
        "散布能力": ("habitat_fragmentation", "high"),  # 栖息地破碎促进散布
        
        # ========== 防御机制 ==========
        "化学防御": ("herbivory", "high"),           # 食草压力促进化学防御
        "物理防御": ("herbivory", "high"),           # 食草压力促进物理防御
    }
    
    # 【新增】植物特质的权衡关系（增加某特质时，哪些特质可能降低）
    PLANT_TRAIT_TRADEOFFS = {
        "光合效率": ["耐旱性", "繁殖速度"],         # 高效光合需要更多水分
        "根系发达度": ["散布能力", "繁殖速度"],     # 发达根系限制移动
        "木质化程度": ["繁殖速度", "光合效率"],     # 木质化消耗大量能量
        "化学防御": ["繁殖速度", "光合效率"],       # 毒素合成消耗能量
        "物理防御": ["繁殖速度", "散布能力"],       # 刺等结构消耗资源
        "种子化程度": ["繁殖速度"],                 # 种子发育周期长
        "保水能力": ["光合效率"],                   # 厚角质层阻碍气体交换
    }
    
    @classmethod
    def get_plant_pressure_mapping(cls, trait_name: str) -> tuple[str, str] | None:
        """获取植物特质对应的压力类型
        
        Args:
            trait_name: 特质名称
            
        Returns:
            (压力类型, 触发方向) 或 None
        """
        return cls.PLANT_TRAIT_PRESSURE_MAPPING.get(trait_name)
    
    @classmethod
    def get_trait_tradeoffs(cls, trait_name: str) -> list[str]:
        """获取特质的权衡关系（增加时哪些可能降低）
        
        Args:
            trait_name: 特质名称
            
        Returns:
            可能降低的特质列表
        """
        return cls.PLANT_TRAIT_TRADEOFFS.get(trait_name, [])
    
    @classmethod
    def get_default_plant_traits(cls) -> dict[str, float]:
        """获取默认植物特质集合"""
        # 合并共享特质和植物专属特质
        traits = {}
        for trait in cls.SHARED_TRAITS:
            traits[trait] = TraitConfig.STANDARD_TRAITS.get(trait, 5.0)
        traits.update(cls.PLANT_TRAITS)
        return traits
    
    @classmethod
    def convert_animal_to_plant_traits(cls, animal_traits: dict[str, float]) -> dict[str, float]:
        """将动物特质转换为植物特质
        
        Args:
            animal_traits: 动物特质字典
            
        Returns:
            转换后的植物特质字典
        """
        plant_traits = {}
        
        for trait_name, value in animal_traits.items():
            # 检查是否需要映射
            if trait_name in cls.ANIMAL_TO_PLANT_MAPPING:
                mapped_name = cls.ANIMAL_TO_PLANT_MAPPING[trait_name]
                plant_traits[mapped_name] = value
            elif trait_name in cls.SHARED_TRAITS:
                plant_traits[trait_name] = value
            # 忽略其他动物专属特质
        
        # 确保所有植物特质都有值
        for trait_name, default_value in cls.PLANT_TRAITS.items():
            if trait_name not in plant_traits:
                plant_traits[trait_name] = default_value
        
        return plant_traits
    
    @classmethod
    def convert_plant_to_animal_traits(cls, plant_traits: dict[str, float]) -> dict[str, float]:
        """将植物特质转换回动物特质格式（用于兼容性）
        
        Args:
            plant_traits: 植物特质字典
            
        Returns:
            兼容动物特质格式的字典
        """
        animal_traits = {}
        
        for trait_name, value in plant_traits.items():
            if trait_name in cls.PLANT_TO_ANIMAL_MAPPING:
                mapped_name = cls.PLANT_TO_ANIMAL_MAPPING[trait_name]
                animal_traits[mapped_name] = value
            elif trait_name in cls.SHARED_TRAITS:
                animal_traits[trait_name] = value
            else:
                # 保留植物专属特质
                animal_traits[trait_name] = value
        
        return animal_traits
    
    @classmethod
    def is_plant(cls, species) -> bool:
        """判断物种是否为植物（生产者）
        
        Args:
            species: 物种对象
            
        Returns:
            是否为植物
        """
        # 营养级 < 2.0 是生产者
        if hasattr(species, 'trophic_level') and species.trophic_level < 2.0:
            return True
        
        # 有光合作用能力
        caps = getattr(species, 'capabilities', []) or []
        if '光合作用' in caps or 'photosynthesis' in caps:
            return True
        
        # 食性为自养
        diet = getattr(species, 'diet_type', '')
        if diet == 'autotroph':
            return True
        
        return False
    
    @classmethod
    def validate_growth_form(cls, growth_form: str, life_form_stage: int) -> bool:
        """验证生长形式与演化阶段是否匹配
        
        Args:
            growth_form: 生长形式
            life_form_stage: 演化阶段
            
        Returns:
            是否匹配
        """
        if growth_form not in cls.GROWTH_FORM_STAGE_CONSTRAINTS:
            return False
        
        allowed_stages = cls.GROWTH_FORM_STAGE_CONSTRAINTS[growth_form]
        return life_form_stage in allowed_stages
    
    @classmethod
    def get_valid_growth_forms(cls, life_form_stage: int) -> list[str]:
        """获取指定阶段允许的生长形式
        
        Args:
            life_form_stage: 演化阶段
            
        Returns:
            允许的生长形式列表
        """
        valid_forms = []
        for form, stages in cls.GROWTH_FORM_STAGE_CONSTRAINTS.items():
            if life_form_stage in stages:
                valid_forms.append(form)
        return valid_forms
    
    @classmethod
    def get_stage_name(cls, life_form_stage: int) -> str:
        """获取阶段名称"""
        return cls.LIFE_FORM_STAGE_NAMES.get(life_form_stage, "未知阶段")