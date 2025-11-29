"""板块运动引擎测试"""

import pytest
import numpy as np

from ..plate_generator import PlateGenerator
from ..motion_engine import PlateMotionEngine
from ..models import Plate, PlateType, BoundaryType, MotionPhase


class TestPlateMotionEngine:
    """测试板块运动引擎"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.width = 64
        self.height = 20
        self.generator = PlateGenerator(self.width, self.height)
        self.engine = PlateMotionEngine(self.width, self.height)
        
        # 生成初始状态
        self.plates, self.plate_map, self.tiles = self.generator.generate(seed=42)
    
    def test_step_returns_valid_results(self):
        """测试step返回有效结果"""
        terrain_changes, events, pressure_feedback = self.engine.step(
            self.plates, self.plate_map, self.tiles, turn_index=0
        )
        
        # 返回类型正确
        assert isinstance(terrain_changes, list)
        assert isinstance(events, list)
        assert isinstance(pressure_feedback, dict)
    
    def test_step_updates_plate_ages(self):
        """测试step更新板块年龄"""
        initial_ages = [p.age for p in self.plates]
        
        self.engine.step(self.plates, self.plate_map, self.tiles, turn_index=0)
        
        # 所有板块年龄增加1
        for i, plate in enumerate(self.plates):
            assert plate.age == initial_ages[i] + 1
    
    def test_boundary_detection(self):
        """测试边界检测"""
        self.engine.step(self.plates, self.plate_map, self.tiles, turn_index=0)
        
        # 应该有边界地块
        boundary_tiles = [t for t in self.tiles if t.boundary_type != BoundaryType.INTERNAL]
        assert len(boundary_tiles) > 0
    
    def test_terrain_changes_within_limits(self):
        """测试地形变化在限制范围内"""
        terrain_changes, _, _ = self.engine.step(
            self.plates, self.plate_map, self.tiles, turn_index=0
        )
        
        max_change = self.engine.terrain_config["max_elevation_change"]
        
        for tc in terrain_changes:
            delta = abs(tc.new_elevation - tc.old_elevation)
            assert delta <= max_change + 0.01  # 允许小误差
    
    def test_pressure_modifiers_affect_motion(self):
        """测试压力修改器影响运动"""
        # 先记录无压力时的速度
        plates1, _, _ = self.generator.generate(seed=42)
        self.engine.step(plates1, self.plate_map, self.tiles, pressure_modifiers={})
        speeds1 = [p.speed() for p in plates1]
        
        # 应用压力
        plates2, _, _ = self.generator.generate(seed=42)
        self.engine.step(
            plates2, self.plate_map, self.tiles,
            pressure_modifiers={"earthquake_period": 8}
        )
        speeds2 = [p.speed() for p in plates2]
        
        # 速度应该有所不同
        assert any(abs(s1 - s2) > 0.001 for s1, s2 in zip(speeds1, speeds2))
    
    def test_velocity_decay(self):
        """测试速度衰减"""
        # 设置一个高速板块
        self.plates[0].velocity_x = 0.2
        self.plates[0].velocity_y = 0.1
        
        initial_speed = self.plates[0].speed()
        
        self.engine.step(self.plates, self.plate_map, self.tiles, turn_index=0)
        
        # 速度应该减小（衰减）
        assert self.plates[0].speed() < initial_speed
    
    def test_polar_bounce(self):
        """测试极地反弹"""
        # 创建一个明确在极地边缘并向极地移动的板块
        polar_plate = None
        for plate in self.plates:
            if plate.rotation_center_y < 2:  # 在极地边缘
                polar_plate = plate
                break
        
        if polar_plate is None:
            # 如果没有极地板块，手动创建一个位于极地边缘的场景
            self.plates[0].rotation_center_y = 1.0
            self.plates[0].velocity_y = -0.1
            polar_plate = self.plates[0]
        else:
            polar_plate.velocity_y = -0.1  # 向北极移动
        
        initial_vy = polar_plate.velocity_y
        
        self.engine.step(self.plates, self.plate_map, self.tiles, turn_index=0)
        
        # 速度应该被限制或反弹（比初始值更正向）
        # 或者板块不再继续向极地移动（速度变小或反向）
        assert polar_plate.velocity_y > initial_vy or \
               polar_plate.rotation_center_y >= 1.0, \
               "极地边缘的板块应该受到反弹或限制"
    
    def test_events_have_valid_properties(self):
        """测试生成的事件有有效属性"""
        # 多次执行以增加事件概率
        all_events = []
        for i in range(10):
            _, events, _ = self.engine.step(
                self.plates, self.plate_map, self.tiles,
                pressure_modifiers={"earthquake_period": 5},
                turn_index=i
            )
            all_events.extend(events)
        
        for event in all_events:
            # 位置有效
            assert 0 <= event.x < self.width
            assert 0 <= event.y < self.height
            
            # 震级/强度有效
            assert event.magnitude > 0
            
            # 影响范围有效
            assert event.affected_radius > 0
    
    def test_motion_phase_updates(self):
        """测试运动阶段更新"""
        # 执行多步以触发状态变化
        for i in range(5):
            self.engine.step(self.plates, self.plate_map, self.tiles, turn_index=i)
        
        # 至少有一个板块有明确的运动阶段
        phases = [p.motion_phase for p in self.plates]
        assert any(phase != MotionPhase.STABLE for phase in phases) or \
               all(p.speed() < 0.05 for p in self.plates)


class TestBoundaryClassification:
    """测试边界分类"""
    
    def setup_method(self):
        self.engine = PlateMotionEngine(64, 20)
    
    def test_approaching_oceanic_continental(self):
        """测试接近的洋壳-陆壳边界"""
        oceanic = Plate(id=0, plate_index=0, plate_type=PlateType.OCEANIC,
                       velocity_x=0.1, rotation_center_x=30, rotation_center_y=10)
        continental = Plate(id=1, plate_index=1, plate_type=PlateType.CONTINENTAL,
                           velocity_x=-0.1, rotation_center_x=40, rotation_center_y=10)
        
        boundary = self.engine._classify_boundary(oceanic, continental)
        
        # 应该是俯冲边界
        assert boundary == BoundaryType.SUBDUCTION
    
    def test_separating_plates(self):
        """测试分离的板块"""
        plate_a = Plate(id=0, plate_index=0, velocity_x=-0.1,
                       rotation_center_x=30, rotation_center_y=10)
        plate_b = Plate(id=1, plate_index=1, velocity_x=0.1,
                       rotation_center_x=40, rotation_center_y=10)
        
        boundary = self.engine._classify_boundary(plate_a, plate_b)
        
        # 应该是张裂边界
        assert boundary == BoundaryType.DIVERGENT
    
    def test_continental_collision(self):
        """测试大陆碰撞"""
        cont_a = Plate(id=0, plate_index=0, plate_type=PlateType.CONTINENTAL,
                      velocity_x=0.1, rotation_center_x=30, rotation_center_y=10)
        cont_b = Plate(id=1, plate_index=1, plate_type=PlateType.CONTINENTAL,
                      velocity_x=-0.1, rotation_center_x=40, rotation_center_y=10)
        
        boundary = self.engine._classify_boundary(cont_a, cont_b)
        
        # 应该是碰撞边界
        assert boundary == BoundaryType.CONVERGENT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

