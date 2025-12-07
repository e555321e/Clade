/**
 * GeneEditorTab - 基因编辑标签页组件
 *
 * 在物种详情模态框中显示和管理休眠基因
 * 功能：
 * - 查看当前休眠基因库（特质和器官）
 * - 手动添加新的休眠基因
 * - 手动激活休眠基因
 * - 删除未激活的休眠基因
 */

import { useState, useCallback } from "react";
import {
  Dna,
  Plus,
  Zap,
  Trash2,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  Clock,
  Target,
  Loader2,
} from "lucide-react";

import type { SpeciesDetail, DormantGenes, DormantGeneData } from "@/services/api.types";
import {
  addDormantGene,
  activateDormantGene,
  removeDormantGene,
} from "@/services/api";
import "./GeneEditorTab.css";

interface Props {
  species: SpeciesDetail;
  onSpeciesUpdate: (species: SpeciesDetail) => void;
}

// 压力类型选项
const PRESSURE_TYPE_OPTIONS = [
  { value: "temperature", label: "温度" },
  { value: "drought", label: "干旱" },
  { value: "cold", label: "寒冷" },
  { value: "toxin", label: "毒性" },
  { value: "predation", label: "捕食" },
  { value: "competition", label: "竞争" },
  { value: "disease", label: "疾病" },
  { value: "radiation", label: "辐射" },
  { value: "anoxic", label: "缺氧" },
  { value: "salinity", label: "盐度" },
];

// 器官类别选项
const ORGAN_CATEGORY_OPTIONS = [
  { value: "sensory", label: "感知器官" },
  { value: "locomotion", label: "运动器官" },
  { value: "defense", label: "防御器官" },
  { value: "digestion", label: "消化器官" },
  { value: "respiration", label: "呼吸器官" },
  { value: "reproduction", label: "生殖器官" },
  { value: "other", label: "其他" },
];

