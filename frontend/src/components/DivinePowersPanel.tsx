import { useState, useEffect, useCallback } from "react";
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
  onClose?: () => void;
}

// ==================== 子标签页组件 ====================

type TabType = "path" | "faith" | "miracles" | "wagers";

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
        fetchStatus();
      } else {
        alert(data.detail || "选择神格失败");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  const handleUseSkill = async (skillId: string) => {
    const target = prompt("请输入目标物种代码（部分技能需要）:");
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
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartMiracle = async (miracleId: string) => {
    setActionLoading(true);
    try {
      const res = await fetch("/api/divine/miracle/charge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ miracle_id: miracleId }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message);
        fetchStatus();
        dispatchEnergyChanged();
      } else {
        alert(data.detail || "蓄力失败");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecuteMiracle = async (miracleId: string) => {
    setActionLoading(true);
    try {
      const res = await fetch("/api/divine/miracle/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ miracle_id: miracleId }),
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

  if (loading || !status) {
    return (
      <div className="divine-panel">
        <div className="divine-loading">加载神力系统...</div>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="divine-panel">
      <div className="divine-header">
        <h2>⚡ 神力进阶</h2>
        {onClose && (
          <button className="close-btn" onClick={onClose}>
            ✕
          </button>
        )}
      </div>

      <div className="divine-tabs">
        <button
          className={`tab ${activeTab === "path" ? "active" : ""}`}
          onClick={() => setActiveTab("path")}
        >
          🌟 神格
        </button>
        <button
          className={`tab ${activeTab === "faith" ? "active" : ""}`}
          onClick={() => setActiveTab("faith")}
        >
          🙏 信仰
        </button>
        <button
          className={`tab ${activeTab === "miracles" ? "active" : ""}`}
          onClick={() => setActiveTab("miracles")}
        >
          ✨ 神迹
        </button>
        <button
          className={`tab ${activeTab === "wagers" ? "active" : ""}`}
          onClick={() => setActiveTab("wagers")}
        >
          🎲 预言
        </button>
      </div>

      <div className="divine-content">
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
            onStartCharge={handleStartMiracle}
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

      <style>{styles}</style>
    </div>
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

  // 未选择神格
  if (!status.path && status.available_paths) {
    return (
      <div className="path-selection">
        <h3>选择你的神格</h3>
        <p className="hint">选择一条神力路线，解锁专属能力和加成。</p>
        <div className="paths-grid">
          {status.available_paths.map((path) => (
            <div
              key={path.path}
              className="path-card"
              style={{ borderColor: path.color }}
              onClick={() => !loading && onChoosePath(path.path)}
            >
              <div className="path-icon" style={{ color: path.color }}>
                {path.icon}
              </div>
              <div className="path-name">{path.name}</div>
              <div className="path-desc">{path.description}</div>
              <div className="path-bonus">
                <strong>被动加成:</strong> {path.passive_bonus}
              </div>
              <div className="path-skills">
                技能: {path.skills.join(", ")}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 已选择神格
  const currentPath = status.path!;
  const expPercent = Math.min(
    100,
    (currentPath.experience / currentPath.next_level_exp) * 100
  );

  return (
    <div className="path-info">
      <div
        className="current-path-card"
        style={{ borderColor: currentPath.color }}
      >
        <div className="path-header">
          <span className="path-icon" style={{ color: currentPath.color }}>
            {currentPath.icon}
          </span>
          <span className="path-name">{currentPath.name}</span>
          <span className="path-level">Lv.{currentPath.level}</span>
        </div>
        <div className="exp-bar">
          <div
            className="exp-fill"
            style={{
              width: `${expPercent}%`,
              background: currentPath.color,
            }}
          />
          <span className="exp-text">
            {currentPath.experience} / {currentPath.next_level_exp}
          </span>
        </div>
        <div className="path-bonus">{currentPath.passive_bonus}</div>
      </div>

      <h4>技能</h4>
      <div className="skills-list">
        {skills
          .filter((s) => s.is_current_path)
          .map((skill) => (
            <div
              key={skill.id}
              className={`skill-card ${skill.unlocked ? "" : "locked"}`}
            >
              <div className="skill-header">
                <span className="skill-icon">{skill.icon}</span>
                <span className="skill-name">{skill.name}</span>
                <span className="skill-cost">{skill.cost}⚡</span>
              </div>
              <div className="skill-desc">{skill.description}</div>
              <div className="skill-meta">
                <span>冷却: {skill.cooldown}回合</span>
                <span>使用: {skill.uses}次</span>
              </div>
              {skill.unlocked && (
                <button
                  className="skill-btn"
                  onClick={() => onUseSkill(skill.id)}
                  disabled={loading}
                >
                  释放
                </button>
              )}
              {!skill.unlocked && (
                <div className="unlock-hint">
                  需要等级 {skill.unlock_level}
                </div>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}

// ==================== 信仰标签页 ====================

function FaithTab({
  status,
  onRefresh,
}: {
  status: DivineStatus;
  onRefresh: () => void;
}) {
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
        onRefresh();
      } else {
        alert(data.detail || "添加失败");
      }
    } catch (e) {
      console.error(e);
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
        alert(data.message);
        onRefresh();
        dispatchEnergyChanged();
      } else {
        alert(data.detail || "显圣失败");
      }
    } catch (e) {
      console.error(e);
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
        alert(data.message);
        onRefresh();
        dispatchEnergyChanged();
      } else {
        alert(data.detail || "圣化失败");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="faith-tab">
      <div className="faith-summary">
        <div className="faith-stat">
          <span className="stat-value">{faith.total_followers}</span>
          <span className="stat-label">信徒</span>
        </div>
        <div className="faith-stat">
          <span className="stat-value">{faith.total_faith.toFixed(1)}</span>
          <span className="stat-label">总信仰</span>
        </div>
        <div className="faith-stat">
          <span className="stat-value">+{faith.faith_bonus_per_turn}</span>
          <span className="stat-label">每回合</span>
        </div>
      </div>

      <div className="action-row">
        <button
          className="action-btn"
          onClick={handleAddFollower}
          disabled={actionLoading}
        >
          ➕ 添加信徒
        </button>
      </div>

      <h4>信徒列表</h4>
      <div className="followers-list">
        {faith.followers.length === 0 ? (
          <div className="empty-hint">暂无信徒，保护物种后自动成为信徒</div>
        ) : (
          faith.followers.map((f) => (
            <div key={f.lineage_code} className="follower-card">
              <div className="follower-header">
                <span className="follower-name">{f.common_name}</span>
                <span className="follower-code">{f.lineage_code}</span>
                {f.is_sanctified && <span className="badge sanctified">圣</span>}
                {f.is_blessed && !f.is_sanctified && (
                  <span className="badge blessed">眷</span>
                )}
              </div>
              <div className="follower-stats">
                <span>信仰: {f.faith_value.toFixed(1)}</span>
                <span>贡献: +{f.contribution_per_turn}/回合</span>
                <span>追随: {f.turns_as_follower}回合</span>
              </div>
              <div className="follower-actions">
                {!f.is_blessed && (
                  <button
                    className="small-btn"
                    onClick={() => handleBless(f.lineage_code)}
                    disabled={actionLoading}
                  >
                    🙏 显圣 (20⚡)
                  </button>
                )}
                {f.is_blessed && !f.is_sanctified && (
                  <button
                    className="small-btn gold"
                    onClick={() => handleSanctify(f.lineage_code)}
                    disabled={actionLoading}
                  >
                    👑 圣化 (40⚡)
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ==================== 神迹标签页 ====================

function MiraclesTab({
  status,
  onStartCharge,
  onExecute,
  loading,
}: {
  status: DivineStatus;
  onStartCharge: (id: string) => void;
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
              <span className="miracle-icon">{m.icon}</span>
              <span className="miracle-name">{m.name}</span>
              <span className="miracle-cost">{m.cost}⚡</span>
            </div>
            <div className="miracle-desc">{m.description}</div>
            <div className="miracle-meta">
              <span>蓄力: {m.charge_turns}回合</span>
              <span>冷却: {m.cooldown}回合</span>
              {m.one_time && <span className="one-time">一次性</span>}
            </div>

            {m.is_charging && (
              <div className="charging-bar">
                <div
                  className="charging-fill"
                  style={{
                    width: `${(m.charge_progress / m.charge_turns) * 100}%`,
                  }}
                />
                <span>
                  蓄力中 {m.charge_progress}/{m.charge_turns}
                </span>
              </div>
            )}

            {m.current_cooldown > 0 && (
              <div className="cooldown-info">
                冷却中: {m.current_cooldown}回合
              </div>
            )}

            <div className="miracle-actions">
              {m.available && !m.is_charging && (
                <button
                  className="miracle-btn"
                  onClick={() => onExecute(m.id)}
                  disabled={loading}
                >
                  ✨ 释放神迹
                </button>
              )}
              {!m.available && m.current_cooldown === 0 && !m.is_charging && (
                <button
                  className="miracle-btn secondary"
                  onClick={() => onStartCharge(m.id)}
                  disabled={loading}
                >
                  ⏳ 开始蓄力
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
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
      <div className="wager-summary">
        <div className="wager-stat">
          <span className="stat-value">{wagers.total_won}</span>
          <span className="stat-label">总赢得</span>
        </div>
        <div className="wager-stat">
          <span className="stat-value">{wagers.total_lost}</span>
          <span className="stat-label">总损失</span>
        </div>
        <div className="wager-stat">
          <span
            className={`stat-value ${wagers.net_profit >= 0 ? "positive" : "negative"}`}
          >
            {wagers.net_profit >= 0 ? "+" : ""}
            {wagers.net_profit}
          </span>
          <span className="stat-label">净收益</span>
        </div>
      </div>

      {wagers.faith_shaken_turns > 0 && (
        <div className="debuff-warning">
          ⚠️ 神威动摇！无法下注，剩余 {wagers.faith_shaken_turns} 回合
        </div>
      )}

      <h4>可用预言</h4>
      <div className="wager-types-grid">
        {wagers.wager_types.map((wt) => (
          <div key={wt.type} className="wager-type-card">
            <div className="wt-header">
              <span className="wt-icon">{wt.icon}</span>
              <span className="wt-name">{wt.name}</span>
            </div>
            <div className="wt-desc">{wt.description}</div>
            <div className="wt-meta">
              <span>
                押注: {wt.min_bet}~{wt.max_bet}⚡
              </span>
              <span>期限: {wt.duration}回合</span>
              <span className="multiplier">×{wt.multiplier}</span>
            </div>
            <button
              className="wager-btn"
              onClick={() => onPlaceWager(wt.type)}
              disabled={loading || wagers.faith_shaken_turns > 0}
            >
              🎲 下注
            </button>
          </div>
        ))}
      </div>

      <h4>进行中的预言</h4>
      <div className="active-wagers">
        {wagers.active_wagers.length === 0 ? (
          <div className="empty-hint">暂无进行中的预言</div>
        ) : (
          wagers.active_wagers.map((w) => {
            const typeInfo = wagers.wager_types.find(
              (t) => t.type === w.wager_type
            );
            return (
              <div key={w.id} className="active-wager-card">
                <div className="aw-header">
                  <span>{typeInfo?.icon}</span>
                  <span>{typeInfo?.name}</span>
                  <span className="aw-bet">{w.bet_amount}⚡</span>
                </div>
                <div className="aw-target">
                  目标: {w.target_species}
                  {w.secondary_species && ` vs ${w.secondary_species}`}
                </div>
                <div className="aw-deadline">
                  截止回合: {w.end_turn}
                </div>
                <button
                  className="check-btn"
                  onClick={() => handleCheckWager(w.id)}
                >
                  检查结果
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ==================== 样式 ====================

const styles = `
.divine-panel {
  background: var(--bg-secondary, #1a1a2e);
  border: 1px solid var(--border-primary, #333);
  border-radius: 12px;
  padding: 16px;
  min-width: 420px;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  color: var(--text-primary, #e0e0e0);
  font-family: 'Segoe UI', system-ui, sans-serif;
}

.divine-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-primary, #333);
}

.divine-header h2 {
  margin: 0;
  font-size: 1.4rem;
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted, #888);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px 8px;
}

.close-btn:hover {
  color: var(--text-primary, #e0e0e0);
}

.divine-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
}

.tab {
  flex: 1;
  padding: 10px 12px;
  background: rgba(255,255,255,0.05);
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--text-secondary, #aaa);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.9rem;
}

.tab:hover {
  background: rgba(255,255,255,0.1);
}

.tab.active {
  background: rgba(245, 158, 11, 0.15);
  border-color: rgba(245, 158, 11, 0.5);
  color: #f59e0b;
}

.divine-content {
  min-height: 300px;
}

.divine-loading {
  text-align: center;
  padding: 40px;
  color: var(--text-muted, #888);
}

/* 神格选择 */
.path-selection h3 {
  margin: 0 0 8px 0;
  color: var(--text-primary);
}

.hint {
  color: var(--text-muted, #888);
  font-size: 0.85rem;
  margin-bottom: 16px;
}

.paths-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.path-card {
  padding: 16px;
  background: rgba(255,255,255,0.03);
  border: 2px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.path-card:hover {
  background: rgba(255,255,255,0.08);
  transform: translateY(-2px);
}

.path-icon {
  font-size: 2rem;
  margin-bottom: 8px;
}

.path-name {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 6px;
}

.path-desc {
  font-size: 0.8rem;
  color: var(--text-secondary, #aaa);
  margin-bottom: 8px;
}

.path-bonus {
  font-size: 0.75rem;
  color: #10b981;
  margin-bottom: 6px;
}

.path-skills {
  font-size: 0.7rem;
  color: var(--text-muted, #888);
}

/* 当前神格信息 */
.current-path-card {
  padding: 16px;
  background: rgba(255,255,255,0.03);
  border: 2px solid;
  border-radius: 12px;
  margin-bottom: 16px;
}

.path-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.path-level {
  margin-left: auto;
  font-weight: 600;
  font-size: 1.1rem;
}

.exp-bar {
  position: relative;
  height: 20px;
  background: rgba(0,0,0,0.3);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 10px;
}

.exp-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 10px;
  transition: width 0.3s;
}

.exp-text {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.75rem;
  font-weight: 600;
  color: white;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}

/* 技能列表 */
.skills-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skill-card {
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
}

.skill-card.locked {
  opacity: 0.5;
}

.skill-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.skill-icon {
  font-size: 1.2rem;
}

.skill-name {
  font-weight: 600;
}

.skill-cost {
  margin-left: auto;
  color: #f59e0b;
}

.skill-desc {
  font-size: 0.8rem;
  color: var(--text-secondary, #aaa);
  margin-bottom: 6px;
}

.skill-meta {
  display: flex;
  gap: 12px;
  font-size: 0.7rem;
  color: var(--text-muted, #888);
  margin-bottom: 8px;
}

.skill-btn {
  padding: 6px 16px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  border: none;
  border-radius: 6px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.skill-btn:hover:not(:disabled) {
  transform: scale(1.02);
}

.skill-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.unlock-hint {
  font-size: 0.75rem;
  color: var(--text-muted, #888);
  font-style: italic;
}

/* 信仰标签 */
.faith-summary {
  display: flex;
  justify-content: space-around;
  padding: 16px;
  background: rgba(139, 92, 246, 0.1);
  border-radius: 12px;
  margin-bottom: 16px;
}

.faith-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #8b5cf6;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted, #888);
}

.action-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.action-btn {
  padding: 8px 16px;
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.4);
  border-radius: 8px;
  color: #a78bfa;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover:not(:disabled) {
  background: rgba(139, 92, 246, 0.3);
}

.followers-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.follower-card {
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
}

.follower-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.follower-name {
  font-weight: 600;
}

.follower-code {
  font-size: 0.75rem;
  color: var(--text-muted, #888);
}

.badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 600;
}

.badge.blessed {
  background: rgba(59, 130, 246, 0.3);
  color: #60a5fa;
}

.badge.sanctified {
  background: rgba(234, 179, 8, 0.3);
  color: #facc15;
}

.follower-stats {
  display: flex;
  gap: 12px;
  font-size: 0.75rem;
  color: var(--text-secondary, #aaa);
  margin-bottom: 8px;
}

.follower-actions {
  display: flex;
  gap: 8px;
}

.small-btn {
  padding: 4px 10px;
  font-size: 0.75rem;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 6px;
  color: #60a5fa;
  cursor: pointer;
}

.small-btn.gold {
  background: rgba(234, 179, 8, 0.2);
  border-color: rgba(234, 179, 8, 0.4);
  color: #facc15;
}

.empty-hint {
  text-align: center;
  padding: 20px;
  color: var(--text-muted, #888);
  font-style: italic;
}

/* 神迹标签 */
.miracles-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.miracle-card {
  padding: 14px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
}

.miracle-card.unavailable {
  opacity: 0.6;
}

.miracle-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.miracle-icon {
  font-size: 1.3rem;
}

.miracle-name {
  font-weight: 600;
}

.miracle-cost {
  margin-left: auto;
  color: #f59e0b;
  font-weight: 600;
}

.miracle-desc {
  font-size: 0.8rem;
  color: var(--text-secondary, #aaa);
  margin-bottom: 8px;
}

.miracle-meta {
  display: flex;
  gap: 10px;
  font-size: 0.7rem;
  color: var(--text-muted, #888);
  margin-bottom: 10px;
}

.one-time {
  color: #ef4444;
}

.charging-bar {
  position: relative;
  height: 18px;
  background: rgba(0,0,0,0.3);
  border-radius: 9px;
  overflow: hidden;
  margin-bottom: 10px;
}

.charging-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: linear-gradient(90deg, #8b5cf6, #a78bfa);
  border-radius: 9px;
}

.charging-bar span {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.7rem;
  color: white;
  font-weight: 600;
}

.cooldown-info {
  padding: 6px;
  background: rgba(239, 68, 68, 0.2);
  border-radius: 6px;
  font-size: 0.75rem;
  color: #f87171;
  text-align: center;
  margin-bottom: 10px;
}

.miracle-actions {
  display: flex;
  justify-content: center;
}

.miracle-btn {
  padding: 8px 16px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.miracle-btn.secondary {
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.4);
  color: #a78bfa;
}

.miracle-btn:hover:not(:disabled) {
  transform: scale(1.02);
}

.miracle-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 预言标签 */
.wager-summary {
  display: flex;
  justify-content: space-around;
  padding: 16px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 12px;
  margin-bottom: 16px;
}

.wager-stat .stat-value {
  color: #10b981;
}

.wager-stat .stat-value.positive {
  color: #10b981;
}

.wager-stat .stat-value.negative {
  color: #ef4444;
}

.debuff-warning {
  padding: 10px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: 8px;
  color: #f87171;
  text-align: center;
  margin-bottom: 16px;
}

.wager-types-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}

.wager-type-card {
  padding: 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
}

.wt-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.wt-icon {
  font-size: 1.2rem;
}

.wt-name {
  font-weight: 600;
}

.wt-desc {
  font-size: 0.75rem;
  color: var(--text-secondary, #aaa);
  margin-bottom: 6px;
}

.wt-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 0.7rem;
  color: var(--text-muted, #888);
  margin-bottom: 8px;
}

.multiplier {
  color: #10b981;
  font-weight: 600;
}

.wager-btn {
  width: 100%;
  padding: 6px;
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.4);
  border-radius: 6px;
  color: #34d399;
  cursor: pointer;
  transition: all 0.2s;
}

.wager-btn:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.3);
}

.wager-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.active-wagers {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.active-wager-card {
  padding: 12px;
  background: rgba(16, 185, 129, 0.05);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 8px;
}

.aw-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.aw-bet {
  margin-left: auto;
  color: #10b981;
  font-weight: 600;
}

.aw-target, .aw-deadline {
  font-size: 0.8rem;
  color: var(--text-secondary, #aaa);
  margin-bottom: 4px;
}

.check-btn {
  margin-top: 8px;
  padding: 6px 12px;
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.4);
  border-radius: 6px;
  color: #34d399;
  cursor: pointer;
}

h4 {
  margin: 16px 0 10px 0;
  font-size: 0.9rem;
  color: var(--text-primary);
}
`;

export default DivinePowersPanel;

