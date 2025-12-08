"""
Taichi 加速内核 - 实验模块

使用 Taichi 实现高性能的张量计算内核：
- 死亡率计算 (mortality)
- 种群扩散 (diffusion)
- 环境适应度评估 (fitness)
- 地理隔离检测 (isolation)

用法：
    from app.tensor.taichi_kernels import TaichiKernels
    
    kernels = TaichiKernels()
    mortality = kernels.compute_mortality(pop, env, params)
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import numpy as np

logger = logging.getLogger(__name__)

# Taichi 初始化标志
_taichi_initialized = False
_taichi_available = False

try:
    import taichi as ti
    _taichi_available = True
except ImportError:
    logger.warning("[Taichi] taichi 未安装，将使用 NumPy 回退")
    ti = None


def init_taichi(arch: str = "auto") -> bool:
    """初始化 Taichi 运行时（使用统一初始化函数）
    
    Args:
        arch: 目标架构（已废弃，始终使用 GPU）
    
    Returns:
        是否成功初始化
    """
    global _taichi_initialized
    
    if not _taichi_available:
        return False
    
    if _taichi_initialized:
        return True
    
    try:
        # 使用统一的初始化函数
        from .taichi_hybrid_kernels import _ensure_taichi_init
        _ensure_taichi_init()
        _taichi_initialized = True
        
        # 定义内核
        _define_taichi_kernels()
        
        logger.info(f"[Taichi] 初始化成功")
        return True
        
    except Exception as e:
        logger.warning(f"[Taichi] 初始化失败: {e}，将使用 NumPy 回退")
        return False


# ============================================================================
# Taichi 内核定义（仅在 Taichi 可用时编译）
# ============================================================================

# Taichi 内核将在 init_taichi() 后定义
# 使用延迟定义避免模块导入时就需要初始化 Taichi
_kernels_defined = False
_ti_compute_mortality = None
_ti_diffusion_step = None
_ti_apply_mortality = None
_ti_compute_fitness = None
_ti_sum_population = None


def _define_taichi_kernels():
    """在 Taichi 初始化后定义内核"""
    global _kernels_defined
    global _ti_compute_mortality, _ti_diffusion_step, _ti_apply_mortality
    global _ti_compute_fitness, _ti_sum_population
    
    if _kernels_defined or not _taichi_available:
        return
    
    @ti.kernel
    def compute_mortality_kernel(
        pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
        env: ti.types.ndarray(dtype=ti.f32, ndim=3),
        params: ti.types.ndarray(dtype=ti.f32, ndim=2),
        result: ti.types.ndarray(dtype=ti.f32, ndim=3),
        temp_idx: ti.i32,
        temp_opt: ti.f32,
        temp_tol: ti.f32,
    ):
        for s, i, j in ti.ndrange(pop.shape[0], pop.shape[1], pop.shape[2]):
            if pop[s, i, j] > 0:
                temp = env[temp_idx, i, j]
                temp_deviation = ti.abs(temp - temp_opt)
                base_mortality = 1.0 - ti.exp(-temp_deviation / temp_tol)
                result[s, i, j] = ti.max(0.01, ti.min(0.99, base_mortality))
            else:
                result[s, i, j] = 0.0
    
    @ti.kernel
    def diffusion_step_kernel(
        pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
        new_pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
        diffusion_rate: ti.f32,
    ):
        S, H, W = pop.shape[0], pop.shape[1], pop.shape[2]
        for s, i, j in ti.ndrange(S, H, W):
            center = pop[s, i, j] * (1.0 - diffusion_rate)
            received = 0.0
            neighbor_rate = diffusion_rate / 4.0
            
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
    def apply_mortality_kernel(
        pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
        mortality: ti.types.ndarray(dtype=ti.f32, ndim=3),
        result: ti.types.ndarray(dtype=ti.f32, ndim=3),
    ):
        for s, i, j in ti.ndrange(pop.shape[0], pop.shape[1], pop.shape[2]):
            survival_rate = 1.0 - mortality[s, i, j]
            result[s, i, j] = pop[s, i, j] * survival_rate
    
    @ti.kernel
    def compute_fitness_kernel(
        pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
        env: ti.types.ndarray(dtype=ti.f32, ndim=3),
        params: ti.types.ndarray(dtype=ti.f32, ndim=2),
        result: ti.types.ndarray(dtype=ti.f32, ndim=3),
        n_features: ti.i32,
    ):
        for s, i, j in ti.ndrange(pop.shape[0], pop.shape[1], pop.shape[2]):
            if pop[s, i, j] > 0:
                fitness = 0.0
                for f in range(n_features):
                    match = 1.0 - ti.abs(env[f, i, j] - params[s, f]) / 10.0
                    fitness += ti.max(0.0, match)
                result[s, i, j] = fitness / ti.cast(n_features, ti.f32)
            else:
                result[s, i, j] = 0.0
    
    @ti.kernel
    def sum_population_kernel(
        pop: ti.types.ndarray(dtype=ti.f32, ndim=3),
        result: ti.types.ndarray(dtype=ti.f32, ndim=1),
    ):
        for s in range(pop.shape[0]):
            total = 0.0
            for i, j in ti.ndrange(pop.shape[1], pop.shape[2]):
                total += pop[s, i, j]
            result[s] = total
    
    _ti_compute_mortality = compute_mortality_kernel
    _ti_diffusion_step = diffusion_step_kernel
    _ti_apply_mortality = apply_mortality_kernel
    _ti_compute_fitness = compute_fitness_kernel
    _ti_sum_population = sum_population_kernel
    _kernels_defined = True


# ============================================================================
# Python 接口类
# ============================================================================

class TaichiKernels:
    """Taichi 加速内核的 Python 接口
    
    自动处理 Taichi 初始化和 NumPy 回退。
    
    Example:
        kernels = TaichiKernels()
        
        # 计算死亡率
        mortality = kernels.compute_mortality(pop, env, params)
        
        # 种群扩散
        new_pop = kernels.diffusion_step(pop, rate=0.1)
    """
    
    def __init__(self, arch: str = "auto"):
        """初始化 Taichi 内核
        
        Args:
            arch: Taichi 后端架构
        """
        self._use_taichi = init_taichi(arch) if _taichi_available else False
        self._arch = arch
        
        if self._use_taichi:
            logger.info("[TaichiKernels] 使用 Taichi 加速")
        else:
            logger.info("[TaichiKernels] 使用 NumPy 回退")
    
    @property
    def is_taichi_enabled(self) -> bool:
        """是否启用了 Taichi"""
        return self._use_taichi
    
    def compute_mortality(
        self,
        pop: np.ndarray,
        env: np.ndarray,
        params: np.ndarray,
        temp_idx: int = 1,
        temp_opt: float = 20.0,
        temp_tol: float = 15.0,
    ) -> np.ndarray:
        """计算死亡率
        
        Args:
            pop: 种群张量 (S, H, W)
            env: 环境张量 (C, H, W)
            params: 物种参数 (S, F)
            temp_idx: 温度通道索引
            temp_opt: 最适温度
            temp_tol: 温度容忍度
        
        Returns:
            死亡率张量 (S, H, W)
        """
        result = np.zeros_like(pop, dtype=np.float32)
        
        if self._use_taichi and _ti_compute_mortality is not None:
            _ti_compute_mortality(
                pop.astype(np.float32),
                env.astype(np.float32),
                params.astype(np.float32),
                result,
                temp_idx,
                temp_opt,
                temp_tol,
            )
        else:
            # NumPy 回退
            temp = env[temp_idx]
            temp_deviation = np.abs(temp - temp_opt)
            base_mortality = 1.0 - np.exp(-temp_deviation / temp_tol)
            
            for s in range(pop.shape[0]):
                mask = pop[s] > 0
                result[s, mask] = np.clip(base_mortality[mask], 0.01, 0.99)
        
        return result
    
    def diffusion_step(
        self,
        pop: np.ndarray,
        diffusion_rate: float = 0.1,
    ) -> np.ndarray:
        """执行一步种群扩散
        
        Args:
            pop: 种群张量 (S, H, W)
            diffusion_rate: 扩散率 (0-1)
        
        Returns:
            扩散后的种群张量 (S, H, W)
        """
        new_pop = np.zeros_like(pop, dtype=np.float32)
        
        if self._use_taichi and _ti_diffusion_step is not None:
            _ti_diffusion_step(
                pop.astype(np.float32),
                new_pop,
                diffusion_rate,
            )
        else:
            # NumPy 回退
            from scipy.ndimage import convolve
            
            # 4邻居扩散核
            kernel = np.array([
                [0, 1, 0],
                [1, 0, 1],
                [0, 1, 0],
            ], dtype=np.float32) * (diffusion_rate / 4)
            kernel[1, 1] = 1.0 - diffusion_rate
            
            for s in range(pop.shape[0]):
                new_pop[s] = convolve(pop[s], kernel, mode='constant', cval=0)
        
        return new_pop
    
    def apply_mortality(
        self,
        pop: np.ndarray,
        mortality: np.ndarray,
    ) -> np.ndarray:
        """应用死亡率
        
        Args:
            pop: 种群张量 (S, H, W)
            mortality: 死亡率张量 (S, H, W)
        
        Returns:
            更新后的种群张量 (S, H, W)
        """
        result = np.zeros_like(pop, dtype=np.float32)
        
        if self._use_taichi and _ti_apply_mortality is not None:
            _ti_apply_mortality(
                pop.astype(np.float32),
                mortality.astype(np.float32),
                result,
            )
        else:
            result = pop * (1.0 - mortality)
        
        return result
    
    def compute_fitness(
        self,
        pop: np.ndarray,
        env: np.ndarray,
        params: np.ndarray,
    ) -> np.ndarray:
        """计算环境适应度
        
        Args:
            pop: 种群张量 (S, H, W)
            env: 环境张量 (C, H, W)
            params: 物种参数 (S, F)
        
        Returns:
            适应度张量 (S, H, W)
        """
        result = np.zeros_like(pop, dtype=np.float32)
        n_features = min(env.shape[0], params.shape[1])
        
        if self._use_taichi and _ti_compute_fitness is not None:
            _ti_compute_fitness(
                pop.astype(np.float32),
                env.astype(np.float32),
                params.astype(np.float32),
                result,
                n_features,
            )
        else:
            # NumPy 回退
            S, H, W = pop.shape
            
            for s in range(S):
                mask = pop[s] > 0
                if not mask.any():
                    continue
                
                fitness = np.zeros((H, W), dtype=np.float32)
                for f in range(n_features):
                    match = 1.0 - np.abs(env[f] - params[s, f]) / 10.0
                    fitness += np.maximum(0, match)
                
                result[s] = fitness / n_features
                result[s, ~mask] = 0
        
        return result
    
    def sum_population(self, pop: np.ndarray) -> np.ndarray:
        """计算每个物种的总种群
        
        Args:
            pop: 种群张量 (S, H, W)
        
        Returns:
            总种群数组 (S,)
        """
        if self._use_taichi and _ti_sum_population is not None:
            result = np.zeros(pop.shape[0], dtype=np.float32)
            _ti_sum_population(pop.astype(np.float32), result)
            return result
        else:
            return pop.sum(axis=(1, 2)).astype(np.float32)


# ============================================================================
# 性能基准测试
# ============================================================================

def benchmark_kernels(
    shape: tuple[int, int, int] = (10, 128, 128),
    iterations: int = 100,
) -> dict:
    """性能基准测试
    
    Args:
        shape: 张量形状 (S, H, W)
        iterations: 迭代次数
    
    Returns:
        性能指标字典
    """
    S, H, W = shape
    
    # 创建测试数据
    pop = np.random.rand(S, H, W).astype(np.float32) * 100
    env = np.random.rand(5, H, W).astype(np.float32)
    env[1] = np.random.rand(H, W) * 40 - 10  # 温度 -10 到 30
    params = np.random.rand(S, 5).astype(np.float32) * 10
    
    results = {
        "shape": shape,
        "iterations": iterations,
        "numpy": {},
        "taichi": {},
    }
    
    # NumPy 基准
    kernels_np = TaichiKernels.__new__(TaichiKernels)
    kernels_np._use_taichi = False
    
    # 预热
    kernels_np.compute_mortality(pop, env, params)
    kernels_np.diffusion_step(pop)
    
    # 测试死亡率计算
    start = time.perf_counter()
    for _ in range(iterations):
        kernels_np.compute_mortality(pop, env, params)
    results["numpy"]["mortality_ms"] = (time.perf_counter() - start) * 1000 / iterations
    
    # 测试扩散
    start = time.perf_counter()
    for _ in range(iterations):
        kernels_np.diffusion_step(pop)
    results["numpy"]["diffusion_ms"] = (time.perf_counter() - start) * 1000 / iterations
    
    # Taichi 基准（如果可用）
    if _taichi_available:
        kernels_ti = TaichiKernels(arch="auto")
        
        if kernels_ti.is_taichi_enabled:
            # 预热（触发 JIT 编译）
            for _ in range(3):
                kernels_ti.compute_mortality(pop, env, params)
                kernels_ti.diffusion_step(pop)
            
            # 测试死亡率计算
            start = time.perf_counter()
            for _ in range(iterations):
                kernels_ti.compute_mortality(pop, env, params)
            results["taichi"]["mortality_ms"] = (time.perf_counter() - start) * 1000 / iterations
            
            # 测试扩散
            start = time.perf_counter()
            for _ in range(iterations):
                kernels_ti.diffusion_step(pop)
            results["taichi"]["diffusion_ms"] = (time.perf_counter() - start) * 1000 / iterations
            
            # 计算加速比
            results["speedup"] = {
                "mortality": results["numpy"]["mortality_ms"] / results["taichi"]["mortality_ms"],
                "diffusion": results["numpy"]["diffusion_ms"] / results["taichi"]["diffusion_ms"],
            }
    
    return results


def print_benchmark_results(results: dict) -> None:
    """打印基准测试结果"""
    print("\n" + "=" * 60)
    print(f"Taichi vs NumPy 性能对比")
    print(f"张量形状: {results['shape']}, 迭代次数: {results['iterations']}")
    print("=" * 60)
    
    print(f"\n{'操作':<20} {'NumPy (ms)':<15} {'Taichi (ms)':<15} {'加速比':<10}")
    print("-" * 60)
    
    for op in ["mortality", "diffusion"]:
        np_time = results["numpy"].get(f"{op}_ms", 0)
        ti_time = results["taichi"].get(f"{op}_ms", 0)
        speedup = results.get("speedup", {}).get(op, 0)
        
        ti_str = f"{ti_time:.3f}" if ti_time > 0 else "N/A"
        speedup_str = f"{speedup:.2f}x" if speedup > 0 else "N/A"
        
        print(f"{op:<20} {np_time:.3f}{'':>8} {ti_str:<15} {speedup_str}")
    
    print("=" * 60)


if __name__ == "__main__":
    # 运行基准测试
    print("运行性能基准测试...")
    
    # 小规模测试
    results_small = benchmark_kernels(shape=(10, 64, 64), iterations=100)
    print_benchmark_results(results_small)
    
    # 中规模测试
    results_medium = benchmark_kernels(shape=(20, 128, 128), iterations=50)
    print_benchmark_results(results_medium)
    
    # 大规模测试
    results_large = benchmark_kernels(shape=(50, 256, 256), iterations=20)
    print_benchmark_results(results_large)

