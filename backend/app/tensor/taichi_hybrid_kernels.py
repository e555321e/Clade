"""
Taichi 内核定义模块

此模块在导入时初始化 Taichi 并定义所有内核。
支持多种 GPU 后端：
- NVIDIA: CUDA (首选)
- AMD: Vulkan
- Intel: Vulkan
- Apple: Metal (macOS)

如果 Taichi 不可用，则此模块的导入会失败。
"""

import logging
import taichi as ti

logger = logging.getLogger(__name__)

# 初始化 Taichi（在模块级别，但只初始化一次）
_taichi_initialized = False
_taichi_backend = None

def _ensure_taichi_init():
    """确保 Taichi 只初始化一次，支持多 GPU 厂商
    
    尝试顺序：
    1. CUDA (NVIDIA 最优)
    2. Vulkan (AMD/Intel/NVIDIA 通用)
    3. Metal (macOS)
    4. OpenGL (兼容层)
    5. CPU (最后回退)
    """
    global _taichi_initialized, _taichi_backend
    
    if _taichi_initialized:
        return _taichi_backend
    
    # 按优先级尝试各后端
    backends = [
        ("cuda", ti.cuda, "NVIDIA CUDA"),
        ("vulkan", ti.vulkan, "Vulkan (AMD/Intel/NVIDIA)"),
        ("metal", ti.metal, "Apple Metal"),
        ("opengl", ti.opengl, "OpenGL"),
    ]
    
    for backend_name, backend_arch, backend_desc in backends:
        try:
            ti.init(
                arch=backend_arch, 
                default_fp=ti.f32, 
                offline_cache=True,
                # 对于 Vulkan，设置更宽松的内存限制
                device_memory_fraction=0.7 if backend_name == "vulkan" else 0.8,
            )
            _taichi_initialized = True
            _taichi_backend = backend_name
            logger.info(f"[Taichi] 初始化成功: {backend_desc}")
            return backend_name
        except Exception as e:
            logger.debug(f"[Taichi] {backend_desc} 初始化失败: {e}")
            continue
    
    # 所有 GPU 后端失败，抛出错误（GPU-only 模式）
    _taichi_initialized = True  # 防止重复尝试
    _taichi_backend = None
    raise RuntimeError(
        "Taichi GPU 初始化失败。支持的 GPU:\n"
        "  - NVIDIA: 需要 CUDA 驱动\n"
        "  - AMD: 需要 Vulkan 驱动 (AMD Software/ROCm)\n"
        "  - Intel: 需要 Vulkan 驱动 (Intel Graphics Driver)\n"
        "请确保已安装对应的 GPU 驱动程序。"
    )

def get_taichi_backend() -> str | None:
    """获取当前 Taichi 后端名称"""
    return _taichi_backend

_ensure_taichi_init()


@ti.kernel
def kernel_mortality(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    env: ti.types.ndarray(dtype=ti.f32, ndim=3),
    params: ti.types.ndarray(dtype=ti.f32, ndim=2),
    result: ti.types.ndarray(dtype=ti.f32, ndim=3),
    temp_idx: ti.i32,
    temp_opt: ti.f32,
    temp_tol: ti.f32,
):
    """死亡率计算 - Taichi 并行"""
    for s, i, j in ti.ndrange(pop.shape[0], pop.shape[1], pop.shape[2]):
        if pop[s, i, j] > 0:
            temp = env[temp_idx, i, j]
            deviation = ti.abs(temp - temp_opt)
            mortality = 1.0 - ti.exp(-deviation / temp_tol)
            result[s, i, j] = ti.max(0.01, ti.min(0.99, mortality))
        else:
            result[s, i, j] = 0.0


@ti.kernel
def kernel_diffusion(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    new_pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    rate: ti.f32,
):
    """种群扩散 - Taichi 并行"""
    S, H, W = pop.shape[0], pop.shape[1], pop.shape[2]
    neighbor_rate = rate / 4.0
    
    for s, i, j in ti.ndrange(S, H, W):
        center = pop[s, i, j] * (1.0 - rate)
        received = 0.0
        
        if i > 0:
            received += pop[s, i - 1, j] * neighbor_rate
        if i < H - 1:
            received += pop[s, i + 1, j] * neighbor_rate
        if j > 0:
            received += pop[s, i, j - 1] * neighbor_rate
        if j < W - 1:
            received += pop[s, i, j + 1] * neighbor_rate
        
        new_pop[s, i, j] = center + received


