import { useState } from "react";
import type { ViewMode } from "./MapViewSelector";

interface Props {
  viewMode: ViewMode;
  seaLevel?: number;
  temperature?: number;
  visible?: boolean;
  hasSelectedSpecies?: boolean;
}

// 图例数据定义 - 与后端 map_coloring.py 保持一致
const LEGENDS: Record<ViewMode, { 
  title: string;
  subtitle?: string;
  description?: string;  // 新增: 功能说明
  items: Array<{ color: string; label: string; range?: string }> 
}> = {
  terrain: {
    title: "实景地图",
    subtitle: "35级地形 + 30种覆盖",
    description: "显示真实世界风格的地形、植被和覆盖物",
    items: [
      // 海洋层级 (关键节点)
      { color: "#050a12", label: "超深海沟", range: "< -8000m" },
      { color: "#0c1e38", label: "深海平原", range: "-6000 ~ -4000m" },
      { color: "#2d6699", label: "大陆坡", range: "-800 ~ -400m" },
      { color: "#5dade2", label: "近岸浅水", range: "-50 ~ 0m" },
      // 陆地关键节点
      { color: "#3d6b4a", label: "潮间带", range: "0 ~ 10m" },
      { color: "#649f6d", label: "平原", range: "150 ~ 300m" },
      { color: "#a6c48e", label: "台地", range: "1000 ~ 1300m" },
      { color: "#9f7a50", label: "中山", range: "3500 ~ 4000m" },
      { color: "#f0f4f8", label: "极地之巅", range: "> 8000m" },
      // 冰雪类覆盖
      { color: "#F5FAFF", label: "冰川" },
      { color: "#E6F2FF", label: "冰原" },
      { color: "#8A9BAA", label: "冻土" },
      // 荒漠类覆盖
      { color: "#E8C872", label: "沙漠" },
      { color: "#C4A87A", label: "戈壁" },
      { color: "#A09080", label: "裸地" },
      // 草地类覆盖
      { color: "#7A9E8A", label: "苔原" },
      { color: "#A8D068", label: "草原" },
      { color: "#6A9A58", label: "灌木丛" },
      // 森林类覆盖
      { color: "#3E6850", label: "针叶林" },
      { color: "#3A7048", label: "阔叶林" },
      { color: "#1A5030", label: "雨林" },
      // 湿地类覆盖
      { color: "#3D5A45", label: "沼泽" },
      { color: "#3A5840", label: "红树林" },
    ],
  },
  terrain_type: {
    title: "地形分类",
    subtitle: "35级海拔分类",
    description: "按海拔高度分类的地形类型图",
    items: [
      // 海洋10级（显示关键节点）
      { color: "#050a12", label: "超深海沟", range: "< -8000m" },
      { color: "#081425", label: "深海沟", range: "-8000 ~ -6000m" },
      { color: "#12294a", label: "深海盆地", range: "-4000 ~ -2500m" },
      { color: "#235080", label: "大陆坡深部", range: "-1500 ~ -800m" },
      { color: "#3a7db3", label: "大陆架深部", range: "-400 ~ -150m" },
      { color: "#5dade2", label: "近岸浅水", range: "-50 ~ 0m" },
      // 陆地低海拔8级
      { color: "#3d6b4a", label: "潮间带", range: "0 ~ 10m" },
      { color: "#589264", label: "低海拔平原", range: "80 ~ 150m" },
      { color: "#72ab76", label: "缓坡丘陵", range: "300 ~ 500m" },
      { color: "#94c088", label: "高丘陵", range: "750 ~ 1000m" },
      // 陆地中海拔8级
      { color: "#b5c58e", label: "低高原", range: "1300 ~ 1600m" },
      { color: "#ccbb86", label: "亚山麓", range: "1900 ~ 2200m" },
      { color: "#bf9a6a", label: "低山", range: "2600 ~ 3000m" },
      { color: "#9f7a50", label: "中山", range: "3500 ~ 4000m" },
      // 高海拔9级
      { color: "#8d6c47", label: "中高山", range: "4000 ~ 4500m" },
      { color: "#6e6a5e", label: "雪线区", range: "5000 ~ 5500m" },
      { color: "#8a8e94", label: "永久冰雪", range: "6000 ~ 6500m" },
      { color: "#b5bcc6", label: "极高山", range: "7000 ~ 7500m" },
      { color: "#f0f4f8", label: "极地之巅", range: "> 8000m" },
    ],
  },
  elevation: {
    title: "海拔高度",
    subtitle: "35级连续色阶",
    description: "显示相对于海平面的海拔高度",
    items: [
      // 海洋
      { color: "#050a12", label: "超深海", range: "< -8000m" },
      { color: "#0c1e38", label: "深海", range: "-4000m" },
      { color: "#2d6699", label: "大陆坡", range: "-800m" },
      { color: "#5dade2", label: "近岸", range: "0m" },
      // 陆地低
      { color: "#4e855b", label: "平原", range: "+80m" },
      { color: "#72ab76", label: "丘陵", range: "+500m" },
      // 陆地中
      { color: "#a6c48e", label: "台地", range: "+1000m" },
      { color: "#c9ab78", label: "山麓", range: "+2200m" },
      { color: "#9f7a50", label: "中山", range: "+4000m" },
      // 高山
      { color: "#6e6a5e", label: "雪线", range: "+5000m" },
      { color: "#9ea4ac", label: "冰川", range: "+6500m" },
      { color: "#f0f4f8", label: "极巅", range: "> +8000m" },
    ],
  },
  biodiversity: {
    title: "生物热力图",
    subtitle: "物种数量分布",
    description: "显示每个地块的物种数量，颜色越暖表示物种越多",
    items: [
      { color: "#2D3436", label: "无生命", range: "0种" },
      { color: "#6C5CE7", label: "极少", range: "1种" },
      { color: "#0984E3", label: "稀少", range: "2种" },
      { color: "#00B894", label: "中等", range: "3-4种" },
      { color: "#BADC58", label: "较多", range: "5-7种" },
      { color: "#FDCB6E", label: "丰富", range: "8-10种" },
      { color: "#E17055", label: "极丰富", range: "11+种" },
    ],
  },
  climate: {
    title: "温度分布图",
    subtitle: "连续温度渐变",
    description: "基于实际温度的连续色阶，冷色为低温，暖色为高温",
    items: [
      { color: "#FFFFFF", label: "极寒", range: "< -30°C" },
      { color: "#B3E5FC", label: "严寒", range: "-20°C" },
      { color: "#64B5F6", label: "寒冷", range: "-10°C" },
      { color: "#4DD0E1", label: "凉爽", range: "0°C" },
      { color: "#66BB6A", label: "温和", range: "10°C" },
      { color: "#C6D545", label: "温暖", range: "20°C" },
      { color: "#FFCA28", label: "炎热", range: "25°C" },
      { color: "#FF7043", label: "酷热", range: "30°C" },
      { color: "#D32F2F", label: "极热", range: "> 40°C" },
    ],
  },
  suitability: {
    title: "生存适宜度",
    subtitle: "选中物种的适宜度分布",
    description: "需要先选择一个物种，显示该物种在各地块的生存适宜度",
    items: [
      { color: "#10B981", label: "极佳", range: "80-100%" },
      { color: "#34D399", label: "良好", range: "60-80%" },
      { color: "#FBBF24", label: "一般", range: "40-60%" },
      { color: "#F97316", label: "较差", range: "20-40%" },
      { color: "#EF4444", label: "极差", range: "0-20%" },
      { color: "#374151", label: "不适宜", range: "物种未分布" },
    ],
  },
};

