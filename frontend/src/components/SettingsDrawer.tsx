import { useState } from "react";
import type { UIConfig, ProviderConfig, CapabilityRouteConfig } from "../services/api.types";
import { testApiConnection } from "../services/api";
import { GamePanel } from "./common/GamePanel";
import "./SettingsDrawer.css";

interface Props {
  config: UIConfig;
  onClose: () => void;
  onSave: (config: UIConfig) => void;
}

const PROVIDER_TYPES = ["openai", "deepseek", "anthropic", "custom", "local"];
type Tab = "connection" | "models" | "memory";

// 预设服务商模板
const PROVIDER_PRESETS = [
  {
    id: "deepseek_official",
    name: "DeepSeek 官方",
    type: "openai",
    base_url: "https://api.deepseek.com",
    description: "DeepSeek 官方 API（支持 deepseek-chat, deepseek-reasoner 等模型）",
    models: ["deepseek-chat", "deepseek-reasoner"],
  },
  {
    id: "siliconflow",
    name: "硅基流动 ⚡",
    type: "openai",
    base_url: "https://api.siliconflow.cn/v1",
    description: "硅基流动 API（支持多种开源模型，支持思维链功能 🧠）",
    models: ["Pro/deepseek-ai/DeepSeek-V3.2-Exp"],
  },
  {
    id: "volcengine",
    name: "火山引擎（豆包）⚡",
    type: "openai",
    base_url: "https://ark.cn-beijing.volces.com/api/v3",
    description: "火山引擎 API（支持思维链功能 🧠，需要填写端点ID作为模型名）",
    models: [],
  },
  {
    id: "openai_official",
    name: "OpenAI 官方",
    type: "openai",
    base_url: "https://api.openai.com/v1",
    description: "OpenAI 官方 API（ChatGPT）",
    models: ["gpt-4.1"],
  },
  {
    id: "anthropic_proxy",
    name: "Claude (OpenAI 兼容)",
    type: "openai",
    base_url: "https://api.anthropic.com/v1",
    description: "Claude API（需使用支持 OpenAI 格式的代理）",
    models: ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
  },
  {
    id: "gemini_proxy",
    name: "Gemini (OpenAI 兼容)",
    type: "openai",
    base_url: "https://generativelanguage.googleapis.com/v1beta/openai",
    description: "Google Gemini API（OpenAI 兼容格式）",
    models: ["gemini-2.5-flash", "gemini-2.5-pro"],
  },
] as const;

// AI 能力列表定义
const AI_CAPABILITIES = [
  { key: "turn_report", label: "主推演叙事", priority: "high", desc: "负责生成每个回合的总体生态演化报告" },
  { key: "focus_batch", label: "重点批次推演", priority: "high", desc: "处理关键物种的具体生存判定" },
  { key: "critical_detail", label: "关键物种分析", priority: "high", desc: "分析濒危或优势物种的详细状态" },
  { key: "speciation", label: "物种分化", priority: "medium", desc: "判定新物种的诞生条件与特征" },
  { key: "migration", label: "迁徙建议", priority: "low", desc: "计算物种在不同地块间的移动" },
  { key: "pressure_escalation", label: "压力升级", priority: "low", desc: "动态调整环境生存压力" },
  { key: "reemergence", label: "物种重现/起名", priority: "low", desc: "为新物种生成名称与描述" },
  { key: "species_generation", label: "物种生成", priority: "medium", desc: "生成初始物种或新物种" },
] as const;

// 简单的 ID 生成器
const generateId = () => Math.random().toString(36).substr(2, 9);