@ti.kernel
def kernel_apply_mortality(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    mortality: ti.types.ndarray(dtype=ti.f32, ndim=3),
    result: ti.types.ndarray(dtype=ti.f32, ndim=3),
):
    """应用死亡率 - Taichi 并行"""
    for s, i, j in ti.ndrange(pop.shape[0], pop.shape[1], pop.shape[2]):
        result[s, i, j] = pop[s, i, j] * (1.0 - mortality[s, i, j])


@ti.kernel
def kernel_reproduction(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    fitness: ti.types.ndarray(dtype=ti.f32, ndim=3),
    capacity: ti.types.ndarray(dtype=ti.f32, ndim=2),
    birth_rate: ti.f32,
    result: ti.types.ndarray(dtype=ti.f32, ndim=3),
):
    """繁殖计算 - Taichi 并行"""
    S, H, W = pop.shape[0], pop.shape[1], pop.shape[2]
    for s, i, j in ti.ndrange(S, H, W):
        if pop[s, i, j] > 0:
            total_pop = 0.0
            for sp in range(S):
                total_pop += pop[sp, i, j]
            
            cap = capacity[i, j]
            if cap > 0 and total_pop > 0:
                crowding = ti.min(1.0, total_pop / cap)
                effective_rate = birth_rate * fitness[s, i, j] * (1.0 - crowding)
                result[s, i, j] = pop[s, i, j] * (1.0 + effective_rate)
            else:
                result[s, i, j] = pop[s, i, j]
        else:
            result[s, i, j] = 0.0


@ti.kernel
def kernel_competition(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    fitness: ti.types.ndarray(dtype=ti.f32, ndim=3),
    result: ti.types.ndarray(dtype=ti.f32, ndim=3),
    strength: ti.f32,
):
    """种间竞争 - Taichi 并行"""
    S = pop.shape[0]
    for s, i, j in ti.ndrange(pop.shape[0], pop.shape[1], pop.shape[2]):
        if pop[s, i, j] > 0:
            total_competitor = 0.0
            for sp in range(S):
                if sp != s:
                    total_competitor += pop[sp, i, j]
            
            my_fitness = fitness[s, i, j]
            if my_fitness > 0:
                pressure = total_competitor * strength / (my_fitness + 0.1)
                loss = ti.min(0.5, pressure / (pop[s, i, j] + 1.0))
                result[s, i, j] = pop[s, i, j] * (1.0 - loss)
            else:
                result[s, i, j] = pop[s, i, j] * 0.9
        else:
            result[s, i, j] = 0.0


@ti.kernel
def kernel_redistribute_population(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    current_totals: ti.types.ndarray(dtype=ti.f32, ndim=1),
    new_totals: ti.types.ndarray(dtype=ti.f32, ndim=1),
    out_pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    tile_count: ti.i32,
):
    """按权重或均匀分配新的种群总数 - Taichi 并行"""
    for s, i, j in ti.ndrange(pop.shape[0], pop.shape[1], pop.shape[2]):
        target = new_totals[s]
        if target <= 0:
            out_pop[s, i, j] = 0.0
        else:
            total = current_totals[s]
            if total > 0:
                weight = pop[s, i, j] / total
                out_pop[s, i, j] = weight * target
            else:
                out_pop[s, i, j] = target / tile_count


# ============================================================================
# 迁徙相关内核 - GPU 加速物种迁徙计算
# ============================================================================

