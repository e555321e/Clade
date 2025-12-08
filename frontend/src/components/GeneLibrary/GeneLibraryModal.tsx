/**
 * GeneLibraryModal - 基因库界面
 * 
 * 科幻风格的基因浏览器，支持：
 * - 目录视图：分类导航 + 卡片网格
 * - 语义星云视图：2D t-SNE 散点图
 * - 详情透镜：基因档案 + 物种分布 + 演化路径
 */

import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { Search, X, Grid3X3, Sparkles, ChevronRight, ChevronDown, Users, GitBranch, Dna, Eye, Zap, Shield, Wind, Waves, ThermometerSun, ZoomIn, ZoomOut, RotateCcw, TreeDeciduous } from "lucide-react";
import type { SpeciesSnapshot } from "@/services/api.types";
import "./GeneLibraryModal.css";

// ============ 类型定义 ============
interface GeneData {
  id: string;
  name: string;
  category: "trait" | "organ" | "capability";
  subCategory: string;
  icon: string;
  color: string;
  speciesCount: number;
  speciesList: GeneSpeciesInfo[];
  // 语义星云坐标（t-SNE降维后）
  x?: number;
  y?: number;
  // 相似基因
  similarGenes?: { id: string; name: string; similarity: number }[];
  // 演化路径
  predecessors?: string[];
  mutations?: { name: string; distance: number; description: string }[];
}

interface GeneSpeciesInfo {
  lineageCode: string;
  name: string;
  level: number;
  status: "alive" | "endangered" | "extinct";
}

interface GeneLibraryModalProps {
  isOpen: boolean;
  onClose: () => void;
  speciesList: SpeciesSnapshot[];
  onSelectSpecies?: (lineageCode: string) => void;
}

// ============ 分类配置 ============
const CATEGORY_CONFIG = {
  trait: {
    label: "特质",
    icon: "🧬",
    subCategories: [
      { key: "adaptation", label: "环境适应", icon: <ThermometerSun size={16} /> },
      { key: "metabolism", label: "代谢", icon: <Zap size={16} /> },
      { key: "behavior", label: "行为", icon: <Wind size={16} /> },
    ],
  },
  organ: {
    label: "器官",
    icon: "🫀",
    subCategories: [
      { key: "sensory", label: "感知", icon: <Eye size={16} /> },
      { key: "locomotion", label: "运动", icon: <Wind size={16} /> },
      { key: "respiratory", label: "呼吸", icon: <Waves size={16} /> },
      { key: "defense", label: "防御", icon: <Shield size={16} /> },
    ],
  },
  capability: {
    label: "能力",
    icon: "⚡",
    subCategories: [
      { key: "photosynthesis", label: "光合作用", icon: <TreeDeciduous size={16} /> },
      { key: "motion", label: "运动方式", icon: <Wind size={16} /> },
    ],
  },
};

// ============ 颜色映射 ============
const CATEGORY_COLORS: Record<string, string> = {
  adaptation: "#eab308",
  metabolism: "#22c55e",
  behavior: "#a855f7",
  sensory: "#3b82f6",
  locomotion: "#a855f7",
  respiratory: "#06b6d4",
  defense: "#f97316",
  photosynthesis: "#22c55e",
  motion: "#8b5cf6",
  default: "#38bdf8",
};

// ============ 图标映射 ============
const GENE_ICONS: Record<string, string> = {
  "耐寒性": "❄️",
  "耐热性": "🔥",
  "耐旱性": "🏜️",
  "耐盐性": "🧂",
  "光合作用": "🌱",
  "化能合成": "⚗️",
  "眼点": "👁️",
  "复眼": "🪲",
  "侧线": "〰️",
  "听觉": "👂",
  "鳍": "🐟",
  "肢体": "🦿",
  "鳃": "🫁",
  "肺": "💨",
  "鳞片": "🔷",
  "棘刺": "🦔",
  "利爪": "🦅",
  "尖牙": "🦷",
  "毒腺": "☠️",
  default: "🧬",
};

