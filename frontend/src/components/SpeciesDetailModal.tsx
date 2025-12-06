/**
 * SpeciesDetailModal - 物种详情弹窗组件
 * 
 * 独立弹窗展示物种详细信息，包含：
 * - 中文化的所有字段显示
 * - 美观的卡片式 UI 设计
 * - 使用 Portal 渲染到 body，确保全局居中
 */

import { useState, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  X, RefreshCw, Edit2, Save, Zap, GitBranch, GitMerge,
  Eye, BarChart3, Sparkles, Activity, Target, Dna, Shield,
  Heart, Leaf, Users, Star
} from "lucide-react";

import type { SpeciesDetail, SpeciesSnapshot } from "@/services/api.types";
import { fetchSpeciesDetail, editSpecies } from "@/services/api";
import { OrganismBlueprint } from "./OrganismBlueprint";
import { SpeciesAITab } from "./SpeciesAITab";
import "./SpeciesDetailModal.css";

// ============ 中英文字段映射表 ============
const fieldTranslations: Record<string, string> = {
  // 形态参数
  body_length_cm: "体长 (cm)",
  body_weight_g: "体重 (g)",
  body_surface_area_cm2: "体表面积 (cm²)",
  lifespan_days: "寿命 (天)",
  generation_time_days: "世代时间 (天)",
  population: "种群数量",
  metabolic_rate: "代谢率",
  growth_rate: "生长速率",
  reproduction_rate: "繁殖率",
  size: "体型",
  metabolism: "代谢",
  
  // 抽象特质（0-15范围）- 中文键（后端直接使用中文）
  耐热性: "耐热性",
  耐寒性: "耐寒性",
  耐旱性: "耐旱性",
  耐盐性: "耐盐性",
  耐酸碱性: "耐酸碱性",
  社会性: "社会性",
  免疫力: "免疫力",
  耐火性: "耐火性",
  挖掘能力: "挖掘能力",
  抗紫外线: "抗紫外线",
  解毒能力: "解毒能力",
  光照需求: "光照需求",
  氧气需求: "氧气需求",
  繁殖速度: "繁殖速度",
  运动能力: "运动能力",
  光合效率: "光合效率",
  固碳能力: "固碳能力",
  根系发达度: "根系发达度",
  保水能力: "保水能力",
  养分吸收: "养分吸收",
  多细胞程度: "多细胞程度",
  木质化程度: "木质化程度",
  种子化程度: "种子化程度",
  散布能力: "散布能力",
  
  // 英文键版本的抽象特质（兼容旧数据）
  adaptability: "适应性",
  aggression: "攻击性",
  intelligence: "智力",
  camouflage: "伪装能力",
  speed: "速度",
  endurance: "耐力",
  sensory_acuity: "感知敏锐度",
  nocturnal: "夜行性",
  heat_resistance: "耐热性",
  cold_resistance: "耐寒性",
  drought_resistance: "耐旱性",
  salinity_resistance: "耐盐性",
  sociality: "社会性",
  immunity: "免疫力",
  fire_resistance: "耐火性",
  burrowing_ability: "挖掘能力",
  uv_resistance: "抗紫外线",
  detoxification: "解毒能力",
  light_requirement: "光照需求",
  oxygen_requirement: "氧气需求",
  reproduction_speed: "繁殖速度",
  mobility: "运动能力",
  
  // 隐藏特质
  environment_sensitivity: "环境敏感度",
  mutation_rate: "突变率",
  genetic_stability: "基因稳定性",
  gene_diversity: "基因多样性",
  evolution_potential: "进化潜力",
  
  // 能力
  photosynthesis: "光合作用",
  chemosynthesis: "化学合成",
  flight: "飞行",
  swimming: "游泳",
  burrowing: "穴居",
  venom: "毒液",
  echolocation: "回声定位",
  bioluminescence: "生物发光",
  camouflage_ability: "变色伪装",
  regeneration: "再生",
  hibernation: "冬眠",
  migration: "迁徙",
  pack_hunting: "群体狩猎",
  tool_use: "工具使用",
  nitrogen_fixation: "固氮作用",
  spore_dispersal: "孢子散播",
  
  // 生态角色
  producer: "生产者",
  herbivore: "食草动物",
  carnivore: "食肉动物",
  omnivore: "杂食动物",
  decomposer: "分解者",
  scavenger: "食腐动物",
  mixotroph: "混合营养",
  detritivore: "腐食者",
  autotroph: "自养生物",
  
  // 栖息地类型
  marine: "海洋",
  freshwater: "淡水",
  coastal: "海岸",
  terrestrial: "陆地",
  aerial: "空中",
  amphibious: "两栖",
  deep_sea: "深海",
  
  // 器官系统
  locomotion: "运动系统",
  sensory: "感觉系统",
  respiratory: "呼吸系统",
  digestive: "消化系统",
  circulatory: "循环系统",
  nervous: "神经系统",
  reproductive: "生殖系统",
  integumentary: "皮肤系统",
  skeletal: "骨骼系统",
  muscular: "肌肉系统",
  metabolic: "代谢系统",
  defense: "防御系统",
  excretory: "排泄系统",
  photosynthetic: "光合器官",
  root_system: "根系",
  stem: "茎",
  protection: "保护结构",
  vascular: "维管系统",
  storage: "储存器官",
  
  // 状态
  alive: "存活",
  extinct: "灭绝",
  endangered: "濒危",
  
  // 生长形态
  aquatic: "水生",
  moss: "苔藓",
  herb: "草本",
  shrub: "灌木",
  tree: "乔木",
};

