/**
 * ModelsSection - 智能路由配置 (全新设计)
 */

import { memo, type Dispatch } from "react";
import type { ProviderConfig, CapabilityRouteConfig } from "@/services/api.types";
import type { SettingsAction, CapabilityDef } from "../types";
import { AI_CAPABILITIES } from "../constants";
import { getProviderLogo } from "../reducer";
import { SectionHeader, Card, InfoBox, SelectRow, NumberInput } from "../common/Controls";

interface Props {
  providers: Record<string, ProviderConfig>;
  capabilityRoutes: Record<string, CapabilityRouteConfig>;
  aiProvider: string | null;
  aiModel: string | null;
  aiTimeout: number;
  dispatch: Dispatch<SettingsAction>;
}

// 能力分组配置
const CAPABILITY_GROUPS = [
  { key: "core", title: "核心能力", icon: "⚡", color: "#ef4444", desc: "影响整体推演质量的关键能力" },
  { key: "speciation", title: "物种分化", icon: "🧬", color: "#f59e0b", desc: "控制物种演化与分化的 AI 能力" },
  { key: "narrative", title: "叙事生成", icon: "📖", color: "#10b981", desc: "生成物种故事与描述的能力" },
  { key: "advanced", title: "高级功能", icon: "🔬", color: "#3b82f6", desc: "杂交、智能体评估等进阶功能" },
];

