/**
 * PressureSection - 压力强度配置
 * 
 * 控制玩家施加的环境压力效果强度
 * - 一阶压力（生态波动）
 * - 二阶压力（气候变迁）
 * - 三阶压力（天灾降临）
 */

import { memo, type Dispatch } from "react";
import type { PressureIntensityConfig } from "@/services/api.types";
import type { SettingsAction } from "../types";
import { SectionHeader, Card, ConfigGroup, SliderRow, ActionButton, InfoBox } from "../common/Controls";
import { DEFAULT_PRESSURE_INTENSITY_CONFIG } from "../constants";

interface Props {
  config: PressureIntensityConfig;
  dispatch: Dispatch<SettingsAction>;
}

export const PressureSection = memo(function PressureSection({
  config,
  dispatch,
}: Props) {
  const handleUpdate = (updates: Partial<PressureIntensityConfig>) => {
    dispatch({ type: "UPDATE_PRESSURE", updates });
  };

  const handleReset = () => {
    dispatch({ type: "RESET_PRESSURE" });
  };

  const c = { ...DEFAULT_PRESSURE_INTENSITY_CONFIG, ...config };

  return (
    <div className="section-page">
      <SectionHeader
        icon="🌊"
        title="压力强度配置"
        subtitle="调整玩家施加的环境压力效果强度"
        actions={<ActionButton label="恢复默认" onClick={handleReset} variant="ghost" icon="↻" />}
      />

      {/* 概念说明 */}
      <InfoBox variant="info" title="压力系统说明">
        压力分为三个等级：<strong>一阶（生态波动）</strong>影响轻微，<strong>二阶（气候变迁）</strong>影响显著但可控，<strong>三阶（天灾降临）</strong>可造成大灭绝。
        每种压力的最终效果 = 基础系数 × 类型倍率 × 强度倍率。
      </InfoBox>

      {/* 压力类型倍率 */}
      <Card title="压力类型倍率" icon="📊" desc="不同等级压力类型的效果强度">
        <InfoBox>
          压力类型决定了该压力的基础威胁程度。一阶压力是轻微的生态波动，三阶压力是毁灭性的天灾。
          倍率越高，该等级压力造成的影响越大。
        </InfoBox>
        <ConfigGroup title="三阶压力系统">
          <SliderRow
            label="一阶压力倍率"
            desc="🌱 生态波动：自然演化、微调等轻微变化。建议保持较低值，让生态系统自然发展。"
            value={c.tier1_multiplier ?? 0.5}
            min={0.1}
            max={2.0}
            step={0.1}
            onChange={(v) => handleUpdate({ tier1_multiplier: v })}
            formatValue={(v) => `×${v.toFixed(1)}`}
          />
          <SliderRow
            label="二阶压力倍率"
            desc="🌡️ 气候变迁：冰河期、干旱、温室效应等显著变化。中等值可创造演化压力。"
            value={c.tier2_multiplier ?? 0.7}
            min={0.1}
            max={2.0}
            step={0.1}
            onChange={(v) => handleUpdate({ tier2_multiplier: v })}
            formatValue={(v) => `×${v.toFixed(1)}`}
          />
          <SliderRow
            label="三阶压力倍率"
            desc="💥 天灾降临：火山喷发、陨石撞击、大灭绝事件。高值可实现大浪淘沙效果。"
            value={c.tier3_multiplier ?? 1.5}
            min={0.5}
            max={5.0}
            step={0.1}
            onChange={(v) => handleUpdate({ tier3_multiplier: v })}
            formatValue={(v) => `×${v.toFixed(1)}`}
          />
        </ConfigGroup>
      </Card>

      {/* 强度滑块倍率 */}
      <Card title="强度滑块倍率" icon="🎚️" desc="压力强度1-10对应的效果倍率">
        <InfoBox>
          施加压力时可选择1-10的强度等级。低强度(1-3)适合微调，中强度(4-7)产生显著影响，高强度(8-10)造成毁灭性效果。
        </InfoBox>
        <div className="card-grid">
          <SliderRow
            label="轻微强度 (1-3)"
            desc="低强度压力的效果倍率。较低值使轻微压力几乎无害。"
            value={c.intensity_low_multiplier ?? 0.3}
            min={0.1}
            max={1.0}
            step={0.05}
            onChange={(v) => handleUpdate({ intensity_low_multiplier: v })}
            formatValue={(v) => `×${v.toFixed(2)}`}
          />
          <SliderRow
            label="显著强度 (4-7)"
            desc="中等强度压力的效果倍率。合理的中间值创造适度挑战。"
            value={c.intensity_mid_multiplier ?? 0.6}
            min={0.2}
            max={1.5}
            step={0.05}
            onChange={(v) => handleUpdate({ intensity_mid_multiplier: v })}
            formatValue={(v) => `×${v.toFixed(2)}`}
          />
          <SliderRow
            label="毁灭强度 (8-10)"
            desc="高强度压力的效果倍率。高值使极端压力真正致命。"
            value={c.intensity_high_multiplier ?? 1.2}
            min={0.5}
            max={3.0}
            step={0.1}
            onChange={(v) => handleUpdate({ intensity_high_multiplier: v })}
            formatValue={(v) => `×${v.toFixed(1)}`}
          />
        </div>
      </Card>

      {/* 温度效果 */}
      <Card title="温度修饰效果" icon="🌡️" desc="温度相关压力的影响程度">
        <InfoBox>
          冰河期和温室效应等压力会改变全球温度。此参数控制每单位压力修饰对应的温度变化。
          较低值使气候变化更温和，较高值使冰河期/温室效应更剧烈。
        </InfoBox>
        <SliderRow
          label="每单位温度效果"
          desc="每单位温度修饰对应的实际温度变化（°C）。例如冰川期-1.0系数 × 0.8 = 降温0.8°C/单位强度。"
          value={c.temperature_effect_per_unit ?? 0.8}
          min={0.2}
          max={3.0}
          step={0.1}
          onChange={(v) => handleUpdate({ temperature_effect_per_unit: v })}
          formatValue={(v) => `${v.toFixed(1)}°C`}
        />
      </Card>

      {/* 效果预览 */}
      <Card title="效果预览" icon="📈" desc="当前配置下的压力效果示例">
        <div className="stat-grid">
          {/* 一阶轻微 */}
          <div className="stat-card low">
            <div className="stat-label">一阶 + 轻微(3)</div>
            <div className="stat-value">
              ×{((c.tier1_multiplier ?? 0.5) * (c.intensity_low_multiplier ?? 0.3)).toFixed(2)}
            </div>
            <div className="stat-desc">几乎无影响</div>
          </div>
          {/* 二阶显著 */}
          <div className="stat-card mid">
            <div className="stat-label">二阶 + 显著(5)</div>
            <div className="stat-value">
              ×{((c.tier2_multiplier ?? 0.7) * (c.intensity_mid_multiplier ?? 0.6)).toFixed(2)}
            </div>
            <div className="stat-desc">适度挑战</div>
          </div>
          {/* 三阶毁灭 */}
          <div className="stat-card high">
            <div className="stat-label">三阶 + 毁灭(10)</div>
            <div className="stat-value">
              ×{((c.tier3_multiplier ?? 1.5) * (c.intensity_high_multiplier ?? 1.2)).toFixed(2)}
            </div>
            <div className="stat-desc">大浪淘沙！</div>
          </div>
        </div>
        <div style={{ marginTop: '1rem', fontSize: '0.8rem', opacity: 0.7, textAlign: 'center' }}>
          5级冰川期温度影响：约 {(5 * (c.tier2_multiplier ?? 0.7) * (c.intensity_mid_multiplier ?? 0.6) * (c.temperature_effect_per_unit ?? 0.8)).toFixed(1)}°C 降温
        </div>
      </Card>

      {/* ============ 张量压力桥接参数 ============ */}
      <Card title="🧬 张量死亡率计算" icon="⚗️" desc="高级：控制各类压力对物种的具体死亡率影响">
        <InfoBox variant="warning" title="高级参数">
          这些参数控制张量计算模块中，各类环境压力如何转化为物种死亡率。
          调整不当可能导致物种大灭绝或压力无效，建议谨慎修改。
        </InfoBox>

        {/* 基础死亡率 */}
        <ConfigGroup title="各因子基础死亡率">
          <SliderRow
            label="温度压力乘数"
            desc="每单位温度压力等于多少°C的温度变化。值越高，冰期/温室效应越剧烈。"
            value={c.thermal_multiplier ?? 3.0}
            min={1.0}
            max={10.0}
            step={0.5}
            onChange={(v) => handleUpdate({ thermal_multiplier: v })}
            formatValue={(v) => `${v.toFixed(1)}°C`}
          />
          <SliderRow
            label="毒性基础死亡率"
            desc="🧪 每单位毒性压力造成的基础死亡率。火山/硫化事件会产生毒性。"
            value={c.toxin_base_mortality ?? 0.06}
            min={0.01}
            max={0.20}
            step={0.01}
            onChange={(v) => handleUpdate({ toxin_base_mortality: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="干旱基础死亡率"
            desc="🏜️ 每单位干旱压力造成的基础死亡率。干旱期、资源枯竭会产生干旱压力。"
            value={c.drought_base_mortality ?? 0.05}
            min={0.01}
            max={0.20}
            step={0.01}
            onChange={(v) => handleUpdate({ drought_base_mortality: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="缺氧基础死亡率"
            desc="💨 每单位缺氧压力造成的基础死亡率。缺氧事件对需氧生物致命。"
            value={c.anoxic_base_mortality ?? 0.08}
            min={0.01}
            max={0.25}
            step={0.01}
            onChange={(v) => handleUpdate({ anoxic_base_mortality: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="直接死亡率"
            desc="💀 每单位直接死亡压力的死亡率。陨石撞击、风暴等直接造成死亡。"
            value={c.direct_mortality_rate ?? 0.04}
            min={0.01}
            max={0.15}
            step={0.01}
            onChange={(v) => handleUpdate({ direct_mortality_rate: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="辐射基础死亡率"
            desc="☢️ 每单位辐射压力造成的基础死亡率。伽马射线暴、紫外辐射等。"
            value={c.radiation_base_mortality ?? 0.04}
            min={0.01}
            max={0.15}
            step={0.01}
            onChange={(v) => handleUpdate({ radiation_base_mortality: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
        </ConfigGroup>

        {/* 特殊机制 */}
        <ConfigGroup title="特殊生物机制">
          <SliderRow
            label="化能自养毒性受益"
            desc="🦠 化能自养生物在高毒性环境中的生存优势。值越高，它们在火山/硫化事件中受益越多。"
            value={c.autotroph_toxin_benefit ?? 0.15}
            min={0.0}
            max={0.5}
            step={0.05}
            onChange={(v) => handleUpdate({ autotroph_toxin_benefit: v })}
            formatValue={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <SliderRow
            label="需氧生物敏感度"
            desc="🐟 需氧生物对缺氧的敏感程度。值越高，氧气需求高的物种在缺氧事件中损失越大。"
            value={c.aerobe_sensitivity ?? 0.6}
            min={0.2}
            max={1.0}
            step={0.1}
            onChange={(v) => handleUpdate({ aerobe_sensitivity: v })}
            formatValue={(v) => `×${v.toFixed(1)}`}
          />
        </ConfigGroup>

        {/* 多压力衰减 */}
        <ConfigGroup title="多压力平衡">
          <SliderRow
            label="多压力衰减系数"
            desc="⚖️ 当多个压力同时存在时的边际递减效应。值越低，多压力叠加效果越弱，避免极端灭绝。"
            value={c.multi_pressure_decay ?? 0.7}
            min={0.3}
            max={1.0}
            step={0.05}
            onChange={(v) => handleUpdate({ multi_pressure_decay: v })}
            formatValue={(v) => `×${v.toFixed(2)}`}
          />
          <InfoBox>
            衰减机制：第1个压力通道效果×1，第2个×{(c.multi_pressure_decay ?? 0.7).toFixed(2)}，第3个×{((c.multi_pressure_decay ?? 0.7) ** 2).toFixed(2)}...
            <br />
            当前设置下，3个压力同时激活时，总效果约为单压力的 {(1 + (c.multi_pressure_decay ?? 0.7) + (c.multi_pressure_decay ?? 0.7) ** 2).toFixed(1)} 倍（而非 3 倍）。
          </InfoBox>
        </ConfigGroup>
      </Card>
    </div>
  );
});