export function MapLegend({ viewMode, seaLevel = 0, temperature = 15, visible = true, hasSelectedSpecies = false }: Props) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const legend = LEGENDS[viewMode];

  if (!visible) return null;

  return (
    <div className={`map-legend-v2 ${isCollapsed ? 'collapsed' : ''}`}>
      {/* 折叠按钮 */}
      <button 
        className="legend-toggle"
        onClick={() => setIsCollapsed(!isCollapsed)}
        title={isCollapsed ? "展开图例" : "折叠图例"}
      >
        {isCollapsed ? '◀' : '▶'}
      </button>

      {!isCollapsed && (
        <>
          {/* 标题区 */}
          <div className="legend-header-v2">
            <div className="legend-title">{legend.title}</div>
            {legend.subtitle && (
              <div className="legend-subtitle">{legend.subtitle}</div>
            )}
            
            {/* 功能说明 */}
            {legend.description && (
              <div className="legend-description">{legend.description}</div>
            )}
            
            {/* 环境信息 */}
            {(viewMode === "terrain" || viewMode === "elevation") && (
              <div className="legend-env-info">
                <span className="env-item">
                  <span className="env-icon">🌊</span>
                  <span className="env-label">海平面</span>
                  <span className="env-value">{seaLevel.toFixed(0)}m</span>
                </span>
              </div>
            )}
            {viewMode === "climate" && (
              <div className="legend-env-info">
                <span className="env-item">
                  <span className="env-icon">🌡️</span>
                  <span className="env-label">全球均温</span>
                  <span className="env-value">{temperature.toFixed(1)}°C</span>
                </span>
              </div>
            )}
            
            {/* 适宜度模式的特殊提示 */}
            {viewMode === "suitability" && !hasSelectedSpecies && (
              <div className="legend-warning">
                <span className="warning-icon">⚠️</span>
                <span className="warning-text">请先在物种列表中选择一个物种</span>
              </div>
            )}
            {viewMode === "suitability" && hasSelectedSpecies && (
              <div className="legend-tip">
                <span className="tip-icon">💡</span>
                <span className="tip-text">显示选中物种的生存环境适宜度</span>
              </div>
            )}
          </div>

          {/* 图例项 */}
          <div className="legend-items-v2">
            {legend.items.map((item, index) => (
              <div key={index} className="legend-item-v2">
                <div 
                  className="legend-color-v2" 
                  style={{ backgroundColor: item.color }}
                />
                <div className="legend-text-v2">
                  <span className="legend-label-v2">{item.label}</span>
                  {item.range && (
                    <span className="legend-range">{item.range}</span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* 生物栖息指示器说明 */}
          <div className="legend-section-divider" />
          <div className="legend-habitat-section">
            <div className="legend-subtitle">生物分布</div>
            <div className="legend-habitat-items">
              {hasSelectedSpecies && (
                <div className="legend-item-v2">
                  <div className="legend-indicator" style={{ backgroundColor: "#2dd4bf" }} />
                  <span className="legend-label-v2">选中物种存在</span>
                </div>
              )}
              <div className="legend-item-v2">
                <div className="legend-indicator" style={{ backgroundColor: "#2e7d32" }} />
                <span className="legend-label-v2">多物种 (5+)</span>
              </div>
              <div className="legend-item-v2">
                <div className="legend-indicator" style={{ backgroundColor: "#66bb6a" }} />
                <span className="legend-label-v2">少量物种 (2-4)</span>
              </div>
              <div className="legend-item-v2">
                <div className="legend-indicator" style={{ backgroundColor: "#f9a825" }} />
                <span className="legend-label-v2">单一物种</span>
              </div>
            </div>
          </div>
        </>
      )}

      {/* 折叠状态下显示当前视图图标 */}
      {isCollapsed && (
        <div className="legend-collapsed-hint">
          <span className="collapsed-icon">
            {viewMode === "terrain" ? "🌍" : 
             viewMode === "terrain_type" ? "🏔️" :
             viewMode === "elevation" ? "📐" :
             viewMode === "climate" ? "🌡️" :
             viewMode === "biodiversity" ? "🧬" : "🎯"}
          </span>
        </div>
      )}
    </div>
  );
}