// 翻译函数
function translate(key: string): string {
  return fieldTranslations[key] || key;
}

interface Props {
  speciesId: string;
  snapshot?: SpeciesSnapshot;
  isOpen: boolean;
  onClose: () => void;
  previousPopulations?: Map<string, number>;
}

// 生态角色配置
const roleConfig: Record<string, {
  color: string;
  gradient: string;
  bgGradient: string;
  icon: string;
  label: string;
  description: string;
}> = {
  producer: {
    color: "#22c55e",
    gradient: "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)",
    bgGradient: "linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(22, 163, 74, 0.08) 100%)",
    icon: "🌿",
    label: "生产者",
    description: "光合作用的基石"
  },
  herbivore: {
    color: "#eab308",
    gradient: "linear-gradient(135deg, #eab308 0%, #ca8a04 100%)",
    bgGradient: "linear-gradient(135deg, rgba(234, 179, 8, 0.15) 0%, rgba(202, 138, 4, 0.08) 100%)",
    icon: "🦌",
    label: "食草动物",
    description: "植被的消费者"
  },
  carnivore: {
    color: "#ef4444",
    gradient: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
    bgGradient: "linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.08) 100%)",
    icon: "🦁",
    label: "食肉动物",
    description: "顶级掠食者"
  },
  omnivore: {
    color: "#f97316",
    gradient: "linear-gradient(135deg, #f97316 0%, #ea580c 100%)",
    bgGradient: "linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(234, 88, 12, 0.08) 100%)",
    icon: "🐻",
    label: "杂食动物",
    description: "适应性强的觅食者"
  },
  decomposer: {
    color: "#a855f7",
    gradient: "linear-gradient(135deg, #a855f7 0%, #9333ea 100%)",
    bgGradient: "linear-gradient(135deg, rgba(168, 85, 247, 0.15) 0%, rgba(147, 51, 234, 0.08) 100%)",
    icon: "🍄",
    label: "分解者",
    description: "生态循环的清道夫"
  },
  scavenger: {
    color: "#64748b",
    gradient: "linear-gradient(135deg, #64748b 0%, #475569 100%)",
    bgGradient: "linear-gradient(135deg, rgba(100, 116, 139, 0.15) 0%, rgba(71, 85, 105, 0.08) 100%)",
    icon: "🦅",
    label: "食腐动物",
    description: "资源的回收者"
  },
  mixotroph: {
    color: "#22d3ee",
    gradient: "linear-gradient(135deg, #22d3ee 0%, #06b6d4 100%)",
    bgGradient: "linear-gradient(135deg, rgba(34, 211, 238, 0.15) 0%, rgba(6, 182, 212, 0.08) 100%)",
    icon: "🔬",
    label: "混合营养",
    description: "既能自养又能捕食"
  },
  unknown: {
    color: "#3b82f6",
    gradient: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
    bgGradient: "linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(37, 99, 235, 0.08) 100%)",
    icon: "🧬",
    label: "未知",
    description: "神秘的生命形式"
  }
};

// 根据营养级获取生态角色
function getRoleFromTrophicLevel(trophicLevel: number | undefined): string {
  const t = trophicLevel ?? 1.0;
  if (t < 1.5) return 'producer';
  if (t < 2.0) return 'mixotroph';
  if (t < 2.8) return 'herbivore';
  if (t < 3.5) return 'omnivore';
  return 'carnivore';
}