@ti.kernel
def kernel_compute_suitability(
    env: ti.types.ndarray(dtype=ti.f32, ndim=3),
    species_prefs: ti.types.ndarray(dtype=ti.f32, ndim=2),
    habitat_mask: ti.types.ndarray(dtype=ti.f32, ndim=3),
    result: ti.types.ndarray(dtype=ti.f32, ndim=3),
):
    """批量计算所有物种对所有地块的适宜度 - Taichi 并行
    
    Args:
        env: 环境张量 (C, H, W) - [温度, 湿度, 海拔, 资源, 陆地, 海洋, 海岸]
        species_prefs: 物种偏好 (S, 7) - [温度偏好, 湿度偏好, 海拔偏好, 资源需求, 陆地, 海洋, 海岸]
        habitat_mask: 栖息地类型掩码 (S, H, W) - 当前物种是否可以存活于该地块
        result: 适宜度输出 (S, H, W)
    """
    S, H, W = result.shape[0], result.shape[1], result.shape[2]
    
    for s, i, j in ti.ndrange(S, H, W):
        # 温度匹配 (env[0] 是归一化温度 [-1, 1], prefs[0] 是温度偏好)
        temp_diff = ti.abs(env[0, i, j] - species_prefs[s, 0])
        temp_match = ti.max(0.0, 1.0 - temp_diff * 2.0)
        
        # 湿度匹配
        humidity_diff = ti.abs(env[1, i, j] - species_prefs[s, 1])
        humidity_match = ti.max(0.0, 1.0 - humidity_diff * 2.0)
        
        # 资源匹配
        resource_match = env[3, i, j]
        
        # 栖息地类型匹配
        habitat_match = (
            env[4, i, j] * species_prefs[s, 4] +  # 陆地
            env[5, i, j] * species_prefs[s, 5] +  # 海洋
            env[6, i, j] * species_prefs[s, 6]    # 海岸
        )
        
        # 综合适宜度
        base_score = (
            temp_match * 0.3 +
            humidity_match * 0.2 +
            resource_match * 0.2 +
            habitat_match * 0.3
        )
        
        # 应用栖息地掩码（硬约束）
        if habitat_mask[s, i, j] > 0.5:
            # 如果温度或栖息地完全不匹配，适宜度归零
            if temp_match < 0.05 or habitat_match < 0.01:
                result[s, i, j] = 0.0
            else:
                result[s, i, j] = ti.max(0.0, ti.min(1.0, base_score))
        else:
            result[s, i, j] = 0.0


@ti.kernel
def kernel_compute_distance_weights(
    current_pos: ti.types.ndarray(dtype=ti.f32, ndim=3),
    result: ti.types.ndarray(dtype=ti.f32, ndim=3),
    max_distance: ti.f32,
):
    """批量计算所有物种从当前位置到所有地块的距离权重 - Taichi 并行
    
    Args:
        current_pos: 当前种群位置 (S, H, W) - 种群密度
        result: 距离权重输出 (S, H, W)
        max_distance: 最大迁徙距离
    """
    S, H, W = result.shape[0], result.shape[1], result.shape[2]
    
    for s, i, j in ti.ndrange(S, H, W):
        # 计算该物种的质心
        total_pop = 0.0
        center_i = 0.0
        center_j = 0.0
        
        for ii in range(H):
            for jj in range(W):
                pop = current_pos[s, ii, jj]
                if pop > 0:
                    total_pop += pop
                    center_i += ii * pop
                    center_j += jj * pop
        
        if total_pop > 0:
            center_i /= total_pop
            center_j /= total_pop
            
            # 曼哈顿距离
            dist = ti.abs(ti.cast(i, ti.f32) - center_i) + ti.abs(ti.cast(j, ti.f32) - center_j)
            
            # 转换为权重 (近=1, 远=0)
            result[s, i, j] = ti.max(0.0, 1.0 - dist / max_distance)
        else:
            result[s, i, j] = 1.0


@ti.kernel
def kernel_compute_prey_density(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    trophic_levels: ti.types.ndarray(dtype=ti.f32, ndim=1),
    consumer_idx: ti.i32,
    result: ti.types.ndarray(dtype=ti.f32, ndim=2),
):
    """计算消费者的猎物密度分布 - Taichi 并行
    
    Args:
        pop: 种群张量 (S, H, W)
        trophic_levels: 营养级数组 (S,)
        consumer_idx: 消费者物种索引
        result: 猎物密度输出 (H, W)
    """
    S, H, W = pop.shape[0], pop.shape[1], pop.shape[2]
    consumer_trophic = trophic_levels[consumer_idx]
    
    for i, j in ti.ndrange(H, W):
        prey_density = 0.0
        
        for s in range(S):
            # 猎物的营养级应该比消费者低约1级
            if trophic_levels[s] < consumer_trophic and trophic_levels[s] >= consumer_trophic - 1.5:
                prey_density += pop[s, i, j]
        
        result[i, j] = prey_density


