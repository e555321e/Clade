"""演示板块构造系统"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from app.services.tectonic import TectonicSystem


def main():
    print("=" * 60)
    print("板块构造系统演示（含威尔逊周期）")
    print("=" * 60)
    
    # 初始化系统
    system = TectonicSystem(width=128, height=40, seed=42)
    print("\n系统初始化成功！")
    
    # 获取统计信息
    stats = system.get_statistics()
    print(f"  - 板块数量: {stats['n_plates']}")
    print(f"  - 地块数量: {stats['n_tiles']}")
    print(f"  - 火山数量: {stats['features']['volcanoes']}")
    print(f"  - 热点数量: {stats['features']['hotspots']}")
    print(f"  - 陆地比例: {stats['land_ratio']:.1%}")
    
    # 显示威尔逊周期信息
    wilson = system.get_wilson_phase()
    print("\n威尔逊周期状态:")
    print(f"  - 当前阶段: {wilson['phase']}")
    print(f"  - 阶段进度: {wilson['progress']:.0%}")
    print(f"  - 剩余回合: {wilson['turns_remaining']}")
    print(f"  - 大陆聚合度: {wilson['aggregation']:.1%}")
    print(f"  - 描述: {wilson['description']}")
    
    # 显示对流单元
    cells = system.get_convection_cells()
    print(f"\n对流单元: {len(cells)} 个")
    for c in cells[:3]:
        print(f"  [{c['id']}] 中心=({c['center_x']:.0f},{c['center_y']:.0f}) "
              f"半径={c['radius']:.0f} 方向={c['direction']}")
    
    # 显示板块运动
    print("\n板块列表（运动速度）:")
    for p in system.get_plates()[:5]:
        print(f"  [{p.id}] {p.plate_type.value:12s} "
              f"速度=({p.velocity_x:.3f}, {p.velocity_y:.3f}) "
              f"面积={p.tile_count}")
    if len(system.get_plates()) > 5:
        print(f"  ... 还有 {len(system.get_plates()) - 5} 个板块")
    
    # 执行多回合，观察周期变化
    print("\n执行30回合模拟...")
    phase_changes = []
    for i in range(30):
        result = system.step(pressure_modifiers={"volcanic_eruption": 3})
        
        # 检测阶段变化
        for event in result.events:
            if event.event_type == "wilson_phase_change":
                phase_changes.append((i + 1, event.description))
    
    print(f"  - 最终回合: {system.turn_index}")
    
    # 显示阶段变化
    if phase_changes:
        print("\n周期阶段变化:")
        for turn, desc in phase_changes:
            print(f"  回合 {turn}: {desc}")
    
    # 最终状态
    stats2 = system.get_statistics()
    wilson2 = system.get_wilson_phase()
    
    print("\n最终状态:")
    print(f"  - 威尔逊阶段: {wilson2['phase']} (进度 {wilson2['progress']:.0%})")
    print(f"  - 已完成周期: {wilson2['total_cycles']}")
    print(f"  - 海拔范围: {stats2['elevation']['min']:.0f}m ~ {stats2['elevation']['max']:.0f}m")
    print(f"  - 地幔活动: {stats2['mantle']['activity']:.2f}")
    
    # 显示平均板块速度变化
    avg_speed = sum(p.speed() for p in system.get_plates()) / len(system.get_plates())
    print(f"  - 平均板块速度: {avg_speed:.4f}")
    
    print("\n" + "=" * 60)
    print("✓ 板块构造系统运行正常！")
    print("  新增: 地幔对流驱动 + 威尔逊周期")
    print("=" * 60)


if __name__ == "__main__":
    main()

