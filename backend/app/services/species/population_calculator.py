from __future__ import annotations

import math


class PopulationCalculator:
    """根据生物体型计算合理的种群数量范围。
    
    采用生物量单位（kg）而非个体数
    - 1个规模单位 = 1kg 生物量
    - 地块约8万平方公里
    - 基于体型的幂律关系：体型越大，总生物量越小
    
    基于生态学原理：
    - 体型越大，代谢需求越高，环境承载力越小
    - 遵循幂律关系：种群密度 ∝ 体重^(-0.75)
    
    【平衡修复】
    - 降低微生物的初始种群，避免第一回合就爆炸
    - 使用更保守的上限，保持游戏平衡
    """
    
    @staticmethod
    def calculate_reasonable_population(
        body_length_cm: float,
        body_weight_g: float | None = None,
        habitat_quality: float = 1.0,
    ) -> tuple[int, int]:
        """计算合理的种群生物量范围（单位：kg）。
        
        Args:
            body_length_cm: 体长（厘米）
            body_weight_g: 单个个体体重（克），如果为None则根据体长估算
            habitat_quality: 栖息地质量系数（0.5-2.0，默认1.0）
            
        Returns:
            (最小合理生物量kg, 最大合理生物量kg)
        """
        # 如果没有体重，根据体长估算（假设大致球形或圆柱形）
        if body_weight_g is None or body_weight_g <= 0:
            # 粗略估算：体重 ≈ 体长^3（立方关系）
            body_weight_g = max(0.000001, (body_length_cm ** 3) * 0.1)
        
        body_weight_kg = body_weight_g / 1000
        
        # 【平衡修复】使用更温和的幂律关系
        # 原来：scale_factor = (body_weight_kg)^(-0.75) 导致微生物数值爆炸
        # 现在：使用对数缩放，避免极端值
        # 
        # 基准：1kg个体，基准生物量约 10^7 kg (1000万)
        # 微生物（0.001g = 1e-6 kg）：约 10^8 kg (1亿)
        # 大型动物（100kg）：约 10^5 kg (10万)
        
        import math
        
        # 使用对数缩放替代幂律，更平滑
        # log10(1e-6) = -6, log10(1) = 0, log10(100) = 2
        log_weight = math.log10(max(1e-9, body_weight_kg))  # -9 到 3 范围
        
        # 缩放系数：体重越小，系数越大，但增长更平缓
        # log_weight = -6 -> scale = 4
        # log_weight = 0 -> scale = 1
        # log_weight = 2 -> scale = 0.5
        scale_factor = max(0.1, 1.0 - log_weight * 0.5)
        scale_factor = min(scale_factor, 10.0)  # 上限10倍
        
        # 基准生物量（更保守的值）
        base_biomass = 1e7  # 1000万 kg
        
        # 计算目标生物量
        target_biomass = base_biomass * scale_factor
        
        # 设置合理范围
        min_biomass_kg = int(target_biomass * 0.3)
        max_biomass_kg = int(target_biomass * 3.0)
        
        # 应用栖息地质量系数
        habitat_quality = max(0.5, min(2.0, habitat_quality))
        min_biomass_kg = int(min_biomass_kg * habitat_quality)
        max_biomass_kg = int(max_biomass_kg * habitat_quality)
        
        # 【平衡修复】更保守的边界
        # 最小：1,000 kg（保证物种有一定规模）
        # 最大：10^9 kg = 10亿 kg（单物种上限，避免数值爆炸）
        min_biomass_kg = max(1_000, min(min_biomass_kg, int(1e9)))
        max_biomass_kg = max(10_000, min(max_biomass_kg, int(1e9)))
        
        return (min_biomass_kg, max_biomass_kg)
    
    @staticmethod
    def get_initial_population(
        body_length_cm: float,
        body_weight_g: float | None = None,
        habitat_quality: float = 1.0,
    ) -> int:
        """获取推荐的初始种群数量。
        
        【平衡修改】从小族群开始，让演化过程更有意义
        - 微生物（<1mm）：约 10万
        - 小型生物（1mm-10cm）：约 1-5万
        - 中型生物（10cm-1m）：约 5000-1万
        - 大型生物（>1m）：约 1000-5000
        """
        import math
        
        # 基于体长确定初始规模
        # 使用对数缩放：体长越大，初始种群越小
        log_length = math.log10(max(0.001, body_length_cm))  # -3 到 3 范围
        
        # 初始种群基数
        # log_length = -3 (0.001cm = 10μm，微生物) -> 100,000
        # log_length = 0 (1cm) -> 10,000
        # log_length = 2 (100cm = 1m) -> 1,000
        base_initial = 10_000  # 1万作为基准
        
        # 缩放因子：体长每增加10倍，初始种群减少到1/3
        scale = 3.0 ** (-log_length)
        initial_pop = int(base_initial * scale)
        
        # 应用栖息地质量
        habitat_quality = max(0.5, min(2.0, habitat_quality))
        initial_pop = int(initial_pop * habitat_quality)
        
        # 边界限制
        # 最小：1,000（保证物种能够存活）
        # 最大：500,000（不能太大，否则第一回合就到上限）
        initial_pop = max(1_000, min(initial_pop, 500_000))
        
        return initial_pop
    
    @staticmethod
    def validate_population(
        population: int,
        body_length_cm: float,
        body_weight_g: float | None = None,
    ) -> tuple[bool, str]:
        """验证种群数量是否合理。
        
        Returns:
            (是否合理, 提示信息)
        """
        min_pop, max_pop = PopulationCalculator.calculate_reasonable_population(
            body_length_cm, body_weight_g
        )
        
        if population < min_pop * 0.1:
            return (False, f"种群数量过低（建议范围：{min_pop}-{max_pop}）")
        elif population > max_pop * 10:
            return (False, f"种群数量过高（建议范围：{min_pop}-{max_pop}）")
        elif population < min_pop:
            return (True, f"种群数量偏低但可接受（建议范围：{min_pop}-{max_pop}）")
        elif population > max_pop:
            return (True, f"种群数量偏高但可接受（建议范围：{min_pop}-{max_pop}）")
        else:
            return (True, "种群数量合理")

