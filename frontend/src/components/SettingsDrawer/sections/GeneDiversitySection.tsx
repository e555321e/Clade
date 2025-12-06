/**
 * GeneDiversitySection - 基因多样性配置
 * 控制基于 Embedding 的基因多样性半径机制
 */

import { memo, type Dispatch } from "react";
import type { GeneDiversityConfig } from "@/services/api.types";
import type { SettingsAction } from "../types";
import { SectionHeader, Card, ConfigGroup, SliderRow, NumberInput, ActionButton, InfoBox } from "../common/Controls";
import { DEFAULT_GENE_DIVERSITY_CONFIG } from "../constants";

interface Props {
  config: GeneDiversityConfig;
  dispatch: Dispatch<SettingsAction>;
}

export const GeneDiversitySection = memo(function GeneDiversitySection({
  config,
  dispatch,
}: Props) {
  const handleUpdate = (updates: Partial<GeneDiversityConfig>) => {
    dispatch({ type: "UPDATE_GENE_DIVERSITY", updates });
  };

  const handleReset = () => {
    dispatch({ type: "RESET_GENE_DIVERSITY" });
  };

  const c = { ...DEFAULT_GENE_DIVERSITY_CONFIG, ...config };

  return (
    <div className="section-page">
      <SectionHeader
        icon="🧬"
        title="基因多样性配置"
        subtitle="控制物种的演化潜力与基因库范围"
        actions={<ActionButton label="恢复默认" onClick={handleReset} variant="ghost" icon="↻" />}
      />

      {/* 概念说明 */}
      <InfoBox variant="info" title="什么是基因多样性？">
        基因多样性代表物种在 Embedding 空间中的"可演化范围"。半径越大，物种能够演化的方向越多，适应新环境的能力越强。
        当种群经历瓶颈（如大灭绝后幸存）时，基因多样性会减少；而杂交、突变发现等事件会增加多样性。
      </InfoBox>

      {/* 基础参数 */}
      <Card title="基础参数" icon="⚙️" desc="基因多样性的核心控制参数">
        <SliderRow
          label="最小半径"
          desc="物种的基因多样性不会低于此值，确保始终保有基本的演化能力"
          value={c.min_radius ?? 0.05}
          min={0.01}
          max={0.2}
          step={0.01}
          onChange={(v) => handleUpdate({ min_radius: v })}
          formatValue={(v) => v.toFixed(2)}
        />
        <SliderRow
          label="最大衰减率"
          desc="每回合基因多样性最多衰减的比例，防止半径瞬间归零"
          value={c.max_decay_per_turn ?? 0.05}
          min={0.01}
          max={0.15}
          step={0.01}
          onChange={(v) => handleUpdate({ max_decay_per_turn: v })}
          formatValue={(v) => `${(v * 100).toFixed(0)}%/回合`}
        />
        <SliderRow
          label="激活消耗"
          desc="每次激活休眠基因后，基因多样性半径会略微缩小"
          value={c.activation_cost ?? 0.02}
          min={0}
          max={0.1}
          step={0.005}
          onChange={(v) => handleUpdate({ activation_cost: v })}
          formatValue={(v) => `${(v * 100).toFixed(1)}%`}
        />
        <NumberInput
          label="瓶颈系数"
          desc="瓶颈衰减 = 系数 / sqrt(种群) × 压力系数。值越大，小种群衰减越快"
          value={c.bottleneck_coefficient ?? 50}
          min={10}
          max={200}
          step={5}
          onChange={(v) => handleUpdate({ bottleneck_coefficient: v })}
        />
        <NumberInput
          label="恢复阈值"
          desc="种群超过此值时，基因多样性开始正向增长"
          value={c.recovery_threshold ?? 50000}
          min={10000}
          max={200000}
          step={5000}
          onChange={(v) => handleUpdate({ recovery_threshold: v })}
          suffix="个体"
        />
      </Card>

      {/* 杂交与发现 */}
      <Card title="杂交与发现" icon="🔬" desc="杂交和新基因发现对多样性的影响">
        <InfoBox>
          杂交会显著增加基因多样性（基因重组），而新基因/器官的发现也会扩展物种的演化范围。
        </InfoBox>
        <ConfigGroup title="杂交半径提升">
          <SliderRow
            label="杂交提升（最小）"
            desc="杂交后代的基因多样性至少提升此比例"
            value={c.hybrid_bonus_min ?? 0.20}
            min={0.05}
            max={0.5}
            step={0.05}
            onChange={(v) => handleUpdate({ hybrid_bonus_min: v })}
            formatValue={(v) => `+${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="杂交提升（最大）"
            desc="杂交后代的基因多样性最多提升此比例"
            value={c.hybrid_bonus_max ?? 0.40}
            min={0.1}
            max={0.8}
            step={0.05}
            onChange={(v) => handleUpdate({ hybrid_bonus_max: v })}
            formatValue={(v) => `+${(v * 100).toFixed(0)}%`}
          />
        </ConfigGroup>
        <ConfigGroup title="新基因发现提升">
          <SliderRow
            label="发现提升（最小）"
            desc="发现新基因/器官时的半径提升下限"
            value={c.discovery_bonus_min ?? 0.05}
            min={0.01}
            max={0.2}
            step={0.01}
            onChange={(v) => handleUpdate({ discovery_bonus_min: v })}
            formatValue={(v) => `+${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="发现提升（最大）"
            desc="发现新基因/器官时的半径提升上限"
            value={c.discovery_bonus_max ?? 0.12}
            min={0.05}
            max={0.3}
            step={0.01}
            onChange={(v) => handleUpdate({ discovery_bonus_max: v })}
            formatValue={(v) => `+${(v * 100).toFixed(0)}%`}
          />
        </ConfigGroup>
      </Card>

      {/* 太古宙参数 */}
      <Card title="太古宙（第 1-50 回合）" icon="🌋" desc="生命起源时期，基因多样性快速积累">
        <InfoBox>
          太古宙是生命起源的时期，早期生物简单但基因潜力巨大。此阶段基因多样性增长最快，分化时继承也最完整。
        </InfoBox>
        <SliderRow
          label="初始半径"
          desc="太古宙新物种的初始基因多样性半径"
          value={c.archean_initial_radius ?? 0.50}
          min={0.3}
          max={0.8}
          step={0.05}
          onChange={(v) => handleUpdate({ archean_initial_radius: v })}
          formatValue={(v) => v.toFixed(2)}
        />
        <SliderRow
          label="增长率"
          desc="每回合基因多样性自然增长的比例"
          value={c.archean_growth_rate ?? 0.03}
          min={0.01}
          max={0.08}
          step={0.005}
          onChange={(v) => handleUpdate({ archean_growth_rate: v })}
          formatValue={(v) => `+${(v * 100).toFixed(1)}%/回合`}
        />
        <ConfigGroup title="分化继承系数">
          <SliderRow
            label="继承（最小）"
            desc="子种继承父种基因多样性的最小比例"
            value={c.archean_inherit_min ?? 0.95}
            min={0.7}
            max={1.0}
            step={0.01}
            onChange={(v) => handleUpdate({ archean_inherit_min: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="继承（最大）"
            desc="子种继承父种基因多样性的最大比例"
            value={c.archean_inherit_max ?? 1.00}
            min={0.8}
            max={1.0}
            step={0.01}
            onChange={(v) => handleUpdate({ archean_inherit_max: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
        </ConfigGroup>
        <SliderRow
          label="突变发现概率"
          desc="每回合发现新基因/扩展演化范围的概率"
          value={c.archean_mutation_chance ?? 0.15}
          min={0.05}
          max={0.3}
          step={0.01}
          onChange={(v) => handleUpdate({ archean_mutation_chance: v })}
          formatValue={(v) => `${(v * 100).toFixed(0)}%`}
        />
      </Card>

      {/* 元古宙参数 */}
      <Card title="元古宙（第 50-150 回合）" icon="🌊" desc="真核生物兴起，多样性持续增长">
        <InfoBox>
          元古宙见证了真核生物的兴起和多细胞生命的出现。基因多样性继续增长，但速度放缓，分化时的继承也开始减少（奠基者效应）。
        </InfoBox>
        <SliderRow
          label="初始半径"
          desc="元古宙新物种的初始基因多样性半径"
          value={c.proterozoic_initial_radius ?? 0.40}
          min={0.25}
          max={0.6}
          step={0.05}
          onChange={(v) => handleUpdate({ proterozoic_initial_radius: v })}
          formatValue={(v) => v.toFixed(2)}
        />
        <SliderRow
          label="增长率"
          desc="每回合基因多样性自然增长的比例"
          value={c.proterozoic_growth_rate ?? 0.02}
          min={0.005}
          max={0.05}
          step={0.005}
          onChange={(v) => handleUpdate({ proterozoic_growth_rate: v })}
          formatValue={(v) => `+${(v * 100).toFixed(1)}%/回合`}
        />
        <ConfigGroup title="分化继承系数">
          <SliderRow
            label="继承（最小）"
            desc="子种继承父种基因多样性的最小比例"
            value={c.proterozoic_inherit_min ?? 0.90}
            min={0.6}
            max={0.98}
            step={0.01}
            onChange={(v) => handleUpdate({ proterozoic_inherit_min: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="继承（最大）"
            desc="子种继承父种基因多样性的最大比例"
            value={c.proterozoic_inherit_max ?? 0.98}
            min={0.7}
            max={1.0}
            step={0.01}
            onChange={(v) => handleUpdate({ proterozoic_inherit_max: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
        </ConfigGroup>
        <SliderRow
          label="突变发现概率"
          desc="每回合发现新基因/扩展演化范围的概率"
          value={c.proterozoic_mutation_chance ?? 0.10}
          min={0.03}
          max={0.2}
          step={0.01}
          onChange={(v) => handleUpdate({ proterozoic_mutation_chance: v })}
          formatValue={(v) => `${(v * 100).toFixed(0)}%`}
        />
      </Card>

      {/* 古生代及以后参数 */}
      <Card title="古生代及以后（第 150+ 回合）" icon="🦖" desc="复杂生命繁荣，演化趋于稳定">
        <InfoBox>
          古生代以后，生命形式趋于复杂和稳定。基因多样性增长放缓，分化时的继承损失增加，但大灭绝后的幸存者仍可逐渐恢复。
        </InfoBox>
        <SliderRow
          label="初始半径"
          desc="古生代及以后新物种的初始基因多样性半径"
          value={c.phanerozoic_initial_radius ?? 0.35}
          min={0.2}
          max={0.5}
          step={0.05}
          onChange={(v) => handleUpdate({ phanerozoic_initial_radius: v })}
          formatValue={(v) => v.toFixed(2)}
        />
        <SliderRow
          label="增长率"
          desc="每回合基因多样性自然增长的比例"
          value={c.phanerozoic_growth_rate ?? 0.015}
          min={0.005}
          max={0.03}
          step={0.005}
          onChange={(v) => handleUpdate({ phanerozoic_growth_rate: v })}
          formatValue={(v) => `+${(v * 100).toFixed(1)}%/回合`}
        />
        <ConfigGroup title="分化继承系数">
          <SliderRow
            label="继承（最小）"
            desc="子种继承父种基因多样性的最小比例"
            value={c.phanerozoic_inherit_min ?? 0.85}
            min={0.5}
            max={0.95}
            step={0.01}
            onChange={(v) => handleUpdate({ phanerozoic_inherit_min: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="继承（最大）"
            desc="子种继承父种基因多样性的最大比例"
            value={c.phanerozoic_inherit_max ?? 0.95}
            min={0.6}
            max={1.0}
            step={0.01}
            onChange={(v) => handleUpdate({ phanerozoic_inherit_max: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
        </ConfigGroup>
        <SliderRow
          label="突变发现概率"
          desc="每回合发现新基因/扩展演化范围的概率"
          value={c.phanerozoic_mutation_chance ?? 0.08}
          min={0.02}
          max={0.15}
          step={0.01}
          onChange={(v) => handleUpdate({ phanerozoic_mutation_chance: v })}
          formatValue={(v) => `${(v * 100).toFixed(0)}%`}
        />
      </Card>

      {/* 激活机制 */}
      <Card title="休眠基因激活" icon="🔓" desc="控制休眠基因的激活条件">
        <InfoBox>
          休眠基因是物种演化范围内"尚未表达"的适应能力。当面临环境压力时，匹配的休眠基因更容易被激活。
        </InfoBox>
        <SliderRow
          label="激活概率"
          desc="每回合有此概率激活一个休眠基因"
          value={c.activation_chance_per_turn ?? 0.08}
          min={0.02}
          max={0.2}
          step={0.01}
          onChange={(v) => handleUpdate({ activation_chance_per_turn: v })}
          formatValue={(v) => `${(v * 100).toFixed(0)}%/回合`}
        />
        <SliderRow
          label="压力匹配加成"
          desc="当休眠基因方向与当前压力匹配时，激活概率乘以此值"
          value={c.pressure_match_bonus ?? 2.0}
          min={1.0}
          max={4.0}
          step={0.25}
          onChange={(v) => handleUpdate({ pressure_match_bonus: v })}
          formatValue={(v) => `×${v.toFixed(2)}`}
        />
        <SliderRow
          label="新器官发现概率"
          desc="分化时发现新器官的概率（扩展演化范围）"
          value={c.organ_discovery_chance ?? 0.04}
          min={0.01}
          max={0.1}
          step={0.005}
          onChange={(v) => handleUpdate({ organ_discovery_chance: v })}
          formatValue={(v) => `${(v * 100).toFixed(1)}%`}
        />
      </Card>
    </div>
  );
});

