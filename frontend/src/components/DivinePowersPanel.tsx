/**
 * DivinePowersPanel - 神力进阶系统面板
 * 包含四大子系统：神格专精、信仰、神迹、预言赌注
 */
import { useState, useEffect, useCallback } from "react";
import { 
  Sparkles, Crown, Shield, Zap, Leaf, 
  Users, Star, Flame, Target, Dice6,
  ChevronRight, Lock, Check, AlertTriangle
} from "lucide-react";
import { AnalysisPanel, AnalysisSection, ActionButton, StatCard, EmptyState } from "./common/AnalysisPanel";
import { dispatchEnergyChanged } from "./EnergyBar";

// ==================== 类型定义 ====================

interface PathInfo {
  path: string;
  name: string;
  icon: string;
  description: string;
  passive_bonus: string;
  color: string;
  skills: string[];
}

interface CurrentPath extends PathInfo {
  level: number;
  experience: number;
  next_level_exp: number;
  unlocked_skills: string[];
  secondary_path: string | null;
}

interface SkillInfo {
  id: string;
  name: string;
  path: string;
  description: string;
  cost: number;
  cooldown: number;
  unlock_level: number;
  icon: string;
  unlocked: boolean;
  uses: number;
  is_current_path: boolean;
}

interface Follower {
  lineage_code: string;
  common_name: string;
  faith_value: number;
  turns_as_follower: number;
  is_blessed: boolean;
  is_sanctified: boolean;
  contribution_per_turn: number;
  status: string;
}

interface FaithSummary {
  total_followers: number;
  total_faith: number;
  faith_bonus_per_turn: number;
  followers: Follower[];
}

interface MiracleInfo {
  id: string;
  name: string;
  icon: string;
  description: string;
  cost: number;
  cooldown: number;
  charge_turns: number;
  one_time: boolean;
  current_cooldown: number;
  is_charging: boolean;
  charge_progress: number;
  available: boolean;
}

interface WagerType {
  type: string;
  name: string;
  icon: string;
  description: string;
  min_bet: number;
  max_bet: number;
  duration: number;
  multiplier: number;
}

interface ActiveWager {
  id: string;
  wager_type: string;
  target_species: string;
  secondary_species: string | null;
  bet_amount: number;
  start_turn: number;
  end_turn: number;
  predicted_outcome: string;
}

interface WagerSummary {
  active_wagers: ActiveWager[];
  total_bet: number;
  total_won: number;
  total_lost: number;
  net_profit: number;
  consecutive_wins: number;
  consecutive_losses: number;
  faith_shaken_turns: number;
  wager_types: WagerType[];
}

interface DivineStatus {
  path: CurrentPath | null;
  available_paths: PathInfo[] | null;
  faith: FaithSummary;
  miracles: MiracleInfo[];
  charging_miracle: string | null;
  wagers: WagerSummary;
  stats: {
    total_skills_used: number;
    total_miracles_cast: number;
  };
}

interface Props {
  onClose: () => void;
}

type TabType = "path" | "faith" | "miracles" | "wagers";

// 神格配色映射
const PATH_COLORS: Record<string, string> = {
  creator: "#22c55e",
  guardian: "#3b82f6", 
  chaos: "#ef4444",
  ecology: "#a855f7",
};

const PATH_ICONS: Record<string, React.ReactNode> = {
  creator: <Leaf size={20} />,
  guardian: <Shield size={20} />,
  chaos: <Zap size={20} />,
  ecology: <Sparkles size={20} />,
};

// ==================== 主组件 ====================