export const ModelsSection = memo(function ModelsSection({
  providers,
  capabilityRoutes,
  aiProvider,
  aiModel,
  aiTimeout,
  dispatch,
}: Props) {
  const providerList = Object.values(providers).filter((p) => p.api_key);

  const getProviderModels = (providerId: string): string[] => {
    const provider = providers[providerId];
    if (!provider?.models) return [];
    // 只返回启用的模型（不在 disabled_models 中的）
    const disabledModels = provider.disabled_models || [];
    return provider.models.filter(m => !disabledModels.includes(m));
  };

  const getEffectiveConfig = (cap: CapabilityDef) => {
    const route = capabilityRoutes[cap.key];
    if (route?.provider_id) {
      const provider = providers[route.provider_id];
      return {
        provider: provider?.name || route.provider_id,
        model: route.model || "默认",
        isCustom: true,
      };
    }
    if (aiProvider) {
      const provider = providers[aiProvider];
      return {
        provider: provider?.name || aiProvider,
        model: aiModel || "默认",
        isCustom: false,
      };
    }
    return null;
  };

  const renderCapabilityCard = (cap: CapabilityDef, groupColor: string) => {
    const route = capabilityRoutes[cap.key] || {
      provider_id: null,
      provider_ids: null,
      model: null,
      timeout: cap.defaultTimeout,
    };

    // 获取已选中的服务商列表
    const selectedProviderIds = route.provider_ids || (route.provider_id ? [route.provider_id] : []);
    const effective = getEffectiveConfig(cap);

    // 切换服务商选择
    const toggleProvider = (providerId: string) => {
      const current = [...selectedProviderIds];
      const index = current.indexOf(providerId);
      if (index >= 0) {
        current.splice(index, 1);
      } else {
        current.push(providerId);
      }
      dispatch({
        type: "UPDATE_ROUTE",
        capKey: cap.key,
        field: "provider_ids",
        value: current.length > 0 ? current : null,
      });
      // 同时清空单选字段
      if (route.provider_id) {
        dispatch({
          type: "UPDATE_ROUTE",
          capKey: cap.key,
          field: "provider_id",
          value: null,
        });
      }
    };

    return (
      <div
        key={cap.key}
        className="capability-card"
        style={{ borderTopColor: groupColor }}
      >
        {/* 头部 */}
        <div className="capability-header">
          <div className="capability-title">
            <strong>{cap.label}</strong>
            <span className={`parallel-badge ${cap.parallel || "single"}`}>
              {cap.parallel === "batch" ? "批量" : cap.parallel === "concurrent" ? "并发" : "单次"}
            </span>
          </div>
        </div>

        <p className="capability-desc">{cap.desc}</p>

        {/* 当前生效配置 */}
        {(selectedProviderIds.length > 0 || effective) && (
          <div className="capability-effective">
            <span className="effective-label">当前:</span>
            {selectedProviderIds.length > 0 ? (
              <div className="effective-value">
                {selectedProviderIds.map((pid, idx) => {
                  const p = providers[pid];
                  return (
                    <span key={pid} style={{ display: "flex", alignItems: "center", gap: "2px" }}>
                      {idx > 0 && <span className="effective-separator">+</span>}
                      <span className="effective-provider">{p?.name || pid}</span>
                    </span>
                  );
                })}
              </div>
            ) : effective ? (
              <div className="effective-value" style={{ flex: 1 }}>
                <span className="effective-provider">{effective.provider}</span>
                <span className="effective-separator">/</span>
                <span className="effective-model" title={effective.model}>
                  {effective.model}
                </span>
                <span className="effective-badge">默认</span>
              </div>
            ) : null}
          </div>
        )}

        {/* 配置选项 */}
        <div className="capability-config">
          {/* 可用服务商池 - 多选 */}
          <div>
            <div className="config-label" style={{ marginBottom: "6px" }}>
              可用服务商
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              {providerList.length === 0 ? (
                <span className="text-muted italic text-xs">
                  请先配置服务商
                </span>
              ) : (
                providerList.map((p) => {
                  const isSelected = selectedProviderIds.includes(p.id);
                  return (
                    <button
                      key={p.id}
                      onClick={() => toggleProvider(p.id)}
                      className={`provider-chip ${isSelected ? "selected" : ""}`}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "5px 10px",
                        background: isSelected ? "rgba(245, 158, 11, 0.15)" : "var(--s-bg-deep)",
                        border: `1px solid ${isSelected ? "var(--s-primary)" : "var(--s-border)"}`,
                        borderRadius: "var(--s-radius-sm)",
                        color: isSelected ? "var(--s-primary)" : "var(--s-text-secondary)",
                        fontSize: "0.75rem",
                        cursor: "pointer",
                        transition: "all 0.15s",
                      }}
                    >
                      {isSelected && <span>✓</span>}
                      <span>{getProviderLogo(p)}</span>
                      <span>{p.name}</span>
                    </button>
                  );
                })
              )}
            </div>
            {selectedProviderIds.length === 0 && providerList.length > 0 && (
              <div className="text-muted text-xs mt-1 italic">
                未选择则使用全局默认
              </div>
            )}
          </div>

          {/* 模型选择 - 当只选择一个服务商时显示 */}
          {selectedProviderIds.length === 1 && (
            <div className="config-row">
              <span className="config-label">模型</span>
              <select
                value={route.model || ""}
                onChange={(e) =>
                  dispatch({
                    type: "UPDATE_ROUTE",
                    capKey: cap.key,
                    field: "model",
                    value: e.target.value || null,
                  })
                }
                className="config-select"
              >
                <option value="">使用服务商默认</option>
                {getProviderModels(selectedProviderIds[0]).map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* 超时设置 */}
          <div className="config-row timeout">
            <span className="config-label">超时</span>
            <input
              type="number"
              value={route.timeout || cap.defaultTimeout}
              min={10}
              max={300}
              step={10}
              onChange={(e) =>
                dispatch({
                  type: "UPDATE_ROUTE",
                  capKey: cap.key,
                  field: "timeout",
                  value: parseInt(e.target.value) || cap.defaultTimeout,
                })
              }
              className="timeout-input"
            />
            <span className="timeout-unit">秒</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="section-page">
      <SectionHeader
        icon="🤖"
        title="智能路由"
        subtitle="为不同 AI 能力分配专用模型，优化性能与成本"
      />

      {/* 全局默认配置 */}
      <Card title="全局默认" icon="🌐" desc="未单独配置的能力将使用此设置">
        <div className="global-config-panel">
          <div className="global-config-grid">
            <SelectRow
              label="默认服务商"
              value={aiProvider || ""}
              options={[
                { value: "", label: "请选择服务商" },
                ...providerList.map(p => ({ value: p.id, label: `${getProviderLogo(p)} ${p.name}` }))
              ]}
              onChange={(v) => dispatch({ type: "UPDATE_GLOBAL", field: "ai_provider", value: v || null })}
            />

            <SelectRow
              label="默认模型"
              value={aiModel || ""}
              options={[
                { value: "", label: "请选择模型" },
                ...(aiProvider ? getProviderModels(aiProvider).map(m => ({ value: m, label: m })) : [])
              ]}
              onChange={(v) => dispatch({ type: "UPDATE_GLOBAL", field: "ai_model", value: v || null })}
              disabled={!aiProvider}
              placeholder={!aiProvider ? "需先选择服务商" : "请选择模型"}
            />

            <NumberInput
              label="默认超时"
              value={aiTimeout}
              min={10}
              max={300}
              step={10}
              onChange={(v) => dispatch({ type: "UPDATE_GLOBAL", field: "ai_timeout", value: v || 60 })}
              suffix="秒"
            />
          </div>

          {!aiProvider && (
            <div className="config-warning">
              ⚠️ 请先选择默认服务商，否则 AI 功能将无法正常使用
            </div>
          )}
        </div>
      </Card>

      {/* 能力分组 */}
      {CAPABILITY_GROUPS.map((group) => {
        const capabilities = AI_CAPABILITIES[group.key] || [];
        if (capabilities.length === 0) return null;

        return (
          <div key={group.key} className="capability-group">
            <div className="group-header" style={{ borderLeftColor: group.color, background: `linear-gradient(90deg, ${group.color}1a, transparent)` }}>
              <div className="group-icon" style={{ color: group.color }}>{group.icon}</div>
              <div className="group-title-area">
                <h3 className="group-title">{group.title}</h3>
                <p className="group-desc">{group.desc}</p>
              </div>
              <div className="group-count">{capabilities.length} 项</div>
            </div>
            <div className="capabilities-grid">
              {capabilities.map((cap) => renderCapabilityCard(cap, group.color))}
            </div>
          </div>
        );
      })}

      {/* 配置建议 */}
      <InfoBox variant="warning" title="配置建议">
        <ul style={{ margin: 0, paddingLeft: "18px", lineHeight: 1.8 }}>
          <li><strong>核心能力</strong>：建议使用高质量模型（如 GPT-4o、Claude-3.5）</li>
          <li><strong>批量任务</strong>：可使用性价比高的模型（如 DeepSeek、Qwen）</li>
          <li><strong>超时设置</strong>：思考模型（R1等）建议 120-180 秒</li>
        </ul>
      </InfoBox>
    </div>
  );
});