// ============ 主组件 ============
export function GeneLibraryModal({ isOpen, onClose, speciesList, onSelectSpecies }: GeneLibraryModalProps) {
  const [viewMode, setViewMode] = useState<"catalog" | "nebula">("catalog");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedGene, setSelectedGene] = useState<GeneData | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(["trait", "organ"]));

  // 从物种数据中提取基因信息
  const geneData = useMemo(() => extractGeneData(speciesList), [speciesList]);

  // 过滤后的基因列表
  const filteredGenes = useMemo(() => {
    let genes = geneData;
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      genes = genes.filter(g => g.name.toLowerCase().includes(query));
    }
    
    if (selectedCategory) {
      genes = genes.filter(g => g.subCategory === selectedCategory || g.category === selectedCategory);
    }
    
    return genes;
  }, [geneData, searchQuery, selectedCategory]);

  // 分类统计
  const categoryStats = useMemo(() => {
    const stats: Record<string, number> = {};
    for (const gene of geneData) {
      stats[gene.category] = (stats[gene.category] || 0) + 1;
      stats[gene.subCategory] = (stats[gene.subCategory] || 0) + 1;
    }
    return stats;
  }, [geneData]);

  const toggleGroup = useCallback((group: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(group)) {
        next.delete(group);
      } else {
        next.add(group);
      }
      return next;
    });
  }, []);

  const handleGeneSelect = useCallback((gene: GeneData) => {
    setSelectedGene(gene);
  }, []);

  const handleSpeciesClick = useCallback((lineageCode: string) => {
    onSelectSpecies?.(lineageCode);
    onClose();
  }, [onSelectSpecies, onClose]);

  if (!isOpen) return null;

  return (
    <div className="gl-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="gl-modal">
        {/* 顶部栏 */}
        <header className="gl-header">
          <div className="gl-logo">
            <div className="gl-logo-icon">🧬</div>
            <div>
              <div className="gl-title">基因库</div>
              <div className="gl-title-sub">Gene Library</div>
            </div>
          </div>

          {/* 视图切换 */}
          <div className="gl-view-tabs">
            <button
              className={`gl-view-tab ${viewMode === "catalog" ? "active" : ""}`}
              onClick={() => setViewMode("catalog")}
            >
              <Grid3X3 size={16} />
              <span>目录视图</span>
            </button>
            <button
              className={`gl-view-tab ${viewMode === "nebula" ? "active" : ""}`}
              onClick={() => setViewMode("nebula")}
            >
              <Sparkles size={16} />
              <span>语义星云</span>
            </button>
          </div>

          {/* 搜索框 */}
          <div className="gl-search">
            <Search size={16} className="gl-search-icon" />
            <input
              type="text"
              className="gl-search-input"
              placeholder="搜索基因..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <button className="gl-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </header>

        {/* 主内容区 */}
        <div className="gl-content">
          {viewMode === "catalog" ? (
            <CatalogView
              genes={filteredGenes}
              categoryStats={categoryStats}
              selectedCategory={selectedCategory}
              expandedGroups={expandedGroups}
              selectedGene={selectedGene}
              onSelectCategory={setSelectedCategory}
              onToggleGroup={toggleGroup}
              onSelectGene={handleGeneSelect}
            />
          ) : (
            <SemanticNebulaView
              genes={filteredGenes}
              selectedGene={selectedGene}
              onSelectGene={handleGeneSelect}
            />
          )}

          {/* 详情透镜 */}
          <DetailLens
            gene={selectedGene}
            onClose={() => setSelectedGene(null)}
            onSpeciesClick={handleSpeciesClick}
          />
        </div>
      </div>
    </div>
  );
}

// ============ 目录视图 ============
interface CatalogViewProps {
  genes: GeneData[];
  categoryStats: Record<string, number>;
  selectedCategory: string | null;
  expandedGroups: Set<string>;
  selectedGene: GeneData | null;
  onSelectCategory: (cat: string | null) => void;
  onToggleGroup: (group: string) => void;
  onSelectGene: (gene: GeneData) => void;
}