export function DivinePowersPanel({ onClose }: Props) {
  const [status, setStatus] = useState<DivineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>("path");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/divine/status");
      const data = await res.json();
      setStatus(data);
    } catch (e) {
      console.error("获取神力状态失败:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleChoosePath = async (path: string) => {
    setActionLoading(true);
    try {
      const res = await fetch("/api/divine/path/choose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message || "神格选择成功！");
        fetchStatus();
      } else {
        alert(data.detail || "选择神格失败");
      }
    } catch (e) {
      console.error(e);
      alert("请求失败，请检查网络连接");
    } finally {
      setActionLoading(false);
    }
  };

  const handleUseSkill = async (skillId: string) => {
    // 需要目标的技能
    const needsTarget = [
      "ancestor_blessing", "life_shelter", "revival_light",
      "divine_speciation", "chaos_mutation",
    ];
    
    let target: string | null = null;
    if (needsTarget.includes(skillId)) {
      target = prompt("请输入目标物种代码:");
      if (!target) return; // 用户取消
    }
    
    setActionLoading(true);
    try {
      const res = await fetch("/api/divine/skill/use", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_id: skillId, target }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.result?.details || "技能释放成功");
        fetchStatus();
        dispatchEnergyChanged();
      } else {
        alert(data.detail || "技能释放失败");
      }
    } catch (e) {
      console.error(e);
      alert("请求失败，请检查网络连接");
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecuteMiracle = async (miracleId: string) => {
    // miracle_evolution 需要目标物种
    let target: string | null = null;
    if (miracleId === "miracle_evolution") {
      target = prompt("请输入目标物种代码（奇迹进化的起点）:");
      if (!target) return;
    }
    
    setActionLoading(true);
    try {
      const res = await fetch("/api/divine/miracle/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ miracle_id: miracleId, target }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.result?.details || "神迹释放成功");
        fetchStatus();
        dispatchEnergyChanged();
      } else {
        alert(data.detail || "神迹释放失败");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  const handlePlaceWager = async (wagerType: string) => {
    const target = prompt("请输入目标物种代码:");
    if (!target) return;
    
    const betStr = prompt("请输入下注能量 (10-60):");
    const bet = parseInt(betStr || "0", 10);
    if (!bet) return;

    let secondary = null;
    let predicted = "";
    if (wagerType === "duel") {
      secondary = prompt("请输入对决的第二物种代码:");
      predicted = prompt("预测获胜者代码:") || target;
    }

    setActionLoading(true);
    try {
      const res = await fetch("/api/divine/wager/place", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          wager_type: wagerType,
          target_species: target,
          bet_amount: bet,
          secondary_species: secondary,
          predicted_outcome: predicted,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(`${data.message}\n潜在回报: ${data.potential_return} 能量`);
        fetchStatus();
        dispatchEnergyChanged();
      } else {
        alert(data.detail || "下注失败");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  const accentColor = status?.path ? PATH_COLORS[status.path.path] || "#f59e0b" : "#f59e0b";

  if (loading) {
    return (
      <AnalysisPanel
        title="神力进阶"
        icon={<Sparkles size={20} />}
        accentColor="#f59e0b"
        onClose={onClose}
        size="large"
      >
        <EmptyState
          icon={<Sparkles />}
          title="加载中..."
          description="正在获取神力系统状态"
        />
      </AnalysisPanel>
    );
  }

  if (!status) {
    return (
      <AnalysisPanel
        title="神力进阶"
        icon={<Sparkles size={20} />}
        accentColor="#f59e0b"
        onClose={onClose}
        size="large"
      >
        <EmptyState
          icon={<AlertTriangle />}
          title="加载失败"
          description="无法获取神力系统状态"
        />
      </AnalysisPanel>
    );
  }

  return (
    <AnalysisPanel
      title="神力进阶"
      icon={<Sparkles size={20} />}
      accentColor={accentColor}
      onClose={onClose}
      size="large"
      showMaximize
      headerExtra={
        status.path && (
          <div className="header-path-badge" style={{ 
            background: `linear-gradient(135deg, ${accentColor}20, ${accentColor}10)`,
            border: `1px solid ${accentColor}40`,
            color: accentColor,
          }}>
            {status.path.icon} {status.path.name} Lv.{status.path.level}
          </div>
        )
      }
    >
      <div className="divine-powers-content">
        {/* 标签页导航 */}
        <div className="divine-tabs">
          {[
            { key: "path", label: "神格", icon: <Crown size={16} /> },
            { key: "faith", label: "信仰", icon: <Users size={16} /> },
            { key: "miracles", label: "神迹", icon: <Star size={16} /> },
            { key: "wagers", label: "预言", icon: <Dice6 size={16} /> },
          ].map((tab) => (
            <button
              key={tab.key}
              className={`divine-tab ${activeTab === tab.key ? "active" : ""}`}
              onClick={() => setActiveTab(tab.key as TabType)}
              style={{
                "--tab-color": activeTab === tab.key ? accentColor : "transparent",
              } as React.CSSProperties}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* 标签页内容 */}
        <div className="divine-tab-content">
          {activeTab === "path" && (
            <PathTab
              status={status}
              onChoosePath={handleChoosePath}
              onUseSkill={handleUseSkill}
              loading={actionLoading}
            />
          )}
          {activeTab === "faith" && (
            <FaithTab status={status} onRefresh={fetchStatus} />
          )}
          {activeTab === "miracles" && (
            <MiraclesTab
              status={status}
              onExecute={handleExecuteMiracle}
              loading={actionLoading}
            />
          )}
          {activeTab === "wagers" && (
            <WagersTab
              status={status}
              onPlaceWager={handlePlaceWager}
              onRefresh={fetchStatus}
              loading={actionLoading}
            />
          )}
        </div>
      </div>

      <style>{`
        .divine-powers-content {
          display: flex;
          flex-direction: column;
          height: 100%;
          padding: 20px;
          gap: 20px;
        }

        .header-path-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border-radius: 20px;
          font-size: 0.85rem;
          font-weight: 600;
        }

        .divine-tabs {
          display: flex;
          gap: 8px;
          padding: 6px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 14px;
        }

        .divine-tab {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 12px 16px;
          background: transparent;
          border: none;
          border-radius: 10px;
          color: rgba(255, 255, 255, 0.5);
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.25s ease;
          position: relative;
        }

        .divine-tab:hover {
          color: rgba(255, 255, 255, 0.8);
          background: rgba(255, 255, 255, 0.03);
        }

        .divine-tab.active {
          color: #fff;
          background: linear-gradient(135deg, 
            color-mix(in srgb, var(--tab-color) 20%, transparent),
            color-mix(in srgb, var(--tab-color) 10%, transparent)
          );
          box-shadow: 0 0 20px color-mix(in srgb, var(--tab-color) 30%, transparent);
        }

        .divine-tab.active::after {
          content: '';
          position: absolute;
          bottom: -6px;
          left: 50%;
          transform: translateX(-50%);
          width: 20px;
          height: 3px;
          background: var(--tab-color);
          border-radius: 2px;
        }

        .divine-tab-content {
          flex: 1;
          overflow-y: auto;
          overflow-x: hidden;
        }
      `}</style>
    </AnalysisPanel>
  );
}

// ==================== 神格标签页 ====================

function PathTab({
  status,
  onChoosePath,
  onUseSkill,
  loading,
}: {
  status: DivineStatus;
  onChoosePath: (path: string) => void;
  onUseSkill: (skillId: string) => void;
  loading: boolean;
}) {
  const [skills, setSkills] = useState<SkillInfo[]>([]);

  useEffect(() => {
    fetch("/api/divine/skills")
      .then((r) => r.json())
      .then((data) => setSkills(data.skills || []))
      .catch(console.error);
  }, [status]);

  // 未选择神格 - 选择界面
  if (!status.path && status.available_paths) {
    return (
      <div className="path-selection">
        <div className="selection-header">
          <h3>选择你的神格</h3>
          <p>踏上神力之路，选择一条专精路线，解锁独特能力与加成</p>
        </div>
        
        <div className="paths-grid">
          {status.available_paths.map((path) => (
            <div
              key={path.path}
              className="path-option-card"
              style={{ "--path-color": PATH_COLORS[path.path] } as React.CSSProperties}
              onClick={() => !loading && onChoosePath(path.path)}
            >
              <div className="path-option-glow" />
              <div className="path-option-icon">
                {PATH_ICONS[path.path] || <Sparkles size={28} />}
              </div>
              <div className="path-option-name">{path.name}</div>
              <div className="path-option-desc">{path.description}</div>
              <div className="path-option-bonus">
                <Flame size={14} />
                <span>{path.passive_bonus}</span>
              </div>
              <div className="path-option-skills">
                {path.skills.map((skill, i) => (
                  <span key={i} className="skill-tag">{skill}</span>
                ))}
              </div>
              <div className="path-option-select">
                <ChevronRight size={18} />
                <span>选择此神格</span>
              </div>
            </div>
          ))}
        </div>

        <style>{`
          .path-selection {
            display: flex;
            flex-direction: column;
            gap: 24px;
          }

          .selection-header {
            text-align: center;
          }

          .selection-header h3 {
            margin: 0 0 8px;
            font-size: 1.4rem;
            font-weight: 700;
            color: #fff;
          }

          .selection-header p {
            margin: 0;
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.95rem;
          }

          .paths-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
          }

          .path-option-card {
            position: relative;
            padding: 24px;
            background: linear-gradient(135deg, 
              rgba(255, 255, 255, 0.03) 0%,
              rgba(255, 255, 255, 0.01) 100%
            );
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            overflow: hidden;
          }

          .path-option-card:hover {
            border-color: var(--path-color);
            transform: translateY(-4px);
            box-shadow: 0 12px 40px color-mix(in srgb, var(--path-color) 20%, transparent);
          }

          .path-option-glow {
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(
              circle at center,
              color-mix(in srgb, var(--path-color) 10%, transparent) 0%,
              transparent 50%
            );
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
          }

          .path-option-card:hover .path-option-glow {
            opacity: 1;
          }

          .path-option-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg,
              color-mix(in srgb, var(--path-color) 20%, transparent),
              color-mix(in srgb, var(--path-color) 10%, transparent)
            );
            border: 1px solid color-mix(in srgb, var(--path-color) 30%, transparent);
            border-radius: 14px;
            color: var(--path-color);
            margin-bottom: 16px;
          }

          .path-option-name {
            font-size: 1.2rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 8px;
          }

          .path-option-desc {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.5);
            line-height: 1.5;
            margin-bottom: 12px;
          }

          .path-option-bonus {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            font-size: 0.8rem;
            color: var(--path-color);
            margin-bottom: 12px;
          }

          .path-option-skills {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 16px;
          }

          .skill-tag {
            padding: 4px 10px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.6);
          }

          .path-option-select {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 10px;
            background: color-mix(in srgb, var(--path-color) 15%, transparent);
            border: 1px solid color-mix(in srgb, var(--path-color) 30%, transparent);
            border-radius: 10px;
            color: var(--path-color);
            font-size: 0.9rem;
            font-weight: 600;
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.3s;
          }

          .path-option-card:hover .path-option-select {
            opacity: 1;
            transform: translateY(0);
          }
        `}</style>
      </div>
    );
  }

  // 已选择神格 - 展示界面
  const currentPath = status.path!;
  const pathColor = PATH_COLORS[currentPath.path] || "#f59e0b";
  const expPercent = Math.min(100, (currentPath.experience / currentPath.next_level_exp) * 100);
  const currentSkills = skills.filter(s => s.is_current_path);

  return (
    <div className="path-info">
      {/* 神格状态卡片 */}
      <AnalysisSection
        title={`${currentPath.icon} ${currentPath.name}`}
        accentColor={pathColor}
      >
        <div className="current-path-display">
          <div className="path-level-ring">
            <svg viewBox="0 0 100 100" className="level-svg">
              <defs>
                <linearGradient id="pathGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor={pathColor} />
                  <stop offset="100%" stopColor={`${pathColor}80`} />
                </linearGradient>
              </defs>
              <circle
                cx="50" cy="50" r="42"
                fill="none"
                stroke="rgba(255,255,255,0.08)"
                strokeWidth="6"
              />
              <circle
                cx="50" cy="50" r="42"
                fill="none"
                stroke="url(#pathGrad)"
                strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={`${expPercent * 2.64} 264`}
                transform="rotate(-90 50 50)"
              />
            </svg>
            <div className="level-number">
              <span className="level-value">{currentPath.level}</span>
              <span className="level-label">级</span>
            </div>
          </div>
          
          <div className="path-details">
            <div className="path-exp-info">
              <span>经验值</span>
              <span>{currentPath.experience} / {currentPath.next_level_exp}</span>
            </div>
            <div className="path-exp-bar">
              <div 
                className="path-exp-fill" 
                style={{ width: `${expPercent}%`, background: pathColor }}
              />
            </div>
            <div className="path-passive" style={{ color: pathColor }}>
              <Flame size={14} />
              <span>{currentPath.passive_bonus}</span>
            </div>
          </div>
        </div>
      </AnalysisSection>

      {/* 技能列表 */}
      <AnalysisSection title="神力技能" icon={<Zap size={16} />} accentColor={pathColor}>
        <div className="skills-grid">
          {currentSkills.map((skill) => (
            <div
              key={skill.id}
              className={`skill-card ${skill.unlocked ? "" : "locked"}`}
              style={{ "--skill-color": pathColor } as React.CSSProperties}
            >
              <div className="skill-icon-box">
                <span>{skill.icon}</span>
                {!skill.unlocked && <Lock size={12} className="lock-badge" />}
              </div>
              <div className="skill-info">
                <div className="skill-name">{skill.name}</div>
                <div className="skill-desc">{skill.description}</div>
                <div className="skill-meta">
                  <span className="skill-cost">{skill.cost}⚡</span>
                  <span>CD: {skill.cooldown}回合</span>
                  <span>使用: {skill.uses}次</span>
                </div>
              </div>
              {skill.unlocked ? (
                <ActionButton
                  variant="primary"
                  size="small"
                  onClick={() => onUseSkill(skill.id)}
                  disabled={loading}
                >
                  释放
                </ActionButton>
              ) : (
                <div className="unlock-req">Lv.{skill.unlock_level}</div>
              )}
            </div>
          ))}
        </div>
      </AnalysisSection>

      <style>{`
        .path-info {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .current-path-display {
          display: flex;
          align-items: center;
          gap: 24px;
          padding: 8px;
        }

        .path-level-ring {
          position: relative;
          width: 100px;
          height: 100px;
          flex-shrink: 0;
        }

        .level-svg {
          width: 100%;
          height: 100%;
        }

        .level-number {
          position: absolute;
          inset: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
        }

        .level-value {
          font-size: 2rem;
          font-weight: 800;
          color: #fff;
          line-height: 1;
        }

        .level-label {
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.5);
          text-transform: uppercase;
        }

        .path-details {
          flex: 1;
        }

        .path-exp-info {
          display: flex;
          justify-content: space-between;
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.6);
          margin-bottom: 8px;
        }

        .path-exp-bar {
          height: 8px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 4px;
          overflow: hidden;
          margin-bottom: 12px;
        }

        .path-exp-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 0.5s ease;
        }

        .path-passive {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.9rem;
          font-weight: 500;
        }

        .skills-grid {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .skill-card {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 16px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 12px;
          transition: all 0.2s;
        }

        .skill-card:hover {
          background: rgba(255, 255, 255, 0.04);
          border-color: rgba(255, 255, 255, 0.1);
        }

        .skill-card.locked {
          opacity: 0.5;
        }

        .skill-icon-box {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          background: linear-gradient(135deg,
            color-mix(in srgb, var(--skill-color) 20%, transparent),
            color-mix(in srgb, var(--skill-color) 10%, transparent)
          );
          border: 1px solid color-mix(in srgb, var(--skill-color) 30%, transparent);
          border-radius: 12px;
          font-size: 1.4rem;
          flex-shrink: 0;
        }

        .lock-badge {
          position: absolute;
          bottom: -4px;
          right: -4px;
          padding: 3px;
          background: rgba(0, 0, 0, 0.8);
          border-radius: 50%;
          color: rgba(255, 255, 255, 0.6);
        }

        .skill-info {
          flex: 1;
          min-width: 0;
        }

        .skill-name {
          font-size: 1rem;
          font-weight: 600;
          color: #fff;
          margin-bottom: 4px;
        }

        .skill-desc {
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.5);
          margin-bottom: 8px;
          line-height: 1.4;
        }

        .skill-meta {
          display: flex;
          gap: 12px;
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.4);
        }

        .skill-cost {
          color: var(--skill-color);
          font-weight: 600;
        }

        .unlock-req {
          padding: 6px 12px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.4);
        }
      `}</style>
    </div>
  );
}

// ==================== 信仰标签页 ====================

function FaithTab({ status, onRefresh }: { status: DivineStatus; onRefresh: () => void }) {
  const faith = status.faith;
  const [actionLoading, setActionLoading] = useState(false);

  const handleAddFollower = async () => {
    const code = prompt("请输入要添加为信徒的物种代码:");
    if (!code) return;

    setActionLoading(true);
    try {
      const res = await fetch("/api/divine/faith/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lineage_code: code }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message || "添加信徒成功");
        onRefresh();
        dispatchEnergyChanged();
      } else {
        alert(data.detail || "添加失败");
      }
    } catch (e) {
      console.error(e);
      alert("请求失败，请检查网络连接");
    } finally {
      setActionLoading(false);
    }
  };

  const handleBless = async (code: string) => {
    setActionLoading(true);
    try {
      const res = await fetch("/api/divine/faith/bless", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lineage_code: code }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message || "显圣成功！消耗20能量");
        onRefresh();
        dispatchEnergyChanged();
      } else {
        alert(data.detail || "显圣失败");
      }
    } catch (e) {
      console.error(e);
      alert("请求失败");
    } finally {
      setActionLoading(false);
    }
  };

  const handleSanctify = async (code: string) => {
    setActionLoading(true);
    try {
      const res = await fetch("/api/divine/faith/sanctify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lineage_code: code }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message || "圣化成功！消耗40能量");
        onRefresh();
        dispatchEnergyChanged();
      } else {
        alert(data.detail || "圣化失败");
      }
    } catch (e) {
      console.error(e);
      alert("请求失败");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="faith-tab">
      {/* 统计卡片 */}
      <div className="faith-stats">
        <StatCard label="信徒" value={faith.total_followers} icon={<Users size={20} />} accentColor="#a855f7" />
        <StatCard label="总信仰" value={faith.total_faith.toFixed(1)} icon={<Star size={20} />} accentColor="#f59e0b" />
        <StatCard label="每回合" value={`+${faith.faith_bonus_per_turn}`} icon={<Zap size={20} />} accentColor="#22c55e" />
      </div>

      {/* 操作按钮 */}
      <div className="faith-actions">
        <ActionButton variant="secondary" icon={<Users size={16} />} onClick={handleAddFollower} disabled={actionLoading}>
          添加信徒
        </ActionButton>
      </div>

      {/* 信徒列表 */}
      <AnalysisSection title="信徒列表" icon={<Users size={16} />} accentColor="#a855f7">
        {faith.followers.length === 0 ? (
          <EmptyState
            icon={<Users />}
            title="暂无信徒"
            description="保护物种后自动成为信徒，或手动添加"
          />
        ) : (
          <div className="followers-list">
            {faith.followers.map((f) => (
              <div key={f.lineage_code} className="follower-item">
                <div className="follower-avatar">
                  {f.is_sanctified ? "👑" : f.is_blessed ? "✨" : "🙏"}
                </div>
                <div className="follower-info">
                  <div className="follower-name">
                    {f.common_name}
                    <span className="follower-code">{f.lineage_code}</span>
                  </div>
                  <div className="follower-stats">
                    <span>信仰: {f.faith_value.toFixed(1)}</span>
                    <span>贡献: +{f.contribution_per_turn}/回合</span>
                    <span>追随: {f.turns_as_follower}回合</span>
                  </div>
                </div>
                <div className="follower-actions">
                  {!f.is_blessed && (
                    <ActionButton size="small" variant="ghost" onClick={() => handleBless(f.lineage_code)} disabled={actionLoading}>
                      显圣
                    </ActionButton>
                  )}
                  {f.is_blessed && !f.is_sanctified && (
                    <ActionButton size="small" variant="ghost" onClick={() => handleSanctify(f.lineage_code)} disabled={actionLoading}>
                      圣化
                    </ActionButton>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </AnalysisSection>

      <style>{`
        .faith-tab {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .faith-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }

        .faith-actions {
          display: flex;
          gap: 12px;
        }

        .followers-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .follower-item {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 14px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 12px;
          transition: all 0.2s;
        }

        .follower-item:hover {
          background: rgba(255, 255, 255, 0.04);
        }

        .follower-avatar {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 44px;
          height: 44px;
          background: rgba(168, 85, 247, 0.15);
          border: 1px solid rgba(168, 85, 247, 0.25);
          border-radius: 12px;
          font-size: 1.3rem;
        }

        .follower-info {
          flex: 1;
          min-width: 0;
        }

        .follower-name {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          color: #fff;
          margin-bottom: 4px;
        }

        .follower-code {
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.4);
          font-weight: 400;
        }

        .follower-stats {
          display: flex;
          gap: 12px;
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.5);
        }

        .follower-actions {
          display: flex;
          gap: 8px;
        }
      `}</style>
    </div>
  );
}

// ==================== 神迹标签页 ====================

function MiraclesTab({
  status,
  onExecute,
  loading,
}: {
  status: DivineStatus;
  onExecute: (id: string) => void;
  loading: boolean;
}) {
  return (
    <div className="miracles-tab">
      <div className="miracles-grid">
        {status.miracles.map((m) => (
          <div
            key={m.id}
            className={`miracle-card ${m.available ? "" : "unavailable"}`}
          >
            <div className="miracle-header">
              <div className="miracle-icon">{m.icon}</div>
              <div className="miracle-title">
                <span className="miracle-name">{m.name}</span>
                <span className="miracle-cost">{m.cost}⚡</span>
              </div>
            </div>
            
            <div className="miracle-desc">{m.description}</div>
            
            <div className="miracle-meta">
              <span>蓄力: {m.charge_turns}回合</span>
              <span>冷却: {m.cooldown}回合</span>
              {m.one_time && <span className="one-time-badge">一次性</span>}
            </div>

            {m.is_charging && (
              <div className="charging-indicator">
                <div className="charging-bar">
                  <div 
                    className="charging-fill"
                    style={{ width: `${(m.charge_progress / m.charge_turns) * 100}%` }}
                  />
                </div>
                <span>蓄力中 {m.charge_progress}/{m.charge_turns}</span>
              </div>
            )}

            {m.current_cooldown > 0 && (
              <div className="cooldown-badge">
                <AlertTriangle size={14} />
                冷却中: {m.current_cooldown}回合
              </div>
            )}

            {m.available && (
              <ActionButton
                variant="primary"
                size="small"
                icon={<Sparkles size={14} />}
                onClick={() => onExecute(m.id)}
                disabled={loading}
                fullWidth
              >
                释放神迹
              </ActionButton>
            )}
          </div>
        ))}
      </div>

      <style>{`
        .miracles-tab {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .miracles-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 16px;
        }

        .miracle-card {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 20px;
          background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.03) 0%,
            rgba(255, 255, 255, 0.01) 100%
          );
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          transition: all 0.2s;
        }

        .miracle-card:hover {
          border-color: rgba(168, 85, 247, 0.3);
          box-shadow: 0 8px 32px rgba(168, 85, 247, 0.1);
        }

        .miracle-card.unavailable {
          opacity: 0.6;
        }

        .miracle-header {
          display: flex;
          align-items: flex-start;
          gap: 14px;
        }

        .miracle-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          background: linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(168, 85, 247, 0.1));
          border: 1px solid rgba(168, 85, 247, 0.3);
          border-radius: 12px;
          font-size: 1.5rem;
        }

        .miracle-title {
          flex: 1;
        }

        .miracle-name {
          display: block;
          font-size: 1.1rem;
          font-weight: 700;
          color: #fff;
          margin-bottom: 4px;
        }

        .miracle-cost {
          font-size: 0.9rem;
          color: #f59e0b;
          font-weight: 600;
        }

        .miracle-desc {
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.6);
          line-height: 1.5;
        }

        .miracle-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.4);
        }

        .one-time-badge {
          padding: 2px 8px;
          background: rgba(239, 68, 68, 0.2);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 4px;
          color: #f87171;
        }

        .charging-indicator {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .charging-bar {
          height: 6px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 3px;
          overflow: hidden;
        }

        .charging-fill {
          height: 100%;
          background: linear-gradient(90deg, #a855f7, #c084fc);
          border-radius: 3px;
          transition: width 0.3s;
        }

        .charging-indicator span {
          font-size: 0.75rem;
          color: #a855f7;
          text-align: center;
        }

        .cooldown-badge {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 8px;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.2);
          border-radius: 8px;
          font-size: 0.8rem;
          color: #f87171;
        }
      `}</style>
    </div>
  );
}

// ==================== 预言标签页 ====================

function WagersTab({
  status,
  onPlaceWager,
  onRefresh,
  loading,
}: {
  status: DivineStatus;
  onPlaceWager: (type: string) => void;
  onRefresh: () => void;
  loading: boolean;
}) {
  const wagers = status.wagers;

  const handleCheckWager = async (wagerId: string) => {
    try {
      const res = await fetch("/api/divine/wager/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ wager_id: wagerId }),
      });
      const data = await res.json();
      if (res.ok) {
        if (data.status === "resolved") {
          const result = data.success ? "成功" : "失败";
          alert(`预言${result}！${data.reason}\n${data.success ? `获得 ${data.reward} 能量` : `损失押注能量`}`);
          onRefresh();
          dispatchEnergyChanged();
        } else {
          alert(data.message);
        }
      } else {
        alert(data.detail);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="wagers-tab">
      {/* 统计 */}
      <div className="wager-stats">
        <StatCard label="总赢得" value={wagers.total_won} icon={<Check size={20} />} accentColor="#22c55e" />
        <StatCard label="总损失" value={wagers.total_lost} icon={<AlertTriangle size={20} />} accentColor="#ef4444" />
        <StatCard 
          label="净收益" 
          value={`${wagers.net_profit >= 0 ? "+" : ""}${wagers.net_profit}`} 
          icon={<Target size={20} />} 
          accentColor={wagers.net_profit >= 0 ? "#22c55e" : "#ef4444"}
        />
      </div>

      {wagers.faith_shaken_turns > 0 && (
        <div className="debuff-warning">
          <AlertTriangle size={16} />
          神威动摇！无法下注，剩余 {wagers.faith_shaken_turns} 回合
        </div>
      )}

      {/* 预言类型 */}
      <AnalysisSection title="可用预言" icon={<Dice6 size={16} />} accentColor="#22c55e">
        <div className="wager-types-grid">
          {wagers.wager_types.map((wt) => (
            <div key={wt.type} className="wager-type-card">
              <div className="wt-icon">{wt.icon}</div>
              <div className="wt-info">
                <div className="wt-name">{wt.name}</div>
                <div className="wt-desc">{wt.description}</div>
                <div className="wt-meta">
                  <span>{wt.min_bet}~{wt.max_bet}⚡</span>
                  <span>{wt.duration}回合</span>
                  <span className="wt-mult">×{wt.multiplier}</span>
                </div>
              </div>
              <ActionButton
                size="small"
                variant="success"
                icon={<Dice6 size={14} />}
                onClick={() => onPlaceWager(wt.type)}
                disabled={loading || wagers.faith_shaken_turns > 0}
              >
                下注
              </ActionButton>
            </div>
          ))}
        </div>
      </AnalysisSection>

      {/* 进行中的预言 */}
      <AnalysisSection title="进行中" icon={<Target size={16} />} accentColor="#f59e0b">
        {wagers.active_wagers.length === 0 ? (
          <EmptyState icon={<Dice6 />} title="暂无进行中的预言" description="选择一个预言类型开始下注" />
        ) : (
          <div className="active-wagers-list">
            {wagers.active_wagers.map((w) => {
              const typeInfo = wagers.wager_types.find(t => t.type === w.wager_type);
              return (
                <div key={w.id} className="active-wager-item">
                  <div className="aw-icon">{typeInfo?.icon}</div>
                  <div className="aw-info">
                    <div className="aw-title">{typeInfo?.name}</div>
                    <div className="aw-target">
                      目标: {w.target_species}
                      {w.secondary_species && ` vs ${w.secondary_species}`}
                    </div>
                    <div className="aw-meta">
                      <span className="aw-bet">{w.bet_amount}⚡</span>
                      <span>截止: 第{w.end_turn}回合</span>
                    </div>
                  </div>
                  <ActionButton size="small" variant="ghost" onClick={() => handleCheckWager(w.id)}>
                    检查
                  </ActionButton>
                </div>
              );
            })}
          </div>
        )}
      </AnalysisSection>

      <style>{`
        .wagers-tab {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .wager-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }

        .debuff-warning {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          padding: 14px;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.25);
          border-radius: 12px;
          color: #f87171;
          font-weight: 500;
        }

        .wager-types-grid {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .wager-type-card {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 16px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 12px;
          transition: all 0.2s;
        }

        .wager-type-card:hover {
          background: rgba(255, 255, 255, 0.04);
          border-color: rgba(34, 197, 94, 0.2);
        }

        .wt-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 44px;
          height: 44px;
          background: rgba(34, 197, 94, 0.15);
          border: 1px solid rgba(34, 197, 94, 0.25);
          border-radius: 12px;
          font-size: 1.3rem;
        }

        .wt-info {
          flex: 1;
          min-width: 0;
        }

        .wt-name {
          font-weight: 600;
          color: #fff;
          margin-bottom: 4px;
        }

        .wt-desc {
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.5);
          margin-bottom: 6px;
        }

        .wt-meta {
          display: flex;
          gap: 12px;
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.4);
        }

        .wt-mult {
          color: #22c55e;
          font-weight: 600;
        }

        .active-wagers-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .active-wager-item {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 14px;
          background: linear-gradient(135deg, rgba(245, 158, 11, 0.05), transparent);
          border: 1px solid rgba(245, 158, 11, 0.15);
          border-radius: 12px;
        }

        .aw-icon {
          font-size: 1.3rem;
        }

        .aw-info {
          flex: 1;
          min-width: 0;
        }

        .aw-title {
          font-weight: 600;
          color: #fff;
          margin-bottom: 2px;
        }

        .aw-target {
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.6);
          margin-bottom: 4px;
        }

        .aw-meta {
          display: flex;
          gap: 12px;
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.4);
        }

        .aw-bet {
          color: #f59e0b;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}

export default DivinePowersPanel;