export function GeneEditorTab({ species, onSpeciesUpdate }: Props) {
  const [expandedTraits, setExpandedTraits] = useState(true);
  const [expandedOrgans, setExpandedOrgans] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 添加基因表单状态
  const [addForm, setAddForm] = useState({
    gene_type: "trait" as "trait" | "organ",
    name: "",
    potential_value: 7,
    pressure_types: [] as string[],
    organ_category: "sensory",
    organ_type: "custom",
  });

  const dormantGenes: DormantGenes = species.dormant_genes || {
    traits: {},
    organs: {},
  };

  const traitEntries = Object.entries(dormantGenes.traits || {});
  const organEntries = Object.entries(dormantGenes.organs || {});

  const activatedTraitsCount = traitEntries.filter(
    ([, g]) => g.activated
  ).length;
  const activatedOrgansCount = organEntries.filter(
    ([, g]) => g.activated
  ).length;

  // 切换压力类型选择
  const togglePressureType = (type: string) => {
    setAddForm((prev) => ({
      ...prev,
      pressure_types: prev.pressure_types.includes(type)
        ? prev.pressure_types.filter((t) => t !== type)
        : [...prev.pressure_types, type],
    }));
  };

  // 添加基因
  const handleAddGene = useCallback(async () => {
    if (!addForm.name.trim()) {
      setError("请输入基因名称");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const params =
        addForm.gene_type === "trait"
          ? {
              gene_type: "trait" as const,
              name: addForm.name.trim(),
              potential_value: addForm.potential_value,
              pressure_types:
                addForm.pressure_types.length > 0
                  ? addForm.pressure_types
                  : undefined,
            }
          : {
              gene_type: "organ" as const,
              name: addForm.name.trim(),
              pressure_types:
                addForm.pressure_types.length > 0
                  ? addForm.pressure_types
                  : undefined,
              organ_data: {
                category: addForm.organ_category,
                type: addForm.organ_type,
                parameters: {},
              },
            };

      const updated = await addDormantGene(species.lineage_code, params);
      onSpeciesUpdate(updated);
      setShowAddForm(false);
      setAddForm({
        gene_type: "trait",
        name: "",
        potential_value: 7,
        pressure_types: [],
        organ_category: "sensory",
        organ_type: "custom",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "添加失败");
    } finally {
      setIsLoading(false);
    }
  }, [addForm, species.lineage_code, onSpeciesUpdate]);

  // 激活基因
  const handleActivate = useCallback(
    async (geneType: "trait" | "organ", name: string) => {
      setIsLoading(true);
      setError(null);

      try {
        const updated = await activateDormantGene(
          species.lineage_code,
          geneType,
          name
        );
        onSpeciesUpdate(updated);
      } catch (err) {
        setError(err instanceof Error ? err.message : "激活失败");
      } finally {
        setIsLoading(false);
      }
    },
    [species.lineage_code, onSpeciesUpdate]
  );

  // 删除基因
  const handleRemove = useCallback(
    async (geneType: "trait" | "organ", name: string) => {
      if (!confirm(`确定要删除休眠${geneType === "trait" ? "特质" : "器官"} "${name}" 吗？`)) {
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const updated = await removeDormantGene(
          species.lineage_code,
          geneType,
          name
        );
        onSpeciesUpdate(updated);
      } catch (err) {
        setError(err instanceof Error ? err.message : "删除失败");
      } finally {
        setIsLoading(false);
      }
    },
    [species.lineage_code, onSpeciesUpdate]
  );

  // 渲染基因状态徽章
  const renderGeneStatus = (gene: DormantGeneData) => {
    if (gene.activated) {
      return (
        <span className="get-status-badge activated">
          <CheckCircle2 size={12} />
          已激活
          {gene.activated_turn != null && ` (第${gene.activated_turn + 1}回合)`}
        </span>
      );
    }
    return (
      <span className="get-status-badge dormant">
        <Clock size={12} />
        休眠中
      </span>
    );
  };

  // 渲染基因列表项
  const renderGeneItem = (
    name: string,
    gene: DormantGeneData,
    type: "trait" | "organ"
  ) => {
    const isTrait = type === "trait";

    return (
      <div key={name} className={`get-gene-item ${gene.activated ? "activated" : ""}`}>
        <div className="get-gene-header">
          <div className="get-gene-name">
            <span className="get-gene-icon">{isTrait ? "🧬" : "🔬"}</span>
            <span>{name}</span>
          </div>
          {renderGeneStatus(gene)}
        </div>

        <div className="get-gene-details">
          {isTrait && gene.potential_value != null && (
            <div className="get-gene-stat">
              <span className="get-stat-label">潜力值</span>
              <span className="get-stat-value">{gene.potential_value.toFixed(1)}</span>
            </div>
          )}

          {!isTrait && gene.organ_data && (
            <div className="get-gene-stat">
              <span className="get-stat-label">类别</span>
              <span className="get-stat-value">
                {ORGAN_CATEGORY_OPTIONS.find((o) => o.value === gene.organ_data?.category)?.label ||
                  gene.organ_data.category}
              </span>
            </div>
          )}

          {gene.pressure_types && gene.pressure_types.length > 0 && (
            <div className="get-gene-stat">
              <span className="get-stat-label">触发压力</span>
              <span className="get-stat-value get-pressure-tags">
                {gene.pressure_types.map((p) => (
                  <span key={p} className="get-pressure-tag">
                    {PRESSURE_TYPE_OPTIONS.find((o) => o.value === p)?.label || p}
                  </span>
                ))}
              </span>
            </div>
          )}

          {gene.exposure_count != null && gene.exposure_count > 0 && (
            <div className="get-gene-stat">
              <Target size={12} />
              <span className="get-stat-label">暴露</span>
              <span className="get-stat-value">{gene.exposure_count}次</span>
            </div>
          )}
        </div>

        {!gene.activated && (
          <div className="get-gene-actions">
            <button
              className="get-action-btn activate"
              onClick={() => handleActivate(type, name)}
              disabled={isLoading}
              title="手动激活此基因"
            >
              <Zap size={14} />
              激活
            </button>
            <button
              className="get-action-btn delete"
              onClick={() => handleRemove(type, name)}
              disabled={isLoading}
              title="删除此休眠基因"
            >
              <Trash2 size={14} />
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="gene-editor-tab">
      {/* 基因多样性状态 */}
      <div className="get-diversity-status">
        <div className="get-diversity-header">
          <Dna size={18} />
          <span>基因多样性状态</span>
        </div>
        <div className="get-diversity-stats">
          <div className="get-diversity-stat">
            <span className="get-diversity-label">多样性半径</span>
            <span className="get-diversity-value">
              {(species.gene_diversity_radius ?? 0).toFixed(3)}
            </span>
          </div>
          <div className="get-diversity-stat">
            <span className="get-diversity-label">稳定性</span>
            <span className="get-diversity-value">
              {(species.gene_stability ?? 0.5).toFixed(2)}
            </span>
          </div>
          <div className="get-diversity-stat">
            <span className="get-diversity-label">已探索方向</span>
            <span className="get-diversity-value">
              {species.explored_directions?.length ?? 0}
            </span>
          </div>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="get-error">
          <AlertCircle size={16} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* 加载状态 */}
      {isLoading && (
        <div className="get-loading">
          <Loader2 size={16} className="spin" />
          <span>处理中...</span>
        </div>
      )}

      {/* 添加基因按钮 */}
      <button
        className="get-add-btn"
        onClick={() => setShowAddForm(!showAddForm)}
      >
        <Plus size={16} />
        添加休眠基因
      </button>

      {/* 添加基因表单 */}
      {showAddForm && (
        <div className="get-add-form">
          <div className="get-form-row">
            <label>基因类型</label>
            <div className="get-radio-group">
              <label className={addForm.gene_type === "trait" ? "active" : ""}>
                <input
                  type="radio"
                  name="gene_type"
                  value="trait"
                  checked={addForm.gene_type === "trait"}
                  onChange={() => setAddForm((p) => ({ ...p, gene_type: "trait" }))}
                />
                特质
              </label>
              <label className={addForm.gene_type === "organ" ? "active" : ""}>
                <input
                  type="radio"
                  name="gene_type"
                  value="organ"
                  checked={addForm.gene_type === "organ"}
                  onChange={() => setAddForm((p) => ({ ...p, gene_type: "organ" }))}
                />
                器官
              </label>
            </div>
          </div>

          <div className="get-form-row">
            <label>名称</label>
            <input
              type="text"
              value={addForm.name}
              onChange={(e) => setAddForm((p) => ({ ...p, name: e.target.value }))}
              placeholder={addForm.gene_type === "trait" ? "例如: 强化耐热性" : "例如: 热感受器"}
              maxLength={50}
            />
          </div>

          {addForm.gene_type === "trait" && (
            <div className="get-form-row">
              <label>潜力值 (0-15)</label>
              <input
                type="range"
                min={0}
                max={15}
                step={0.5}
                value={addForm.potential_value}
                onChange={(e) =>
                  setAddForm((p) => ({ ...p, potential_value: parseFloat(e.target.value) }))
                }
              />
              <span className="get-range-value">{addForm.potential_value.toFixed(1)}</span>
            </div>
          )}

          {addForm.gene_type === "organ" && (
            <div className="get-form-row">
              <label>器官类别</label>
              <select
                value={addForm.organ_category}
                onChange={(e) => setAddForm((p) => ({ ...p, organ_category: e.target.value }))}
              >
                {ORGAN_CATEGORY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="get-form-row">
            <label>触发压力类型（可选）</label>
            <div className="get-pressure-options">
              {PRESSURE_TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`get-pressure-option ${
                    addForm.pressure_types.includes(opt.value) ? "selected" : ""
                  }`}
                  onClick={() => togglePressureType(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="get-form-actions">
            <button
              className="get-form-btn cancel"
              onClick={() => setShowAddForm(false)}
            >
              取消
            </button>
            <button
              className="get-form-btn confirm"
              onClick={handleAddGene}
              disabled={isLoading || !addForm.name.trim()}
            >
              添加
            </button>
          </div>
        </div>
      )}

      {/* 休眠特质列表 */}
      <div className="get-section">
        <button
          className="get-section-header"
          onClick={() => setExpandedTraits(!expandedTraits)}
        >
          {expandedTraits ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span className="get-section-title">🧬 休眠特质库</span>
          <span className="get-section-count">
            {activatedTraitsCount}/{traitEntries.length} 已激活
          </span>
        </button>

        {expandedTraits && (
          <div className="get-gene-list">
            {traitEntries.length === 0 ? (
              <div className="get-empty">暂无休眠特质</div>
            ) : (
              traitEntries.map(([name, gene]) => renderGeneItem(name, gene, "trait"))
            )}
          </div>
        )}
      </div>

      {/* 休眠器官列表 */}
      <div className="get-section">
        <button
          className="get-section-header"
          onClick={() => setExpandedOrgans(!expandedOrgans)}
        >
          {expandedOrgans ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span className="get-section-title">🔬 休眠器官库</span>
          <span className="get-section-count">
            {activatedOrgansCount}/{organEntries.length} 已激活
          </span>
        </button>

        {expandedOrgans && (
          <div className="get-gene-list">
            {organEntries.length === 0 ? (
              <div className="get-empty">暂无休眠器官</div>
            ) : (
              organEntries.map(([name, gene]) => renderGeneItem(name, gene, "organ"))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default GeneEditorTab;