function getRoleConfig(ecologicalRole: string | undefined, trophicLevel: number | undefined) {
  if (trophicLevel !== undefined && trophicLevel > 0) {
    const roleKey = getRoleFromTrophicLevel(trophicLevel);
    return roleConfig[roleKey] || roleConfig.unknown;
  }
  if (ecologicalRole) {
    const role = roleConfig[ecologicalRole.toLowerCase()];
    if (role) return role;
  }
  return roleConfig.unknown;
}

function formatPopulation(pop: number): string {
  if (pop >= 1_000_000) return `${(pop / 1_000_000).toFixed(1)}M`;
  if (pop >= 1_000) return `${(pop / 1_000).toFixed(1)}K`;
  return pop.toString();
}

export function SpeciesDetailModal({
  speciesId,
  snapshot,
  isOpen,
  onClose,
  previousPopulations = new Map()
}: Props) {
  const [species, setSpecies] = useState<SpeciesDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "traits" | "organs" | "lineage" | "ai">("overview");
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({ description: "", morphology: "", traits: "" });
  const [isSaving, setIsSaving] = useState(false);

  // 加载物种详情
  const loadDetail = useCallback(async () => {
    if (!speciesId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchSpeciesDetail(speciesId);
      setSpecies(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [speciesId]);

  useEffect(() => {
    if (isOpen && speciesId) {
      loadDetail();
    }
  }, [isOpen, speciesId, loadDetail]);

  // 开始编辑
  const handleStartEdit = () => {
    if (!species) return;
    setEditForm({
      description: species.description || "",
      morphology: JSON.stringify(species.morphology_stats, null, 2),
      traits: JSON.stringify(species.abstract_traits, null, 2),
    });
    setIsEditing(true);
  };

  // 保存编辑
  const handleSaveEdit = async () => {
    if (!species) return;
    
    setIsSaving(true);
    try {
      await editSpecies(species.lineage_code, {
        description: editForm.description,
        morphology: editForm.morphology,
        traits: editForm.traits,
      });
      
      await loadDetail();
      setIsEditing(false);
    } catch (err) {
      console.error("保存失败:", err);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  const role = getRoleConfig(snapshot?.ecological_role, snapshot?.trophic_level ?? species?.trophic_level);

  const modalContent = (
    <div className="sdm-overlay" onClick={onClose}>
      <div className="sdm-modal" onClick={(e) => e.stopPropagation()}>
        {/* 头部 */}
        <div className="sdm-header" style={{ background: role.bgGradient }}>
          <div className="sdm-header-accent" style={{ background: role.gradient }} />
          
          <div className="sdm-header-content">
            <div className="sdm-avatar" style={{ borderColor: `${role.color}60` }}>
              <span className="sdm-avatar-icon">{role.icon}</span>
            </div>
            
            <div className="sdm-title-block">
              {loading ? (
                <div className="sdm-loading-title">加载中...</div>
              ) : species ? (
                <>
                  <h2 className="sdm-title">{species.common_name}</h2>
                  <p className="sdm-subtitle">{species.latin_name}</p>
                  <div className="sdm-tags">
                    <span className="sdm-tag code">{species.lineage_code}</span>
                    <span className="sdm-tag role" style={{ 
                      background: `${role.color}20`,
                      color: role.color,
                      borderColor: `${role.color}40`
                    }}>
                      {role.label}
                    </span>
                    {species.status === "extinct" && (
                      <span className="sdm-tag extinct">已灭绝</span>
                    )}
                  </div>
                </>
              ) : (
                <div className="sdm-error-title">加载失败</div>
              )}
            </div>
          </div>
          
          <div className="sdm-header-actions">
            {!loading && species && !isEditing && (
              <>
                <button className="sdm-action-btn" onClick={loadDetail} title="刷新">
                  <RefreshCw size={16} />
                </button>
                <button className="sdm-action-btn" onClick={handleStartEdit} title="编辑">
                  <Edit2 size={16} />
                </button>
              </>
            )}
            <button className="sdm-close-btn" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </div>

        {/* 内容区 */}
        <div className="sdm-body">
          {loading ? (
            <div className="sdm-loading">
              <div className="sdm-spinner" />
              <span>正在加载物种档案...</span>
            </div>
          ) : error ? (
            <div className="sdm-error">
              <span className="sdm-error-icon">⚠️</span>
              <span>{error}</span>
              <button className="sdm-retry-btn" onClick={loadDetail}>
                <RefreshCw size={14} /> 重试
              </button>
            </div>
          ) : species ? (
            <>
              {/* 编辑模式 */}
              {isEditing ? (
                <div className="sdm-edit-form">
                  <div className="sdm-edit-group">
                    <label>物种描述</label>
                    <textarea
                      value={editForm.description}
                      onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                      placeholder="描述这个物种..."
                      rows={4}
                    />
                  </div>
                  <div className="sdm-edit-group">
                    <label>形态参数 (JSON)</label>
                    <textarea
                      value={editForm.morphology}
                      onChange={(e) => setEditForm({ ...editForm, morphology: e.target.value })}
                      className="mono"
                      rows={6}
                    />
                  </div>
                  <div className="sdm-edit-group">
                    <label>抽象特质 (JSON)</label>
                    <textarea
                      value={editForm.traits}
                      onChange={(e) => setEditForm({ ...editForm, traits: e.target.value })}
                      className="mono"
                      rows={6}
                    />
                  </div>
                  <div className="sdm-edit-actions">
                    <button className="sdm-btn secondary" onClick={() => setIsEditing(false)}>
                      取消
                    </button>
                    <button className="sdm-btn primary" onClick={handleSaveEdit} disabled={isSaving}>
                      {isSaving ? <span className="sdm-btn-spinner" /> : <Save size={14} />}
                      <span>保存</span>
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {/* 快速数据概览 */}
                  {snapshot && (
                    <div className="sdm-quick-stats">
                      <div className="sdm-stat-card">
                        <Users size={18} className="sdm-stat-icon" />
                        <div className="sdm-stat-content">
                          <span className="sdm-stat-label">生物量 (kg)</span>
                          <span className="sdm-stat-value">{formatPopulation(snapshot.population)}</span>
                        </div>
                      </div>
                      <div className="sdm-stat-card">
                        <Activity size={18} className="sdm-stat-icon death" />
                        <div className="sdm-stat-content">
                          <span className="sdm-stat-label">死亡率</span>
                          <span className="sdm-stat-value" style={{
                            color: snapshot.death_rate > 0.3 ? '#ef4444' : snapshot.death_rate > 0.15 ? '#f59e0b' : '#22c55e'
                          }}>
                            {(snapshot.death_rate * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <div className="sdm-stat-card">
                        <Target size={18} className="sdm-stat-icon" />
                        <div className="sdm-stat-content">
                          <span className="sdm-stat-label">生态占比</span>
                          <span className="sdm-stat-value">{(snapshot.population_share * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                      {species.trophic_level && (
                        <div className="sdm-stat-card">
                          <Dna size={18} className="sdm-stat-icon" />
                          <div className="sdm-stat-content">
                            <span className="sdm-stat-label">营养级</span>
                            <span className="sdm-stat-value">{species.trophic_level.toFixed(2)}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 标签页 */}
                  <div className="sdm-tabs">
                    {[
                      { key: "overview", label: "总览", icon: <BarChart3 size={14} /> },
                      { key: "traits", label: "能力", icon: <Target size={14} /> },
                      { key: "organs", label: "器官", icon: <Eye size={14} /> },
                      ...(species.hybrid_parent_codes?.length || species.parent_code
                        ? [{ key: "lineage", label: "血统", icon: <GitBranch size={14} /> }]
                        : []),
                      { key: "ai", label: "AI 分析", icon: <Sparkles size={14} /> }
                    ].map(({ key, label, icon }) => (
                      <button
                        key={key}
                        className={`sdm-tab ${activeTab === key ? "active" : ""}`}
                        onClick={() => setActiveTab(key as any)}
                      >
                        {icon}
                        <span>{label}</span>
                      </button>
                    ))}
                  </div>

                  {/* 标签页内容 */}
                  <div className="sdm-tab-content">
                    {activeTab === "overview" && (
                      <div className="sdm-overview">
                        {/* 描述 */}
                        <div className="sdm-desc-card">
                          <div className="sdm-desc-icon">
                            <Leaf size={16} />
                          </div>
                          <p>{species.description || `${species.common_name}是一个神秘的物种，它的故事正等待被书写...`}</p>
                        </div>

                        {/* 形态参数 - 卡片式展示 */}
                        <div className="sdm-section">
                          <div className="sdm-section-header">
                            <BarChart3 size={16} />
                            <span>形态参数</span>
                          </div>
                          <div className="sdm-morph-cards">
                            {Object.entries(species.morphology_stats || {}).slice(0, 8).map(([key, value], index) => {
                              const numValue = value as number;
                              // 为不同参数分配不同的强调色
                              const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];
                              const color = colors[index % colors.length];
                              return (
                                <div key={key} className="sdm-morph-card" style={{ '--card-color': color } as React.CSSProperties}>
                                  <div className="sdm-morph-card-value">
                                    {numValue >= 1000 ? formatPopulation(numValue) : numValue.toFixed(2)}
                                  </div>
                                  <div className="sdm-morph-card-label">{translate(key)}</div>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        {/* 特殊能力 */}
                        {species.capabilities && species.capabilities.length > 0 && (
                          <div className="sdm-section">
                            <div className="sdm-section-header">
                              <Zap size={16} />
                              <span>特殊能力</span>
                            </div>
                            <div className="sdm-capabilities">
                              {species.capabilities.map(cap => (
                                <span key={cap} className="sdm-capability">
                                  <Star size={12} />
                                  {translate(cap)}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {activeTab === "traits" && (
                      <div className="sdm-traits">
                        {/* 抽象特质 - 卡片式展示 */}
                        <div className="sdm-section">
                          <div className="sdm-section-header">
                            <Activity size={16} />
                            <span>详细特质</span>
                            <span className="sdm-section-hint">数值范围 0-15</span>
                          </div>
                          <div className="sdm-trait-cards">
                            {Object.entries(species.abstract_traits || {}).map(([key, value], index) => {
                              const numValue = value as number;
                              const getColor = () => {
                                if (numValue > 10) return '#f59e0b';
                                if (numValue < 5) return '#3b82f6';
                                return '#22c55e';
                              };
                              const getLevel = () => {
                                if (numValue > 10) return '优秀';
                                if (numValue > 7) return '良好';
                                if (numValue > 4) return '一般';
                                return '较弱';
                              };
                              return (
                                <div key={key} className="sdm-trait-card" style={{ '--trait-color': getColor() } as React.CSSProperties}>
                                  <div className="sdm-trait-card-header">
                                    <span className="sdm-trait-card-label">{translate(key)}</span>
                                    <span className="sdm-trait-card-level" style={{ color: getColor() }}>{getLevel()}</span>
                                  </div>
                                  <div className="sdm-trait-card-value" style={{ color: getColor() }}>
                                    {numValue.toFixed(1)}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    )}

                    {activeTab === "organs" && (
                      <div className="sdm-organs">
                        <div className="sdm-organs-intro">
                          <Eye size={16} />
                          <span>生理结构与器官系统可视化</span>
                        </div>
                        <OrganismBlueprint species={species} />
                      </div>
                    )}

                    {activeTab === "lineage" && (
                      <div className="sdm-lineage">
                        {species.parent_code && (
                          <div className="sdm-lineage-card">
                            <div className="sdm-lineage-icon">
                              <GitBranch size={20} />
                            </div>
                            <div className="sdm-lineage-content">
                              <span className="sdm-lineage-label">直系祖先</span>
                              <span className="sdm-lineage-code">{species.parent_code}</span>
                              <span className="sdm-lineage-turn">
                                诞生于第 <strong>{species.created_turn != null ? species.created_turn + 1 : '?'}</strong> 回合
                              </span>
                            </div>
                          </div>
                        )}

                        {species.hybrid_parent_codes && species.hybrid_parent_codes.length > 0 && (
                          <div className="sdm-lineage-card hybrid">
                            <div className="sdm-lineage-icon hybrid">
                              <GitMerge size={20} />
                            </div>
                            <div className="sdm-lineage-content">
                              <span className="sdm-lineage-label">杂交起源</span>
                              <div className="sdm-hybrid-parents">
                                {species.hybrid_parent_codes.map(code => (
                                  <span key={code} className="sdm-parent-badge">{code}</span>
                                ))}
                              </div>
                              <div className="sdm-fertility">
                                <span className="sdm-fertility-label">后代可育性</span>
                                <div className="sdm-fertility-bar">
                                  <div
                                    className="sdm-fertility-fill"
                                    style={{ width: `${(species.hybrid_fertility || 0) * 100}%` }}
                                  />
                                </div>
                                <span className="sdm-fertility-value">
                                  {((species.hybrid_fertility || 0) * 100).toFixed(0)}%
                                </span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {activeTab === "ai" && (
                      <div className="sdm-ai">
                        <SpeciesAITab
                          speciesCode={species.lineage_code}
                          speciesName={species.common_name}
                        />
                      </div>
                    )}
                  </div>
                </>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );

  // 使用 Portal 渲染到 body，确保全局居中
  return createPortal(modalContent, document.body);
}

export default SpeciesDetailModal;