export function SettingsDrawer({ config, onClose, onSave }: Props) {
  // 确保 providers 即使为空也是对象，并添加默认预设服务商
  const getInitialProviders = () => {
    const providers = config.providers || {};
    
    // 如果没有任何服务商，添加预设服务商
    if (Object.keys(providers).length === 0) {
      const presetProviders: Record<string, ProviderConfig> = {};
      
      PROVIDER_PRESETS.forEach((preset) => {
        presetProviders[preset.id] = {
          id: preset.id,
          name: preset.name,
          type: preset.type,
          base_url: preset.base_url,
          api_key: "",
          models: [...preset.models]
        };
      });
      
      return presetProviders;
    }
    
    return providers;
  };
  
  const initialConfig = {
    ...config,
    providers: getInitialProviders(),
    capability_routes: config.capability_routes || {},
  };

  const [form, setForm] = useState<UIConfig>(initialConfig);
  const [tab, setTab] = useState<Tab>("connection");
  
  // UI States
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(
    Object.keys(initialConfig.providers)[0] || null
  );

  // Testing States
  const [testingProviderId, setTestingProviderId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  
  const [testingEmbedding, setTestingEmbedding] = useState(false);
  const [testResultEmbedding, setTestResultEmbedding] = useState<{ success: boolean; message: string; details?: string } | null>(null);
  
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // --- Actions ---

  function addCustomProvider() {
    const newId = generateId();
    const newProvider: ProviderConfig = {
      id: newId,
      name: "自定义服务商",
      type: "openai",
      models: []
    };
    setForm(prev => ({
      ...prev,
      providers: { ...prev.providers, [newId]: newProvider }
    }));
    setSelectedProviderId(newId);
  }

  function removeProvider(id: string) {
    const isPreset = PROVIDER_PRESETS.some(preset => preset.id === id);
    
    if (isPreset) {
      if (!confirm("这是预设服务商，删除后下次打开设置将重新出现。确定要删除吗？")) return;
    } else {
      if (!confirm("确定要删除这个服务商吗？相关的路由配置将失效。")) return;
    }
    
    setForm(prev => {
      const newProviders = { ...prev.providers };
      delete newProviders[id];
      return { ...prev, providers: newProviders };
    });
    
    if (selectedProviderId === id) {
      setSelectedProviderId(null);
    }
  }

  function updateProvider(id: string, field: keyof ProviderConfig, value: any) {
    setForm(prev => ({
      ...prev,
      providers: {
        ...prev.providers,
        [id]: { ...prev.providers[id], [field]: value }
      }
    }));
  }

  function updateGlobalDefault(field: "default_provider_id" | "default_model", value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  function updateRoute(capKey: string, field: keyof CapabilityRouteConfig, value: any) {
    setForm(prev => {
      const currentRoute = prev.capability_routes[capKey] || { timeout: 60 };
      return {
        ...prev,
        capability_routes: {
          ...prev.capability_routes,
          [capKey]: { ...currentRoute, [field]: value }
        }
      };
    });
  }

  async function handleTestProvider(providerId: string) {
    const provider = form.providers[providerId];
    if (!provider || !provider.base_url || !provider.api_key) {
      setTestResults(prev => ({ ...prev, [providerId]: { success: false, message: "请先填写完整配置" } }));
      return;
    }

    setTestingProviderId(providerId);
    setTestResults(prev => {
      const next = { ...prev };
      delete next[providerId];
      return next;
    });

    try {
      const testModel = form.default_model || "Pro/deepseek-ai/DeepSeek-V3.2-Exp";
      
      const result = await testApiConnection({
        type: "chat",
        base_url: provider.base_url,
        api_key: provider.api_key,
        provider: provider.type,
        model: testModel
      });
      setTestResults(prev => ({ ...prev, [providerId]: { success: result.success, message: result.message } }));
    } catch (e) {
      setTestResults(prev => ({ ...prev, [providerId]: { success: false, message: String(e) } }));
    } finally {
      setTestingProviderId(null);
    }
  }

  async function handleTestEmbedding() {
    const providerId = form.embedding_provider_id;
    const effectiveProviderId = providerId || form.default_provider_id;
    const provider = effectiveProviderId ? form.providers[effectiveProviderId] : null;
    
    const baseUrl = provider?.base_url || form.embedding_base_url;
    const apiKey = provider?.api_key || form.embedding_api_key;
    const model = form.embedding_model || "Qwen/Qwen3-Embedding-4B";

    if (!baseUrl || !apiKey) {
      setTestResultEmbedding({ success: false, message: "请先填写配置或选择有效的服务商" });
      return;
    }
    
    setTestingEmbedding(true);
    setTestResultEmbedding(null);
    
    try {
      const result = await testApiConnection({
        type: "embedding",
        base_url: baseUrl,
        api_key: apiKey,
        model: model,
      });
      setTestResultEmbedding(result);
    } catch (error) {
      setTestResultEmbedding({ success: false, message: "失败：" + String(error) });
    } finally {
      setTestingEmbedding(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaveSuccess(false);
    try {
      await onSave(form);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error("保存配置失败:", error);
      alert("保存配置失败：" + String(error));
    } finally {
      setSaving(false);
    }
  }

  const providerList = Object.values(form.providers);
  const selectedProvider = selectedProviderId ? form.providers[selectedProviderId] : null;

  // 判断是否支持思维链
  const supportsThinking = (provider: ProviderConfig | null) => {
    return provider?.base_url && (
      provider.base_url.includes("siliconflow") || 
      provider.base_url.includes("volces.com")
    );
  };

  // 获取配置提示
  const getProviderTip = (baseUrl: string) => {
    if (baseUrl.includes("deepseek.com")) return "DeepSeek 官方 API，支持 deepseek-chat 和 deepseek-reasoner 模型。";
    if (baseUrl.includes("siliconflow")) return "硅基流动支持多种开源模型。✨ 支持思维链功能，可在功能路由中开启。";
    if (baseUrl.includes("volces.com")) return "火山引擎需要在模型名处填写端点 ID（如 ep-xxxxx）。✨ 支持思维链功能。";
    if (baseUrl.includes("openai.com")) return "OpenAI 官方 API，支持 GPT 系列模型。";
    if (baseUrl.includes("anthropic.com")) return "Claude API，需确保代理支持 OpenAI 格式。";
    if (baseUrl.includes("generativelanguage.googleapis.com")) return "Google Gemini API，使用 OpenAI 兼容端点。";
    return "请确保 API 端点支持 OpenAI 兼容格式。";
  };

  return (
    <GamePanel
      title="系统设置"
      onClose={onClose}
      variant="modal"
      width="clamp(600px, 80vw, 1200px)"
      height="clamp(500px, 80vh, 900px)"
      icon={<span>⚙️</span>}
    >
      <div className="settings-container">
        {/* Sidebar Navigation */}
        <nav className="settings-nav">
          <div className="nav-items">
            <NavButton 
              active={tab === "connection"} 
              onClick={() => setTab("connection")} 
              icon="🔌" 
              label="服务商管理" 
              desc="配置 AI 接入点"
            />
            <NavButton 
              active={tab === "models"} 
              onClick={() => setTab("models")} 
              icon="🧠" 
              label="功能路由" 
              desc="分配模型任务"
            />
            <NavButton 
              active={tab === "memory"} 
              onClick={() => setTab("memory")} 
              icon="🧬" 
              label="向量记忆" 
              desc="Embedding 设置"
            />
          </div>
        </nav>

        {/* Content Area */}
        <div className="settings-content">
          
          {/* TAB 1: PROVIDERS */}
          {tab === "connection" && (
            <div className="tab-content fade-in">
              <div className="providers-layout">
                {/* Left: Provider List */}
                <div className="provider-list-panel">
                  <h4 className="panel-title">服务商列表</h4>
                  <div className="provider-list">
                    {providerList.map(p => {
                      const isPreset = !p.api_key;
                      const hasThinking = supportsThinking(p);
                      
                      return (
                        <div 
                          key={p.id}
                          className={`provider-item ${selectedProviderId === p.id ? 'active' : ''}`}
                          onClick={() => setSelectedProviderId(p.id)}
                        >
                          <div className="provider-item-header">
                            <span className="provider-name">{p.name}</span>
                            {hasThinking && <span className="badge-thinking">🧠</span>}
                          </div>
                          {isPreset && (
                            <div className="provider-warning">
                              <span>⚠️</span>
                              <span>需要配置 API Key</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  
                  <button onClick={addCustomProvider} className="btn-add-provider">
                    + 添加自定义服务商
                  </button>

                  <div className="global-defaults">
                    <label className="form-field">
                      <span className="field-label">全局默认服务商</span>
                      <select
                        className="field-input"
                        value={form.default_provider_id ?? ""}
                        onChange={(e) => updateGlobalDefault("default_provider_id", e.target.value)}
                      >
                        <option value="">未选择</option>
                        {providerList.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                      </select>
                    </label>
                    <label className="form-field">
                      <span className="field-label">默认模型</span>
                      <input
                        className="field-input"
                        value={form.default_model ?? ""}
                        onChange={(e) => updateGlobalDefault("default_model", e.target.value)}
                        placeholder="Pro/deepseek-ai/DeepSeek-V3.2-Exp"
                      />
                    </label>
                  </div>
                </div>

                {/* Right: Edit Form */}
                <div className="provider-edit-panel">
                  {selectedProvider ? (
                    <>
                      <div className="edit-header">
                        <div>
                          <h3>编辑服务商</h3>
                          {PROVIDER_PRESETS.some(p => p.id === selectedProviderId) && (
                            <span className="badge-preset">⭐ 预设服务商</span>
                          )}
                        </div>
                        <button 
                          onClick={() => selectedProviderId && removeProvider(selectedProviderId)}
                          className="btn-delete"
                        >
                          🗑️ 删除
                        </button>
                      </div>

                      {selectedProvider.base_url && (
                        <div className="tip-box">
                          💡 <strong>配置提示：</strong>
                          {getProviderTip(selectedProvider.base_url)}
                        </div>
                      )}

                      <div className="form-fields">
                        <label className="form-field">
                          <span className="field-label">名称 (Display Name)</span>
                          <input
                            className="field-input"
                            value={selectedProvider.name}
                            onChange={(e) => selectedProviderId && updateProvider(selectedProviderId, "name", e.target.value)}
                            placeholder="My AI Provider"
                          />
                        </label>

                        <label className="form-field">
                          <span className="field-label">类型 (Type)</span>
                          <select
                            className="field-input"
                            value={selectedProvider.type}
                            onChange={(e) => selectedProviderId && updateProvider(selectedProviderId, "type", e.target.value)}
                          >
                            {PROVIDER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                          </select>
                        </label>

                        <label className="form-field">
                          <span className="field-label">Base URL</span>
                          <input
                            className="field-input"
                            value={selectedProvider.base_url ?? ""}
                            onChange={(e) => selectedProviderId && updateProvider(selectedProviderId, "base_url", e.target.value)}
                            placeholder="https://api.openai.com/v1"
                          />
                        </label>

                        <label className="form-field">
                          <span className="field-label">API Key</span>
                          <input
                            className="field-input"
                            type="password"
                            value={selectedProvider.api_key ?? ""}
                            onChange={(e) => selectedProviderId && updateProvider(selectedProviderId, "api_key", e.target.value)}
                            placeholder="sk-..."
                          />
                        </label>
                      </div>

                      <div className="test-section">
                        <div className="test-row">
                          <button
                            onClick={() => selectedProviderId && handleTestProvider(selectedProviderId)}
                            disabled={testingProviderId === selectedProviderId}
                            className="btn-primary btn-test"
                          >
                            {testingProviderId === selectedProviderId ? (
                              <><span className="spinner-small"></span> 连接中...</>
                            ) : "🔌 测试连接"}
                          </button>
                          <span className="test-hint">(使用默认模型)</span>
                        </div>
                        
                        {selectedProviderId && testResults[selectedProviderId] && (
                          <div className={`test-result ${testResults[selectedProviderId].success ? 'success' : 'error'}`}>
                            <span>{testResults[selectedProviderId].success ? "✅" : "❌"}</span>
                            <span>{testResults[selectedProviderId].message}</span>
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="empty-state">
                      请选择或添加一个服务商
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: MODELS (Routing) */}
          {tab === "models" && (
            <div className="tab-content fade-in">
              <div className="section-header">
                <h3>大脑皮层：功能路由</h3>
                <p>为每个具体的认知功能指定专用服务商与模型。</p>
              </div>
              
              <div className="capabilities-grid">
                {AI_CAPABILITIES.map((cap) => {
                  const route = form.capability_routes[cap.key] || {};
                  
                  const routeProvider = route.provider_id 
                    ? form.providers[route.provider_id] 
                    : (form.default_provider_id ? form.providers[form.default_provider_id] : null);
                  
                  const hasThinking = supportsThinking(routeProvider);
                  
                  return (
                    <div key={cap.key} className="capability-card">
                      <div className="capability-header">
                        <strong>{cap.label}</strong>
                        <span className={`priority-badge ${cap.priority}`}>
                          {cap.priority === "high" ? "高优" : cap.priority === "medium" ? "中等" : "普通"}
                        </span>
                      </div>
                      <p className="capability-desc">{cap.desc}</p>
                      
                      <div className="capability-controls">
                        <select
                          className="field-input"
                          value={route.provider_id ?? ""}
                          onChange={(e) => {
                            const newProviderId = e.target.value || null;
                            updateRoute(cap.key, "provider_id", newProviderId);
                            
                            const newProvider = newProviderId 
                              ? form.providers[newProviderId] 
                              : (form.default_provider_id ? form.providers[form.default_provider_id] : null);
                            
                            if (!supportsThinking(newProvider) && route.enable_thinking) {
                              updateRoute(cap.key, "enable_thinking", false);
                            }
                          }}
                        >
                          <option value="">默认 ({form.default_provider_id ? (form.providers[form.default_provider_id]?.name || "Unknown") : "未设置"})</option>
                          {providerList.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          ))}
                        </select>

                        <input
                          className="field-input"
                          type="text"
                          placeholder={`模型 (默认: ${form.default_model || "未设置"})`}
                          value={route.model || ""}
                          onChange={(e) => updateRoute(cap.key, "model", e.target.value)}
                        />

                        {hasThinking && (
                          <>
                            {!route.enable_thinking && (
                              <div className="thinking-hint">
                                <span>💡</span>
                                <span>此服务商支持思维链，开启可得到更精准的结果</span>
                              </div>
                            )}
                            
                            <label className="thinking-toggle">
                              <input
                                type="checkbox"
                                checked={route.enable_thinking || false}
                                onChange={(e) => updateRoute(cap.key, "enable_thinking", e.target.checked)}
                              />
                              <span>开启思考模式 🧠</span>
                            </label>
                          </>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* TAB 3: MEMORY */}
          {tab === "memory" && (
            <div className="tab-content fade-in">
              <div className="section-header">
                <h3>海马体：向量记忆</h3>
              </div>
              
              <div className="memory-content">
                <div className="tip-box info">
                  向量服务通常需要 Qwen/Qwen3-Embedding-4B 或类似模型。请确保选择的服务商支持 Embedding 接口。
                </div>

                <div className="form-fields">
                  <label className="form-field">
                    <span className="field-label">服务商 (Provider)</span>
                    <select
                      className="field-input"
                      value={form.embedding_provider_id ?? ""}
                      onChange={(e) => setForm(prev => ({ ...prev, embedding_provider_id: e.target.value || null }))}
                    >
                      <option value="">使用全局默认</option>
                      {providerList.map(p => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </label>

                  <label className="form-field">
                    <span className="field-label">Embedding 模型</span>
                    <input
                      className="field-input"
                      type="text"
                      value={form.embedding_model ?? ""}
                      onChange={(e) => setForm(prev => ({ ...prev, embedding_model: e.target.value }))}
                      placeholder="Qwen/Qwen3-Embedding-4B"
                    />
                  </label>
                </div>
                
                <div className="test-section">
                  <button
                    type="button"
                    onClick={handleTestEmbedding}
                    disabled={testingEmbedding}
                    className="btn-primary btn-test full-width"
                  >
                    {testingEmbedding ? "🔄 连接中..." : "🧬 测试向量服务"}
                  </button>
                  
                  {testResultEmbedding && (
                    <div className={`test-result ${testResultEmbedding.success ? 'success' : 'error'}`}>
                      <div className="result-header">
                        <span>{testResultEmbedding.success ? "✅ 连接成功" : "❌ 连接失败"}</span>
                      </div>
                      {testResultEmbedding.details && (
                        <div className="result-details">{testResultEmbedding.details}</div>
                      )}
                      {!testResultEmbedding.success && testResultEmbedding.message && (
                        <div className="result-details">{testResultEmbedding.message}</div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          
          {/* Footer Actions */}
          <div className="settings-footer">
            {saveSuccess && (
              <div className="save-success">✅ 配置已保存</div>
            )}
            <div className="footer-buttons">
              <button onClick={onClose} className="btn-secondary">取消</button>
              <button onClick={handleSave} className="btn-primary" disabled={saving}>
                {saving ? "保存中..." : "保存配置"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </GamePanel>
  );
}

function NavButton({ active, onClick, icon, label, desc }: { active: boolean; onClick: () => void; icon: string; label: string; desc: string }) {
  return (
    <button
      onClick={onClick}
      className={`nav-button ${active ? 'active' : ''}`}
    >
      <span className="nav-icon">{icon}</span>
      <div className="nav-text">
        <div className="nav-label">{label}</div>
        <div className="nav-desc">{desc}</div>
      </div>
    </button>
  );
}