function CatalogView({
  genes,
  categoryStats,
  selectedCategory,
  expandedGroups,
  selectedGene,
  onSelectCategory,
  onToggleGroup,
  onSelectGene,
}: CatalogViewProps) {
  const [sortBy, setSortBy] = useState<"count" | "name">("count");

  const sortedGenes = useMemo(() => {
    const sorted = [...genes];
    if (sortBy === "count") {
      sorted.sort((a, b) => b.speciesCount - a.speciesCount);
    } else {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    }
    return sorted;
  }, [genes, sortBy]);

  return (
    <div className="gl-catalog">
      {/* 左侧导航 */}
      <nav className="gl-nav">
        <div className="gl-nav-title">分类导航</div>
        
        {Object.entries(CATEGORY_CONFIG).map(([key, config]) => (
          <div key={key} className="gl-nav-group">
            <button
              className={`gl-nav-group-header ${selectedCategory === key ? "active" : ""}`}
              onClick={() => {
                onToggleGroup(key);
                onSelectCategory(selectedCategory === key ? null : key);
              }}
            >
              {expandedGroups.has(key) ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <span className="gl-nav-group-icon">{config.icon}</span>
              <span>{config.label}</span>
              <span className="gl-nav-group-count">{categoryStats[key] || 0}</span>
            </button>
            
            {expandedGroups.has(key) && (
              <div className="gl-nav-items">
                {config.subCategories.map((sub) => (
                  <button
                    key={sub.key}
                    className={`gl-nav-item ${selectedCategory === sub.key ? "active" : ""}`}
                    onClick={() => onSelectCategory(selectedCategory === sub.key ? null : sub.key)}
                  >
                    {sub.icon}
                    <span style={{ marginLeft: 8 }}>{sub.label}</span>
                    <span className="gl-nav-group-count" style={{ marginLeft: "auto" }}>
                      {categoryStats[sub.key] || 0}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* 基因网格 */}
      <div className="gl-grid-container">
        <div className="gl-grid-header">
          <div className="gl-grid-title">
            {selectedCategory ? 
              CATEGORY_CONFIG[selectedCategory as keyof typeof CATEGORY_CONFIG]?.label || 
              Object.values(CATEGORY_CONFIG).flatMap(c => c.subCategories).find(s => s.key === selectedCategory)?.label || 
              "所有基因" 
              : "所有基因"}
            <span className="gl-grid-count">{sortedGenes.length} 个基因</span>
          </div>
          <div className="gl-grid-sort">
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as "count" | "name")}>
              <option value="count">按物种数量</option>
              <option value="name">按名称</option>
            </select>
          </div>
        </div>

        <div className="gl-grid">
          {sortedGenes.map((gene, index) => (
            <GeneCard
              key={gene.id}
              gene={gene}
              isSelected={selectedGene?.id === gene.id}
              onClick={() => onSelectGene(gene)}
              style={{ animationDelay: `${index * 30}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ============ 基因卡片 ============
interface GeneCardProps {
  gene: GeneData;
  isSelected: boolean;
  onClick: () => void;
  style?: React.CSSProperties;
}

function GeneCard({ gene, isSelected, onClick, style }: GeneCardProps) {
  const maxCount = 20; // 假设最大物种数量
  const fillWidth = Math.min(100, (gene.speciesCount / maxCount) * 100);

  return (
    <div
      className={`gl-gene-card ${isSelected ? "selected" : ""}`}
      onClick={onClick}
      style={{
        ...style,
        "--card-accent": gene.color,
        animation: "gl-slide-up 0.4s ease-out backwards",
      } as React.CSSProperties}
    >
      <div className="gl-gene-icon" style={{ color: gene.color }}>
        {gene.icon}
      </div>
      <div className="gl-gene-name">{gene.name}</div>
      <div className="gl-gene-stats">
        <div className="gl-gene-bar">
          <div
            className="gl-gene-bar-fill"
            style={{ width: `${fillWidth}%`, background: gene.color }}
          />
        </div>
        <span className="gl-gene-count">{gene.speciesCount}种</span>
      </div>
    </div>
  );
}

// ============ 语义星云视图 ============
interface SemanticNebulaViewProps {
  genes: GeneData[];
  selectedGene: GeneData | null;
  onSelectGene: (gene: GeneData) => void;
}

function SemanticNebulaView({ genes, selectedGene, onSelectGene }: SemanticNebulaViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  // 为基因生成 2D 坐标（模拟 t-SNE）
  const genesWithCoords = useMemo(() => {
    return genes.map((gene, i) => {
      // 基于分类和索引生成伪随机坐标
      const categoryOffset = {
        trait: { x: 0.2, y: 0.3 },
        organ: { x: 0.6, y: 0.5 },
        capability: { x: 0.3, y: 0.7 },
      };
      const base = categoryOffset[gene.category] || { x: 0.5, y: 0.5 };
      const hash = gene.id.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
      
      return {
        ...gene,
        x: (base.x + (Math.sin(hash) * 0.25 + Math.cos(i) * 0.1)) * 100,
        y: (base.y + (Math.cos(hash) * 0.25 + Math.sin(i) * 0.1)) * 100,
      };
    });
  }, [genes]);

  // 鼠标事件处理
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true);
      dragStart.current = { x: e.clientX - offset.x, y: e.clientY - offset.y };
    }
  }, [offset]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y,
      });
    }
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(z => Math.min(3, Math.max(0.5, z * delta)));
  }, []);

  const resetView = useCallback(() => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  }, []);

  return (
    <div className="gl-nebula">
      {/* 星云背景 */}
      <div className="gl-nebula-bg">
        <div className="gl-nebula-cloud" />
        <div className="gl-nebula-cloud" />
        <div className="gl-nebula-cloud" />
      </div>

      {/* 可交互画布 */}
      <div
        ref={containerRef}
        className="gl-nebula-canvas"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        style={{
          transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`,
          transformOrigin: "center center",
        }}
      >
        {genesWithCoords.map((gene) => {
          const size = 8 + Math.min(12, gene.speciesCount * 2);
          return (
            <div
              key={gene.id}
              className="gl-nebula-point"
              style={{
                left: `${gene.x}%`,
                top: `${gene.y}%`,
                "--point-size": `${size}px`,
                "--point-color": gene.color,
              } as React.CSSProperties}
              onClick={(e) => {
                e.stopPropagation();
                onSelectGene(gene);
              }}
            >
              <div className="gl-nebula-point-core" />
              <div className="gl-nebula-tooltip">
                <div className="gl-nebula-tooltip-name">{gene.icon} {gene.name}</div>
                <div className="gl-nebula-tooltip-count">{gene.speciesCount} 个物种</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 控制栏 */}
      <div className="gl-nebula-controls">
        <div className="gl-nebula-zoom">
          <button className="gl-nebula-zoom-btn" onClick={() => setZoom(z => Math.min(3, z * 1.2))}>
            <ZoomIn size={16} />
          </button>
          <span className="gl-nebula-zoom-level">{Math.round(zoom * 100)}%</span>
          <button className="gl-nebula-zoom-btn" onClick={() => setZoom(z => Math.max(0.5, z / 1.2))}>
            <ZoomOut size={16} />
          </button>
          <button className="gl-nebula-zoom-btn" onClick={resetView}>
            <RotateCcw size={16} />
          </button>
        </div>

        <div className="gl-nebula-legend">
          <div className="gl-nebula-legend-item">
            <div className="gl-nebula-legend-dot" style={{ background: "#ef4444" }} />
            <span>攻击</span>
          </div>
          <div className="gl-nebula-legend-item">
            <div className="gl-nebula-legend-dot" style={{ background: "#22c55e" }} />
            <span>代谢</span>
          </div>
          <div className="gl-nebula-legend-item">
            <div className="gl-nebula-legend-dot" style={{ background: "#3b82f6" }} />
            <span>感知</span>
          </div>
          <div className="gl-nebula-legend-item">
            <div className="gl-nebula-legend-dot" style={{ background: "#a855f7" }} />
            <span>运动</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ 详情透镜 ============
interface DetailLensProps {
  gene: GeneData | null;
  onClose: () => void;
  onSpeciesClick: (lineageCode: string) => void;
}

function DetailLens({ gene, onClose, onSpeciesClick }: DetailLensProps) {
  const [showAllSpecies, setShowAllSpecies] = useState(false);

  if (!gene) {
    return (
      <div className="gl-lens">
        <div className="gl-lens-empty">
          <div className="gl-lens-empty-icon">🔍</div>
          <div className="gl-lens-empty-title">选择一个基因</div>
          <div className="gl-lens-empty-hint">点击左侧基因卡片查看详细信息</div>
        </div>
      </div>
    );
  }

  const displayedSpecies = showAllSpecies 
    ? gene.speciesList 
    : gene.speciesList.slice(0, 5);

  const coveragePercent = Math.round((gene.speciesCount / Math.max(1, gene.speciesCount + 10)) * 100);

  // 模拟等级分布
  const levelDistribution = [
    { label: "Lv.1-2", count: Math.ceil(gene.speciesCount * 0.25), percent: 25 },
    { label: "Lv.3-4", count: Math.ceil(gene.speciesCount * 0.5), percent: 50 },
    { label: "Lv.5+", count: Math.ceil(gene.speciesCount * 0.25), percent: 25 },
  ];

  return (
    <div className="gl-lens">
      {/* 头部：基因档案 */}
      <div className="gl-lens-header">
        <div className="gl-lens-gene-info">
          <div className="gl-lens-icon" style={{ "--glow-color": gene.color } as React.CSSProperties}>
            {gene.icon}
          </div>
          <div className="gl-lens-title-block">
            <div className="gl-lens-name">{gene.name}</div>
            <div className="gl-lens-name-en">{gene.id}</div>
            
            {/* 语义标签 */}
            <div className="gl-lens-tags">
              <span className="gl-lens-tag">#{gene.category === "trait" ? "特质" : gene.category === "organ" ? "器官" : "能力"}</span>
              <span className="gl-lens-tag">#{gene.subCategory}</span>
            </div>
          </div>
        </div>

        {/* 相似基因 */}
        {gene.similarGenes && gene.similarGenes.length > 0 && (
          <div className="gl-lens-similar">
            <div className="gl-lens-similar-title">
              <Dna size={14} />
              相似基因
            </div>
            <div className="gl-lens-similar-items">
              {gene.similarGenes.slice(0, 3).map((sim) => (
                <div key={sim.id} className="gl-lens-similar-item">
                  <div className="gl-lens-similar-name">{sim.name}</div>
                  <div className="gl-lens-similar-score">{(sim.similarity * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 内容：物种分布 & 演化路径 */}
      <div className="gl-lens-body">
        {/* 物种分布 */}
        <div className="gl-lens-section">
          <div className="gl-lens-section-header">
            <Users size={16} className="gl-lens-section-icon" />
            物种分布
          </div>

          {/* 覆盖率 */}
          <div className="gl-lens-coverage">
            <div className="gl-lens-coverage-bar">
              <div 
                className="gl-lens-coverage-fill" 
                style={{ width: `${coveragePercent}%` }} 
              />
            </div>
            <div className="gl-lens-coverage-text">
              <span>当前世界覆盖率</span>
              <span className="gl-lens-coverage-pct">{coveragePercent}%</span>
            </div>
          </div>

          {/* 等级分布 */}
          <div className="gl-lens-levels">
            {levelDistribution.map((level) => (
              <div key={level.label} className="gl-lens-level-row">
                <span className="gl-lens-level-label">{level.label}</span>
                <div className="gl-lens-level-bar">
                  <div 
                    className="gl-lens-level-fill" 
                    style={{ width: `${level.percent}%` }} 
                  />
                </div>
                <span className="gl-lens-level-count">{level.count}</span>
              </div>
            ))}
          </div>

          {/* 物种列表 */}
          <div className="gl-lens-species-list">
            {displayedSpecies.map((sp) => (
              <div 
                key={sp.lineageCode} 
                className="gl-lens-species-item"
                onClick={() => onSpeciesClick(sp.lineageCode)}
              >
                <div className={`gl-lens-species-status ${sp.status}`} />
                <span className="gl-lens-species-name">{sp.name}</span>
                <span className="gl-lens-species-level">Lv.{sp.level}</span>
                <ChevronRight size={14} className="gl-lens-species-arrow" />
              </div>
            ))}
          </div>

          {gene.speciesList.length > 5 && (
            <button 
              className="gl-lens-show-all"
              onClick={() => setShowAllSpecies(!showAllSpecies)}
            >
              {showAllSpecies ? "收起" : `显示全部 ${gene.speciesList.length} 个`}
            </button>
          )}
        </div>

        {/* 演化路径 */}
        <div className="gl-lens-section">
          <div className="gl-lens-section-header">
            <GitBranch size={16} className="gl-lens-section-icon" />
            演化路径
          </div>

          <div className="gl-lens-evolution">
            {/* 前置基因路径 */}
            {gene.predecessors && gene.predecessors.length > 0 && (
              <div className="gl-lens-evo-path">
                {gene.predecessors.map((pred, i) => (
                  <span key={pred}>
                    <span className="gl-lens-evo-node">{pred}</span>
                    {i < gene.predecessors!.length - 1 && (
                      <span className="gl-lens-evo-arrow"> → </span>
                    )}
                  </span>
                ))}
                <span className="gl-lens-evo-arrow"> → </span>
                <span className="gl-lens-evo-node current">{gene.name}</span>
              </div>
            )}

            {!gene.predecessors?.length && (
              <div className="gl-lens-evo-path">
                <span className="gl-lens-evo-node current">{gene.name}</span>
                <span style={{ marginLeft: 8, color: "var(--gl-text-muted)", fontSize: "0.75rem" }}>
                  (原始基因)
                </span>
              </div>
            )}

            <div className="gl-lens-evo-confidence">
              置信度：85% (基于 {gene.speciesCount} 个演化案例)
            </div>

            {/* 潜在变异 */}
            {gene.mutations && gene.mutations.length > 0 && (
              <>
                <div className="gl-lens-section-header" style={{ marginTop: 12, marginBottom: 8 }}>
                  <Sparkles size={14} className="gl-lens-section-icon" />
                  潜在变异
                </div>
                <div className="gl-lens-mutations">
                  {gene.mutations.map((mut) => (
                    <div key={mut.name} className="gl-lens-mutation-item">
                      <span className="gl-lens-mutation-distance">{mut.distance.toFixed(2)}</span>
                      <span className="gl-lens-mutation-name">{mut.name}</span>
                      <span className="gl-lens-mutation-badge">{mut.description}</span>
                    </div>
                  ))}
                </div>

                {/* 多样性半径 */}
                <div className="gl-lens-radius">
                  <div className="gl-lens-radius-label">当前平均多样性半径：0.28</div>
                  <div className="gl-lens-radius-bar">
                    <div className="gl-lens-radius-fill" style={{ width: "70%" }} />
                    <div className="gl-lens-radius-marker" style={{ left: "28%" }} />
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="gl-lens-actions">
          <button className="gl-lens-action-btn">
            <TreeDeciduous size={16} />
            在演化树中查看
          </button>
        </div>
      </div>
    </div>
  );
}

// ============ 数据提取函数 ============
function extractGeneData(speciesList: SpeciesSnapshot[]): GeneData[] {
  const geneMap = new Map<string, GeneData>();

  for (const species of speciesList) {
    // 提取特质
    if (species.abstract_traits) {
      for (const [traitName, traitValue] of Object.entries(species.abstract_traits)) {
        const id = `trait_${traitName}`;
        if (!geneMap.has(id)) {
          geneMap.set(id, {
            id,
            name: traitName,
            category: "trait",
            subCategory: inferTraitSubCategory(traitName),
            icon: GENE_ICONS[traitName] || GENE_ICONS.default,
            color: CATEGORY_COLORS[inferTraitSubCategory(traitName)] || CATEGORY_COLORS.default,
            speciesCount: 0,
            speciesList: [],
            similarGenes: generateSimilarGenes(traitName),
            predecessors: generatePredecessors(traitName),
            mutations: generateMutations(traitName),
          });
        }
        const gene = geneMap.get(id)!;
        gene.speciesCount++;
        gene.speciesList.push({
          lineageCode: species.lineage_code,
          name: species.common_name,
          level: Math.round(traitValue as number),
          status: species.status === "alive" ? "alive" : "extinct",
        });
      }
    }

    // 提取器官
    if (species.organs) {
      for (const [category, organData] of Object.entries(species.organs)) {
        if (!organData) continue;
        const organ = organData as { type?: string };
        const organName = organ.type || category;
        const id = `organ_${category}_${organName}`;
        
        if (!geneMap.has(id)) {
          geneMap.set(id, {
            id,
            name: organName,
            category: "organ",
            subCategory: category,
            icon: GENE_ICONS[organName] || GENE_ICONS.default,
            color: CATEGORY_COLORS[category] || CATEGORY_COLORS.default,
            speciesCount: 0,
            speciesList: [],
            similarGenes: generateSimilarGenes(organName),
            predecessors: generatePredecessors(organName),
            mutations: generateMutations(organName),
          });
        }
        const gene = geneMap.get(id)!;
        gene.speciesCount++;
        gene.speciesList.push({
          lineageCode: species.lineage_code,
          name: species.common_name,
          level: 3, // 器官默认等级
          status: species.status === "alive" ? "alive" : "extinct",
        });
      }
    }

    // 提取能力
    if (species.capabilities) {
      for (const cap of species.capabilities) {
        const id = `cap_${cap}`;
        if (!geneMap.has(id)) {
          geneMap.set(id, {
            id,
            name: cap,
            category: "capability",
            subCategory: inferCapabilitySubCategory(cap),
            icon: GENE_ICONS[cap] || GENE_ICONS.default,
            color: CATEGORY_COLORS[inferCapabilitySubCategory(cap)] || CATEGORY_COLORS.default,
            speciesCount: 0,
            speciesList: [],
            similarGenes: [],
            predecessors: [],
            mutations: [],
          });
        }
        const gene = geneMap.get(id)!;
        gene.speciesCount++;
        gene.speciesList.push({
          lineageCode: species.lineage_code,
          name: species.common_name,
          level: 1,
          status: species.status === "alive" ? "alive" : "extinct",
        });
      }
    }
  }

  return Array.from(geneMap.values());
}

function inferTraitSubCategory(traitName: string): string {
  if (traitName.includes("耐") || traitName.includes("适应")) return "adaptation";
  if (traitName.includes("代谢") || traitName.includes("消化")) return "metabolism";
  return "behavior";
}

function inferCapabilitySubCategory(cap: string): string {
  if (cap.includes("光合") || cap.includes("合成")) return "photosynthesis";
  return "motion";
}

function generateSimilarGenes(name: string): { id: string; name: string; similarity: number }[] {
  // 模拟相似基因
  const similar = [
    { id: "sim1", name: `${name}(变体)`, similarity: 0.92 },
    { id: "sim2", name: `原始${name}`, similarity: 0.85 },
  ];
  return similar;
}

function generatePredecessors(name: string): string[] {
  // 模拟前置基因
  if (name.includes("复眼")) return ["感光细胞", "眼斑"];
  if (name.includes("肺")) return ["皮肤呼吸", "简单气囊"];
  return [];
}

function generateMutations(name: string): { name: string; distance: number; description: string }[] {
  // 模拟潜在变异
  if (name.includes("眼") || name.includes("视")) {
    return [
      { name: "红外视觉", distance: 0.12, description: "热感知" },
      { name: "动态捕捉眼", distance: 0.18, description: "高帧率" },
      { name: "紫外视觉", distance: 0.23, description: "UV感知" },
    ];
  }
  if (name.includes("耐")) {
    return [
      { name: `极端${name}`, distance: 0.15, description: "强化版" },
      { name: `${name}恢复`, distance: 0.20, description: "快速适应" },
    ];
  }
  return [];
}

export default GeneLibraryModal;


