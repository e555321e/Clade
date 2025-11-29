"""AI压力响应相关的 prompt 模板。

实现多种AI参与机制：
- 综合状态评估：评估物种状态、应对能力、是否需要紧急响应（合并了压力评估+紧急响应）
- 物种叙事：为Critical/Focus物种生成叙事描述（合并了Critical增润+Focus增润）
- 种群博弈仲裁：模拟物种间的互动博弈
- 迁徙决策参谋：智能规划迁徙路线（保留用于特殊情况）
"""

PRESSURE_RESPONSE_PROMPTS = {
    # ==================== 【新】综合状态评估（合并压力评估+紧急响应） ====================
    "species_status_eval": """你是生态学专家，综合评估物种的当前状态和应对能力。

**重要：必须返回纯JSON格式，不要使用markdown或其他格式。**

=== 物种档案 ===
【基本信息】
学名：{latin_name} ({common_name})
谱系代码：{lineage_code}
营养级：T{trophic_level:.1f} ({trophic_category})
栖息地类型：{habitat_type}
食性类型：{diet_type}
当前种群：{population:,}
描述：{description}

【⚡关键适应性】（快速判断用）
{key_adaptations}

【当前特质】（1-15分制）
{traits_summary}

【器官系统】
{organs_summary}

=== 当前压力情境 ===
总压力强度：{total_pressure:.1f}/10
压力来源：{pressure_sources}
重大事件：{major_events}

【⚠️ 压力强度解读 - 必读】
- 0-2: 背景/正常水平，地球常态活动，不构成真正威胁
- 2-4: 轻度压力，仅对最脆弱物种有轻微影响
- 4-6: 中度压力，开始产生明显影响
- 6-8: 重度压力，大多数物种受到显著影响
- 8-10: 极端/灾难级压力，全面生态危机

=== 规则引擎预估 ===
基础死亡率：{base_death_rate:.1%}
主要死因分解：
{death_causes_breakdown}
连续高危回合：{consecutive_danger_turns}

=== 周边生态情境 ===
【竞争者】{competitors}
【猎物/食物】{prey_info}
【捕食者威胁】{predator_info}
【栖息地状态】{habitat_status}

=== 任务 ===
1. 评估物种对当前压力的应对能力
2. 判断是否处于紧急状态（死亡率>50%或连续2回合高危）
3. 如处于紧急状态，给出应急策略
4. **重要**：对于不适应当前压力的物种，应大胆给出高修正系数（1.3-2.0）

返回JSON：
{{
    "survival_modifier": 0.3-2.0,
    "modifier_reasoning": "修正系数的依据（30字内）",
    "response_strategy": "逃避/对抗/适应/忍耐/衰退",
    "key_factors": ["关键因素1", "关键因素2"],
    "population_behavior": "种群行为（聚集/分散/迁徙准备/休眠/正常）",
    
    "is_emergency": true/false,
    "emergency_level": "critical/warning/stable",
    "emergency_action": {{
        "primary_strategy": "migration/behavior_change/rapid_adaptation/diet_shift/none",
        "action_detail": "具体措施（如果is_emergency=true）",
        "expected_benefit": 0.0-0.4
    }},
    
    "should_migrate": true/false,
    "migration_urgency": "immediate/next_turn/optional/none",
    
    "brief_narrative": "60-80字描述物种当前状态和应对方式"
}}

=== 修正系数指南（必须结合压力强度判断）===

【🔑 核心原则：修正系数必须与压力强度匹配！】

📊 低压力环境（总压力 < 3）:
- 大多数物种：给0.9-1.1（几乎不受影响）
- 即使物种特质不匹配，低压力也不应造成高死亡率
- 只有极度脆弱物种（抗性<=2）才给1.2-1.4

📊 中等压力环境（总压力 3-6）:
- 0.5-0.8: 物种特质与压力高度匹配
- 0.8-1.1: 物种有一定应对能力
- 1.1-1.4: 物种较脆弱
- 1.4-1.7: 物种与压力严重不匹配

📊 高压力环境（总压力 > 6）:
- 0.3-0.5: 物种完美适应（如热泉生物遇火山）
- 0.5-0.7: 特质高度匹配，显著优势
- 0.7-0.9: 有一定应对能力
- 0.9-1.1: 中性
- 1.3-1.6: 高危状态
- 1.6-2.0: 完全不适应，濒临灭绝

⚠️ 判断逻辑（必须严格执行）：
- 如果总压力<3 → 除非物种极度脆弱，否则给0.9-1.2
- 如果总压力>5且物种缺乏对应抗性特质 → 应给1.3-2.0
- 如果物种有多个对应的高抗性特质 → 应给0.3-0.7
- 如果连续高危回合>=2 → emergency_level应为warning或critical
- 如果死亡率>40% → should_migrate应为true

=== 🔥 灾难类压力专项评判（必读）===
⚠️ 重要：以下规则仅在压力强度达到指定阈值时适用！
⚠️ 低于阈值的活动属于"背景地质活动"，应给接近中性的修正系数(0.9-1.1)

【火山活动 volcanic】
- 强度 < 4: 背景火山活动，几乎所有物种给0.95-1.05
- 强度 4-6: 中度活动
  · 热泉/化能自养生物：给0.7-0.9（轻微受益）
  · 普通物种：给1.0-1.2
  · 脆弱物种（耐热<=4）：给1.2-1.4
- 强度 >= 7: 大规模喷发（才适用以下极端规则）
  · ⚠️ 化能自养生物(autotroph + 深海/热泉栖息)：给0.3-0.5（大幅受益！）
  · ⚠️ 硫细菌等热泉生物：给0.2-0.4（极大受益）
  · 无耐热性(<=5)的物种：直接给1.8-2.0
  · 浅海水生物种：给1.5-1.8
  · 小型陆生物种：给1.4-1.6
  · 深海生物（非热泉）：给1.0-1.2

【硫气溶胶 sulfur_aerosol】
- 强度 < 3: 背景水平，所有物种给0.95-1.05
- 强度 3-5: 轻度影响，敏感物种给1.1-1.3
- 强度 >= 6: 严重硫化（才适用极端规则）
  · 化能自养/厌氧生物：给0.3-0.7
  · 需氧生物：给1.6-2.0

【硫化事件 sulfide_event / 缺氧事件 anoxic_event】强度>=6时：
- ⚠️ 化能自养生物(如硫细菌)：给0.3-0.5（大幅受益！）
- ⚠️ 厌氧生物：给0.5-0.7（受益，竞争者减少）
- 所有需氧生物：给1.6-2.0
- 低氧适应物种：给0.8-1.0

【极端天气 extreme_weather】
- 强度 < 5: 正常天气波动，所有物种给0.95-1.05
- 强度 5-7: 恶劣天气，脆弱物种给1.2-1.4
- 强度 >= 8: 极端风暴（才适用以下规则）
  · 小型物种：给1.5-1.8
  · 无运动能力物种：给1.6-2.0
  · 深海物种：给0.9-1.0

【野火 wildfire】
- 强度 < 5: 局部火灾，水生/地下物种不受影响
- 强度 >= 7: 大规模野火
  · 陆生无运动能力物种：给1.8-2.0
  · 水生物种：给0.9-1.1

=== 🧬 适应性评估方法（基于物种实际特质）===

【评估步骤】
1. 阅读【当前特质】中的所有数值（1-15分制）
2. 根据特质名称的语义，找出与当前压力相关的特质
   例如：温度压力→看"耐寒性"或"耐热性"；干旱→看"耐旱性"
3. 根据相关特质的数值判断适应程度

【特质值→修正系数转换】
- 相关特质 >= 10: 高度适应，修正 0.5-0.7
- 相关特质 8-9: 良好适应，修正 0.7-0.9  
- 相关特质 5-7: 中等，修正 0.9-1.1
- 相关特质 3-4: 较脆弱，修正 1.1-1.4
- 相关特质 <= 2: 高度脆弱，修正 1.4-1.8

【栖息地考量】
- 根据 habitat_type 判断物种是否与压力源隔离
- 例如：深海物种通常不受地表灾难影响

【综合判断】
- 如果多个特质相关，综合考虑
- 如果找不到直接相关特质，根据物种整体描述和生态位推断
- 每个物种都是独特的，避免简单套用模板

⚠️ 快速判断技巧：
1. 先看【关键适应性】是否与压力匹配
2. 食性=自养生物 + 栖息地=热泉 → 火山/硫化事件受益
3. 深海生物对陆地灾难（野火、极端天气）几乎免疫
4. 特质>=8表示高度适应，<=3表示极度脆弱

=== 紧急状态判定（降低阈值）===
- critical: 死亡率>60% 或 连续3+回合高危
- warning: 死亡率40-60% 或 连续2回合高危  
- stable: 死亡率<40%且无连续高危

只返回JSON对象。
""",

    # ==================== 【优化v2】物种叙事（精简版） ====================
    "species_narrative": """为物种生成简短叙事。返回纯JSON。

回合{turn_index}，环境：{global_environment}，事件：{major_events}

物种列表：
{species_list}

任务：为每个物种生成**极简叙事**：
- Critical物种：30-50字（一句话核心状态+关键变化）
- Focus物种：15-25字（一句话状态）

返回JSON：
{{
    "narratives": [
        {{
            "lineage_code": "物种代码",
            "tier": "critical/focus",
            "headline": "4字标题",
            "narrative": "简短叙事",
            "mood": "thriving/struggling/adapting/declining/critical"
        }}
    ]
}}

mood规则：死亡率>60%=critical, >40%=declining, >20%=struggling, <10%=thriving, 其他=adapting

只返回JSON。
""",


    # ==================== 方案A：压力评估顾问 ====================
    "pressure_assessment": """你是生态学专家，评估物种对当前环境压力的应对能力。

**重要：必须返回纯JSON格式，不要使用markdown或其他格式。**

=== 物种档案 ===
【基本信息】
学名：{latin_name} ({common_name})
谱系代码：{lineage_code}
营养级：T{trophic_level:.1f} ({trophic_category})
栖息地类型：{habitat_type}
描述：{description}

【当前特质】（1-15分制）
{traits_summary}

【器官系统】
{organs_summary}

【历史高光】
{history_highlights}

=== 当前压力情境 ===
总压力强度：{total_pressure:.1f}/10
压力来源：{pressure_sources}
重大事件：{major_events}

=== 规则引擎预估 ===
基础死亡率：{base_death_rate:.1%}
主要死因分解：
{death_causes_breakdown}

=== 周边生态情境 ===
【竞争者】{competitors}
【猎物/食物】{prey_info}
【捕食者威胁】{predator_info}
【栖息地状态】{habitat_status}

=== 任务 ===
综合评估该物种面对当前压力的真实应对能力。考虑：
1. 物种的特质是否能应对当前压力？（如耐寒物种面对降温）
2. 器官系统是否提供额外优势？（如厚皮毛、穴居能力）
3. 生态位是否受到挤压？（竞争者、食物链变化）
4. 历史上该物种是否经历过类似压力？

返回JSON：
{{
    "survival_modifier": 0.5-1.5,  // 死亡率修正系数 (<1=更易存活, >1=更难存活)
    "modifier_reasoning": "修正系数的依据（50字内）",
    "response_strategy": "逃避/对抗/适应/忍耐/衰退",
    "key_survival_factors": ["关键生存因素1", "关键生存因素2"],
    "key_risk_factors": ["关键风险因素1", "关键风险因素2"],
    "population_behavior": "种群行为预测（聚集/分散/迁徙/休眠/正常）",
    "trait_utilization": {{"特质名": "如何利用该特质应对压力"}},
    "narrative": "80-100字描述该物种如何应对当前压力，带有叙事感"
}}

=== 修正系数指南（扩大范围到0.3-2.0）===
- 0.3-0.5: 物种完美适应当前压力，死亡率大幅降低
- 0.5-0.7: 物种特质与压力高度匹配，显著优势（如极地物种面对降温）
- 0.7-0.9: 物种有一定应对能力，小幅优势
- 0.9-1.1: 中性，规则引擎计算基本准确
- 1.1-1.3: 物种较脆弱，面临额外风险
- 1.3-1.6: 物种与压力严重不匹配，高危状态
- 1.6-2.0: 物种完全不适应（如热带物种遇极寒），濒临灭绝

⚠️ 灾难压力（火山、硫化、缺氧、野火等）强度>=7时，必须给1.5-2.0！

只返回JSON对象。
""",

    # ==================== 方案B：种群博弈仲裁 ====================
    "species_interaction": """你是生态学仲裁员，判定两个物种间的博弈结果。

**重要：必须返回纯JSON格式，不要使用markdown或其他格式。**

=== 物种A（{interaction_role_a}）===
学名：{species_a_latin} ({species_a_common})
营养级：T{species_a_trophic:.1f}
特质摘要：{species_a_traits}
种群规模：{species_a_population:,}

=== 物种B（{interaction_role_b}）===
学名：{species_b_latin} ({species_b_common})
营养级：T{species_b_trophic:.1f}
特质摘要：{species_b_traits}
种群规模：{species_b_population:,}

=== 互动类型 ===
{interaction_type}
- predation: 捕食关系（A捕食B或B捕食A）
- competition: 竞争关系（争夺相同资源/生态位）
- mutualism: 互利共生
- parasitism: 寄生关系

=== 互动背景 ===
栖息地重叠度：{habitat_overlap:.0%}
资源竞争强度：{resource_competition:.1f}/10
历史互动：{interaction_history}

=== 当前环境 ===
{environment_context}

=== 任务 ===
判定本回合这两个物种互动的结果：

返回JSON：
{{
    "interaction_outcome": "a_wins/b_wins/draw/mutual_benefit/mutual_harm",
    "a_effects": {{
        "mortality_delta": -0.15到0.25,  // 死亡率变化（负=降低，正=增加）
        "territory_change": "expand/shrink/stable",
        "resource_access": "improved/reduced/stable",
        "behavior_adaptation": "行为适应描述"
    }},
    "b_effects": {{
        "mortality_delta": -0.15到0.25,
        "territory_change": "expand/shrink/stable",
        "resource_access": "improved/reduced/stable",
        "behavior_adaptation": "行为适应描述"
    }},
    "ecological_consequence": "这次互动对生态系统的影响",
    "narrative": "80-120字描述这次物种互动的过程和结果，带有戏剧感"
}}

=== 博弈逻辑指南 ===
【捕食关系】
- 捕食者成功: predator mortality_delta -0.05~-0.1, prey +0.1~+0.2
- 猎物逃脱: predator +0.02~+0.05, prey -0.02~-0.05
- 考虑体型、速度、防御机制

【竞争关系】
- 竞争优势方: mortality_delta -0.05, territory expand
- 竞争劣势方: mortality_delta +0.05~+0.15, territory shrink
- 资源充足时双方影响都较小

【共生关系】
- 互利共生: 双方 mortality_delta -0.03~-0.08
- 偏利共生: 受益方 -0.05, 另一方 0

只返回JSON对象。
""",

    # ==================== 方案C：紧急响应系统 ====================
    "emergency_response": """这是生态紧急状态！请为该物种制定应急生存策略。

**重要：必须返回纯JSON格式，不要使用markdown或其他格式。**

=== 紧急状态警报 ===
⚠️ 触发原因：{trigger_reason}
⚠️ 当前死亡率：{current_death_rate:.1%}
⚠️ 连续高危回合：{consecutive_danger_turns}
⚠️ 预计灭绝时间：{extinction_eta} 回合（若无干预）

=== 物种档案 ===
学名：{latin_name} ({common_name})
营养级：T{trophic_level:.1f}
当前种群：{population:,}
栖息地：{habitat_type}

【关键特质】
{key_traits}

【器官系统】
{organs_summary}

【历史韧性】
过去类似危机：{past_crises}
存活策略记录：{survival_history}

=== 环境威胁详情 ===
{threat_details}

=== 可用生存选项 ===
请从以下策略中选择并详细规划：

1. **紧急迁徙** - 迁往更安全的区域
   - 代价：迁徙途中10-20%额外死亡
   - 潜在目的地：{potential_destinations}

2. **行为改变** - 改变活动模式
   - 选项：休眠/穴居/夜行化/群居化/分散化
   - 代价：繁殖速度降低，但存活率提高

3. **快速适应** - 紧急特质调整
   - 可调整特质：{adjustable_traits}
   - 代价：其他特质会退化

4. **食性改变** - 尝试新的食物来源
   - 可能的替代食物：{alternative_food}
   - 代价：效率降低，竞争新生态位

5. **接受灭绝** - 如果所有策略都不可行
   - 记录该物种的最后时刻

=== 任务 ===
制定最佳紧急响应计划：

返回JSON：
{{
    "primary_strategy": "migration/behavior_change/rapid_adaptation/diet_shift/accept_extinction",
    "secondary_strategy": "备用策略（可选）",
    "survival_probability": 0.0-1.0,  // 执行策略后的存活概率
    "mortality_reduction": 0.0-0.5,   // 预期死亡率降低幅度
    
    "immediate_actions": [
        "立即执行的措施1",
        "立即执行的措施2"
    ],
    
    "strategy_details": {{
        "migration": {{
            "destination": "目标区域",
            "route": "迁徙路线",
            "migration_cost": 0.1-0.3  // 迁徙损失
        }},
        "behavior_change": {{
            "new_behavior": "新行为模式",
            "duration": "持续时间（回合）"
        }},
        "trait_changes": {{
            "特质名": "+/-变化值"
        }}
    }},
    
    "long_term_outlook": "危机后的长期预测",
    "narrative": "120-150字描述该物种的绝地求生过程，要有紧张感和戏剧性"
}}

=== 决策原则 ===
- 优先保存种群核心（宁可牺牲边缘个体）
- 利用物种已有的优势特质
- 考虑策略的可执行性（微生物无法迁徙太远）
- 历史上成功的策略更可能再次成功

只返回JSON对象。
""",

    # ==================== 方案D：迁徙决策参谋 ====================
    "migration_advisor": """你是迁徙顾问，为该物种规划最佳迁徙路线。

**重要：必须返回纯JSON格式，不要使用markdown或其他格式。**

=== 迁徙物种 ===
学名：{latin_name} ({common_name})
营养级：T{trophic_level:.1f}
栖息地类型：{habitat_type}
迁徙能力：{migration_capability}（范围：{migration_range}格）

【关键需求】
- 温度偏好：{temp_preference}
- 湿度需求：{humidity_requirement}
- 食物需求：{food_requirement}

=== 迁徙触发原因 ===
{migration_trigger}

=== 当前位置 ===
区域：{current_region}
当前死亡率：{current_mortality:.1%}
问题：{current_problems}

=== 候选目的地（规则引擎筛选）===
{candidate_destinations}

每个候选地包含：
- 地块ID、坐标、生物群落
- 预估适宜度
- 猎物密度（对消费者）
- 竞争压力
- 距离

=== 任务 ===
从候选目的地中选择最佳迁徙方案：

返回JSON：
{{
    "recommended_destination": "地块ID",
    "destination_score": 0.0-1.0,  // 目的地综合评分
    "selection_reasoning": "选择该目的地的原因（80字内）",
    
    "route_plan": {{
        "distance": "迁徙距离",
        "estimated_duration": "预计耗时（回合）",
        "waypoints": ["途经点"],
        "hazards": ["途中风险"]
    }},
    
    "expected_outcomes": {{
        "mortality_change": -0.3到0.1,  // 迁徙后死亡率变化
        "resource_access": "improved/stable/reduced",
        "competition_level": "high/medium/low",
        "food_availability": "abundant/adequate/scarce"
    }},
    
    "migration_cost": {{
        "journey_mortality": 0.05-0.2,  // 迁徙途中损失
        "energy_cost": "high/medium/low",
        "separation_risk": 0.0-0.3  // 种群分离风险
    }},
    
    "alternative_recommendation": {{
        "destination": "备选地块ID",
        "reason": "为什么是备选"
    }},
    
    "narrative": "60-80字描述这次迁徙的过程和预期"
}}

=== 选择原则 ===
1. 消费者（T2+）必须有足够的猎物
2. 距离不宜过远（考虑迁徙损失）
3. 避开高竞争区域
4. 环境适宜度 > 0.5
5. 优先选择与当前栖息地类型相似的区域

只返回JSON对象。
""",

    # ==================== 批量处理版本 ====================
    "pressure_assessment_batch": """你是生态学专家，批量评估多个物种对当前环境压力的应对能力。

**重要：必须返回纯JSON格式，不要使用markdown或其他格式。**

=== 全局环境压力 ===
总压力强度：{total_pressure:.1f}/10
压力来源：{pressure_sources}
重大事件：{major_events}

【⚠️ 压力强度解读】
- 0-2: 背景活动，几乎不影响生态（修正系数接近1.0）
- 2-4: 轻度压力
- 4-6: 中度压力
- 6-8: 重度压力
- 8-10: 极端/灾难级

=== 待评估物种列表 ===
{species_list}

=== 任务 ===
为每个物种评估其应对压力的能力，返回JSON数组：

{{
    "assessments": [
        {{
            "lineage_code": "物种代码",
            "survival_modifier": 0.5-1.5,
            "response_strategy": "逃避/对抗/适应/忍耐/衰退",
            "key_factor": "最关键的生存/风险因素",
            "population_behavior": "种群行为预测",
            "brief_narrative": "40-60字简述"
        }}
    ]
}}

=== 修正系数指南（必须结合压力强度）===
📊 低压力（<3）: 大多数物种给0.9-1.1
📊 中压力（3-6）: 根据特质匹配度给0.7-1.4
📊 高压力（>6）: 才适用极端修正系数

- 0.3-0.5: 物种完美适应（仅高压力时）
- 0.5-0.7: 显著优势
- 0.7-0.9: 小幅优势
- 0.9-1.1: 中性/背景压力时的默认值
- 1.1-1.3: 较脆弱
- 1.3-1.6: 高危状态
- 1.6-2.0: 完全不适应（仅高压力+高脆弱时）

⚠️ 只有灾难压力强度>=7时，才考虑给1.5-2.0！

只返回JSON对象。
"""
}