@ti.kernel
def kernel_migration_decision(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    suitability: ti.types.ndarray(dtype=ti.f32, ndim=3),
    distance_weights: ti.types.ndarray(dtype=ti.f32, ndim=3),
    death_rates: ti.types.ndarray(dtype=ti.f32, ndim=1),
    migration_scores: ti.types.ndarray(dtype=ti.f32, ndim=3),
    pressure_threshold: ti.f32,
    saturation_threshold: ti.f32,
):
    """批量计算所有物种的迁徙决策分数 - Taichi 并行
    
    Args:
        pop: 种群张量 (S, H, W)
        suitability: 适宜度张量 (S, H, W)
        distance_weights: 距离权重张量 (S, H, W)
        death_rates: 每个物种的死亡率 (S,)
        migration_scores: 迁徙分数输出 (S, H, W)
        pressure_threshold: 压力迁徙阈值
        saturation_threshold: 饱和度阈值
    """
    S, H, W = pop.shape[0], pop.shape[1], pop.shape[2]
    
    for s, i, j in ti.ndrange(S, H, W):
        # 当前地块已有种群，不需要迁入
        if pop[s, i, j] > 0:
            migration_scores[s, i, j] = 0.0
            continue
        
        death_rate = death_rates[s]
        base_score = suitability[s, i, j] * 0.5 + distance_weights[s, i, j] * 0.5
        
        # 压力驱动迁徙 - 死亡率高时更愿意迁移
        if death_rate > pressure_threshold:
            # 高压力模式：适宜度权重更高，愿意走得更远
            pressure_boost = ti.min(0.5, (death_rate - pressure_threshold) * 2.0)
            base_score = suitability[s, i, j] * (0.6 + pressure_boost * 0.2) + distance_weights[s, i, j] * (0.4 - pressure_boost * 0.2)
        
        # 添加随机扰动（用格子坐标模拟）
        noise = 0.85 + 0.3 * ti.sin(ti.cast(i * 17 + j * 31 + s * 7, ti.f32))
        migration_scores[s, i, j] = base_score * noise


@ti.kernel
def kernel_execute_migration(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    migration_scores: ti.types.ndarray(dtype=ti.f32, ndim=3),
    new_pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    migration_rates: ti.types.ndarray(dtype=ti.f32, ndim=1),
    score_threshold: ti.f32,
):
    """执行迁徙 - Taichi 并行
    
    Args:
        pop: 当前种群张量 (S, H, W)
        migration_scores: 迁徙分数张量 (S, H, W)
        new_pop: 迁徙后的种群张量 (S, H, W)
        migration_rates: 每个物种的迁徙比例 (S,)
        score_threshold: 分数阈值，低于此值不迁徙
    """
    S, H, W = pop.shape[0], pop.shape[1], pop.shape[2]
    
    for s in range(S):
        # 计算该物种的总种群和总迁徙分数
        total_pop = 0.0
        total_score = 0.0
        
        for i, j in ti.ndrange(H, W):
            total_pop += pop[s, i, j]
            if migration_scores[s, i, j] > score_threshold:
                total_score += migration_scores[s, i, j]
        
        # 迁徙量
        migrate_amount = total_pop * migration_rates[s]
        
        # 按分数比例分配迁徙种群
        for i, j in ti.ndrange(H, W):
            if pop[s, i, j] > 0:
                # 原有种群保留部分
                new_pop[s, i, j] = pop[s, i, j] * (1.0 - migration_rates[s])
            else:
                new_pop[s, i, j] = 0.0
            
            # 分配迁入种群
            if total_score > 0 and migration_scores[s, i, j] > score_threshold:
                score_ratio = migration_scores[s, i, j] / total_score
                new_pop[s, i, j] += migrate_amount * score_ratio


@ti.kernel
def kernel_advanced_diffusion(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    suitability: ti.types.ndarray(dtype=ti.f32, ndim=3),
    new_pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    base_rate: ti.f32,
):
    """带适宜度引导的高级扩散 - Taichi 并行
    
    种群会优先向适宜度更高的地块扩散。
    
    Args:
        pop: 种群张量 (S, H, W)
        suitability: 适宜度张量 (S, H, W)
        new_pop: 扩散后的种群张量 (S, H, W)
        base_rate: 基础扩散率
    """
    S, H, W = pop.shape[0], pop.shape[1], pop.shape[2]
    
    for s, i, j in ti.ndrange(S, H, W):
        current = pop[s, i, j]
        if current <= 0:
            new_pop[s, i, j] = 0.0
            continue
        
        # 计算到邻居的扩散
        outflow = 0.0
        inflow = 0.0
        
        # 四个邻居方向
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for di, dj in ti.static(neighbors):
            ni = i + di
            nj = j + dj
            
            if 0 <= ni < H and 0 <= nj < W:
                my_suit = suitability[s, i, j]
                neighbor_suit = suitability[s, ni, nj]
                
                # 适宜度梯度决定扩散方向和强度
                # 如果邻居适宜度更高，更多种群流向邻居
                gradient = neighbor_suit - my_suit
                
                if gradient > 0:
                    # 向高适宜度流出
                    rate = base_rate * (1.0 + gradient)
                    outflow += current * rate * 0.25
                elif gradient < 0:
                    # 从低适宜度流入
                    rate = base_rate * (1.0 - gradient)
                    inflow += pop[s, ni, nj] * rate * 0.25
        
        # 限制最大流出
        outflow = ti.min(outflow, current * 0.5)
        
        new_pop[s, i, j] = current - outflow + inflow


# ============================================================================
# 多因子死亡率内核 - GPU 加速完整生态死亡率计算
# ============================================================================

@ti.kernel
def kernel_multifactor_mortality(
    pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
    env: ti.types.ndarray(dtype=ti.f32, ndim=3),
    species_prefs: ti.types.ndarray(dtype=ti.f32, ndim=2),
    species_params: ti.types.ndarray(dtype=ti.f32, ndim=2),
    trophic_levels: ti.types.ndarray(dtype=ti.f32, ndim=1),
    pressure_overlay: ti.types.ndarray(dtype=ti.f32, ndim=3),
    result: ti.types.ndarray(dtype=ti.f32, ndim=3),
    base_mortality: ti.f32,
    temp_weight: ti.f32,
    competition_weight: ti.f32,
    resource_weight: ti.f32,
    capacity_multiplier: ti.f32,
    era_scaling: ti.f32,
):
    """多因子死亡率计算 - Taichi 全并行
    
    综合以下因子：
    1. 温度压力
    2. 湿度压力
    3. 竞争压力（同地块物种竞争）
    4. 资源压力（承载力）
    5. 营养级压力（捕食/被捕食）
    6. 外部压力（灾害等）
    
    Args:
        pop: 种群张量 (S, H, W)
        env: 环境张量 (C, H, W) - [temp, humidity, altitude, resource, land, sea, coast]
        species_prefs: 物种偏好 (S, 7)
        species_params: 物种参数 (S, F) - 包含耐受性等
        trophic_levels: 营养级 (S,)
        pressure_overlay: 外部压力叠加 (C_pressure, H, W)
        result: 死亡率输出 (S, H, W)
        base_mortality: 基础死亡率
        temp_weight: 温度死亡率权重
        competition_weight: 竞争死亡率权重
        resource_weight: 资源死亡率权重
        capacity_multiplier: 承载力乘数
        era_scaling: 时代缩放因子
    """
    S, H, W = pop.shape[0], pop.shape[1], pop.shape[2]
    C_env = env.shape[0]
    C_pressure = pressure_overlay.shape[0]
    
    for s, i, j in ti.ndrange(S, H, W):
        if pop[s, i, j] <= 0:
            result[s, i, j] = 0.0
            continue
        
        # === 1. 温度死亡率 ===
        temp_channel = 1 if C_env > 1 else 0
        temp = env[temp_channel, i, j]
        temp_pref = species_prefs[s, 0] * 50.0  # 偏好范围 -50~50
        temp_deviation = ti.abs(temp - temp_pref)
        
        # 温度耐受性
        temp_tolerance = 15.0
        if species_params.shape[1] >= 2:
            temp_tolerance = ti.max(5.0, species_params[s, 1])
        
        temp_mortality = 1.0 - ti.exp(-temp_deviation / temp_tolerance)
        temp_mortality = ti.max(0.01, ti.min(0.8, temp_mortality))
        
        # === 2. 湿度死亡率 ===
        humidity = env[1, i, j] if C_env > 2 else env[0, i, j] * 0.5
        humidity_pref = species_prefs[s, 1]
        humidity_deviation = ti.abs(humidity - humidity_pref)
        humidity_mortality = ti.min(0.4, humidity_deviation * 0.5)
        
        # === 3. 竞争死亡率 ===
        total_pop_tile = 0.0
        for sp in range(S):
            total_pop_tile += pop[sp, i, j]
        
        my_pop = ti.max(pop[s, i, j], 1e-6)
        competitor_pop = total_pop_tile - pop[s, i, j]
        competition_ratio = competitor_pop / (my_pop + 100.0)
        competition_mortality = ti.min(0.3, competition_ratio * 0.1)
        
        # === 4. 资源死亡率 ===
        resources = env[3, i, j] if C_env > 3 else 100.0
        capacity = resources * capacity_multiplier
        saturation = total_pop_tile / (capacity + 1e-6)
        resource_mortality = ti.max(0.0, ti.min(0.4, (saturation - 0.5) * 0.4))
        
        # === 5. 营养级死亡率 ===
        # 消费者（T>=2）在缺乏猎物时死亡率上升
        my_trophic = trophic_levels[s]
        prey_scarcity_mortality = 0.0
        
        if my_trophic >= 2.0:
            # 计算猎物密度
            prey_density = 0.0
            for sp in range(S):
                prey_trophic = trophic_levels[sp]
                if prey_trophic < my_trophic and prey_trophic >= my_trophic - 1.5:
                    prey_density += pop[sp, i, j]
            
            # 归一化
            prey_density_norm = prey_density / (total_pop_tile + 1e-6)
            prey_scarcity_mortality = (1.0 - prey_density_norm) * 0.2
        
        # === 6. 外部压力死亡率 ===
        external_pressure = 0.0
        for c in range(C_pressure):
            external_pressure += pressure_overlay[c, i, j]
        external_mortality = ti.min(0.5, external_pressure * 0.1)
        
        # === 综合死亡率 ===
        total_mortality = (
            temp_mortality * temp_weight +
            humidity_mortality * 0.1 +
            competition_mortality * competition_weight +
            resource_mortality * resource_weight +
            prey_scarcity_mortality +
            external_mortality +
            base_mortality
        )
        
        # 时代缩放：早期时代死亡率略低
        if era_scaling > 1.5:
            scale_factor = ti.max(0.7, 1.0 / ti.pow(era_scaling, 0.2))
            total_mortality *= scale_factor
        
        result[s, i, j] = ti.max(0.01, ti.min(0.95, total_mortality))


# ============================================================================
# 预编译所有内核（在主线程中）
# ============================================================================

def _precompile_all_kernels():
    """在模块加载时预编译所有 Taichi 内核
    
    Taichi 内核在首次调用时才会编译，如果首次调用发生在非主线程，
    会触发 "Assertion failure: std::this_thread::get_id() == main_thread_id_" 错误。
    
    通过在模块加载时（主线程）用小数组调用所有内核，可以提前完成编译。
    """
    global _taichi_backend
    
    if _taichi_backend is None:
        logger.warning("[Taichi] 跳过预编译：GPU 后端未初始化")
        return
    
    import numpy as np
    
    # 使用最小的测试数组
    S, H, W = 1, 2, 2
    
    try:
        # 创建测试数组
        pop = np.ones((S, H, W), dtype=np.float32)
        env = np.ones((7, H, W), dtype=np.float32)
        params = np.ones((S, 4), dtype=np.float32)
        prefs = np.ones((S, 6), dtype=np.float32)
        trophic = np.ones((S,), dtype=np.float32)
        pressure = np.zeros((3, H, W), dtype=np.float32)
        result_3d = np.zeros((S, H, W), dtype=np.float32)
        suitability = np.ones((S, H, W), dtype=np.float32)
        capacity = np.ones((H, W), dtype=np.float32)
        habitat_mask = np.ones((S, H, W), dtype=np.float32)
        death_rates = np.zeros((S,), dtype=np.float32)
        migration_rates = np.ones((S,), dtype=np.float32)
        distance_weights = np.ones((S, H, W), dtype=np.float32)
        migration_scores = np.zeros((S, H, W), dtype=np.float32)
        
        # 预编译各内核（小数组调用，仅触发编译）
        kernel_mortality(pop, env, params, result_3d, 0, 20.0, 15.0)
        kernel_apply_mortality(pop, result_3d, result_3d)
        kernel_compute_suitability(env, prefs, habitat_mask, result_3d)
        kernel_advanced_diffusion(pop, suitability, result_3d, 0.1)
        kernel_reproduction(pop, suitability, capacity, 0.1, result_3d)
        kernel_competition(pop, suitability, result_3d, 0.1)
        kernel_compute_distance_weights(pop, result_3d, 3.0)
        # kernel_migration_decision 需要 7 个参数
        kernel_migration_decision(
            pop, suitability, distance_weights, death_rates, 
            migration_scores, 0.12, 0.8  # pressure_threshold, saturation_threshold
        )
        kernel_execute_migration(pop, migration_scores, result_3d, migration_rates, 0.1)
        kernel_multifactor_mortality(
            pop, env, prefs, params, trophic, pressure, result_3d,
            0.05, 0.3, 0.2, 0.15, 1.0, 1.0
        )
        
        # 同步 Taichi 运行时
        ti.sync()
        
        logger.info("[Taichi] 所有内核预编译完成")
        
    except Exception as e:
        logger.warning(f"[Taichi] 内核预编译失败（将在首次使用时编译）: {e}")


# 在模块加载时预编译
_precompile_all_kernels()







