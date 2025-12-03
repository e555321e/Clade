"""物种描述增强服务

为规则生成的物种（背景物种分化、杂交等）提供 LLM 增强的描述。

设计理念：
- 轻量级：只生成描述，不涉及复杂的 JSON 解析和特质计算
- 批量处理：积累多个待增强物种后一次性处理
- 异步执行：不阻塞主要推演流程
- 成本优化：使用较短的 prompt 和较小的模型

使用场景：
1. 背景物种规则分化后
2. 同步杂交物种创建后
3. 任何使用模板描述的物种
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Sequence

from ...models.species import Species

if TYPE_CHECKING:
    from ...ai.model_router import ModelRouter

logger = logging.getLogger(__name__)


# 描述增强的 Prompt 模板
DESCRIPTION_ENHANCE_PROMPT = """你是一位生物学描述专家。请为以下物种生成一段生动、专业的生物学描述。

=== 物种信息 ===
名称：{common_name} ({latin_name})
代码：{lineage_code}
栖息地：{habitat_type}
营养级：{trophic_level:.1f}
食性：{diet_type}

=== 演化背景 ===
{evolution_context}

=== 父系信息 ===
父系：{parent_name} ({parent_code})
分化类型：{speciation_type}

=== 当前特质（关键几项）===
{key_traits}

=== 要求 ===
1. 生成 100-150 字的生物学描述
2. 包含：形态特征、生态习性、与父系的差异、独特适应性
3. 语言生动但科学严谨
4. 不要使用"继承"、"杂交"等机械词汇，而是描述具体特征

直接输出描述文本，不要加任何前缀或格式。"""

HYBRID_DESCRIPTION_PROMPT = """你是一位生物学描述专家。请为以下杂交物种生成一段生动、专业的生物学描述。

=== 物种信息 ===
名称：{common_name} ({latin_name})
代码：{lineage_code}
栖息地：{habitat_type}
营养级：{trophic_level:.1f}
食性：{diet_type}

=== 杂交背景 ===
亲本A：{parent1_name} ({parent1_code})
亲本B：{parent2_name} ({parent2_code})
可育性：{fertility:.0%}

=== 当前特质（关键几项）===
{key_traits}

=== 要求 ===
1. 生成 100-150 字的生物学描述
2. 包含：形态特征（体现双亲融合）、生态习性、独特优势或劣势
3. 语言生动但科学严谨
4. 描述具体的杂交特征表现，而非笼统的"继承双亲特征"

直接输出描述文本，不要加任何前缀或格式。"""


class DescriptionEnhancerService:
    """物种描述增强服务
    
    为规则生成的物种提供 LLM 增强描述，改善 embedding 质量。
    
    使用方式：
    1. 在规则生成物种后，调用 queue_for_enhancement() 将物种加入队列
    2. 在回合结束前，调用 process_queue_async() 批量处理
    3. 或者使用 enhance_single_async() 立即处理单个物种
    
    配置：
    - batch_size: 每批处理的物种数量（默认 10）
    - min_queue_size: 触发自动批量处理的最小队列大小（默认 5）
    """
    
    def __init__(self, router: 'ModelRouter', batch_size: int = 10):
        self.router = router
        self.batch_size = batch_size
        self._pending_queue: list[dict] = []
        self._enhancement_count = 0
    
    def queue_for_enhancement(
        self,
        species: Species,
        parent: Species | None = None,
        speciation_type: str = "自然分化",
        is_hybrid: bool = False,
        parent2: Species | None = None,
        fertility: float = 1.0,
    ) -> None:
        """将物种加入增强队列
        
        Args:
            species: 需要增强描述的物种
            parent: 父系物种（分化时）
            speciation_type: 分化类型
            is_hybrid: 是否为杂交物种
            parent2: 第二亲本（杂交时）
            fertility: 杂交可育性
        """
        entry = {
            "species": species,
            "parent": parent,
            "speciation_type": speciation_type,
            "is_hybrid": is_hybrid,
            "parent2": parent2,
            "fertility": fertility,
        }
        self._pending_queue.append(entry)
        logger.debug(
            f"[描述增强] 加入队列: {species.common_name} "
            f"({'杂交' if is_hybrid else speciation_type}), 队列大小: {len(self._pending_queue)}"
        )
    
    def get_queue_size(self) -> int:
        """获取当前队列大小"""
        return len(self._pending_queue)
    
    def clear_queue(self) -> None:
        """清空队列"""
        self._pending_queue.clear()
    
    async def process_queue_async(
        self,
        max_items: int | None = None,
        timeout_per_item: float = 30.0,
    ) -> list[Species]:
        """批量处理队列中的物种
        
        Args:
            max_items: 最大处理数量（None 表示全部）
            timeout_per_item: 每个物种的超时时间（秒）
            
        Returns:
            成功增强的物种列表
        """
        if not self._pending_queue:
            return []
        
        # 取出要处理的条目
        items_to_process = self._pending_queue[:max_items] if max_items else self._pending_queue[:]
        self._pending_queue = self._pending_queue[len(items_to_process):]
        
        logger.info(f"[描述增强] 开始批量处理 {len(items_to_process)} 个物种")
        
        enhanced_species = []
        tasks = []
        
        for entry in items_to_process:
            task = self._enhance_entry_async(entry, timeout_per_item)
            tasks.append(task)
        
        # 并发执行（带超时）
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for entry, result in zip(items_to_process, results):
            if isinstance(result, Exception):
                logger.warning(
                    f"[描述增强] 失败: {entry['species'].common_name} - {result}"
                )
            elif result:
                enhanced_species.append(result)
                self._enhancement_count += 1
        
        logger.info(
            f"[描述增强] 批量处理完成: {len(enhanced_species)}/{len(items_to_process)} 成功"
        )
        return enhanced_species
    
    async def enhance_single_async(
        self,
        species: Species,
        parent: Species | None = None,
        speciation_type: str = "自然分化",
        is_hybrid: bool = False,
        parent2: Species | None = None,
        fertility: float = 1.0,
        timeout: float = 30.0,
    ) -> Species | None:
        """立即增强单个物种的描述
        
        Args:
            species: 需要增强描述的物种
            parent: 父系物种（分化时）
            speciation_type: 分化类型
            is_hybrid: 是否为杂交物种
            parent2: 第二亲本（杂交时）
            fertility: 杂交可育性
            timeout: 超时时间
            
        Returns:
            增强后的物种（原地修改），失败返回 None
        """
        entry = {
            "species": species,
            "parent": parent,
            "speciation_type": speciation_type,
            "is_hybrid": is_hybrid,
            "parent2": parent2,
            "fertility": fertility,
        }
        return await self._enhance_entry_async(entry, timeout)
    
    async def _enhance_entry_async(
        self,
        entry: dict,
        timeout: float,
    ) -> Species | None:
        """处理单个队列条目"""
        species = entry["species"]
        is_hybrid = entry["is_hybrid"]
        
        try:
            if is_hybrid:
                prompt = self._build_hybrid_prompt(entry)
            else:
                prompt = self._build_speciation_prompt(entry)
            
            # 调用 LLM（使用流式获取完整响应）
            response = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=timeout,
            )
            
            if response and len(response) >= 50:  # 至少 50 字符
                # 清理响应（去除可能的前缀/后缀）
                description = self._clean_response(response)
                
                # 更新物种描述
                old_desc = species.description
                species.description = description
                
                logger.info(
                    f"[描述增强] 成功: {species.common_name}\n"
                    f"  旧: {old_desc[:50]}...\n"
                    f"  新: {description[:50]}..."
                )
                return species
            else:
                logger.warning(
                    f"[描述增强] 响应过短: {species.common_name} - {len(response or '')} 字符"
                )
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"[描述增强] 超时: {species.common_name}")
            return None
        except Exception as e:
            logger.error(f"[描述增强] 异常: {species.common_name} - {e}")
            return None
    
    def _build_speciation_prompt(self, entry: dict) -> str:
        """构建分化物种的描述增强 prompt"""
        species = entry["species"]
        parent = entry["parent"]
        speciation_type = entry["speciation_type"]
        
        # 提取关键特质
        key_traits = self._format_key_traits(species)
        
        # 演化背景
        if parent:
            parent_name = parent.common_name
            parent_code = parent.lineage_code
            evolution_context = f"该物种从 {parent_name} 通过 {speciation_type} 演化而来。"
        else:
            parent_name = "未知祖先"
            parent_code = "N/A"
            evolution_context = f"该物种通过 {speciation_type} 演化形成。"
        
        return DESCRIPTION_ENHANCE_PROMPT.format(
            common_name=species.common_name,
            latin_name=species.latin_name,
            lineage_code=species.lineage_code,
            habitat_type=species.habitat_type or "未知",
            trophic_level=species.trophic_level,
            diet_type=species.diet_type or "未知",
            evolution_context=evolution_context,
            parent_name=parent_name,
            parent_code=parent_code,
            speciation_type=speciation_type,
            key_traits=key_traits,
        )
    
    def _build_hybrid_prompt(self, entry: dict) -> str:
        """构建杂交物种的描述增强 prompt"""
        species = entry["species"]
        parent = entry["parent"]
        parent2 = entry["parent2"]
        fertility = entry["fertility"]
        
        # 提取关键特质
        key_traits = self._format_key_traits(species)
        
        # 亲本信息
        if parent:
            parent1_name = parent.common_name
            parent1_code = parent.lineage_code
        else:
            parent1_name = "未知亲本A"
            parent1_code = "N/A"
        
        if parent2:
            parent2_name = parent2.common_name
            parent2_code = parent2.lineage_code
        else:
            parent2_name = "未知亲本B"
            parent2_code = "N/A"
        
        return HYBRID_DESCRIPTION_PROMPT.format(
            common_name=species.common_name,
            latin_name=species.latin_name,
            lineage_code=species.lineage_code,
            habitat_type=species.habitat_type or "未知",
            trophic_level=species.trophic_level,
            diet_type=species.diet_type or "未知",
            parent1_name=parent1_name,
            parent1_code=parent1_code,
            parent2_name=parent2_name,
            parent2_code=parent2_code,
            fertility=fertility,
            key_traits=key_traits,
        )
    
    def _format_key_traits(self, species: Species) -> str:
        """格式化关键特质用于 prompt"""
        traits = species.abstract_traits or {}
        if not traits:
            return "暂无特质数据"
        
        # 选择最高和最低的几个特质
        sorted_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)
        high_traits = sorted_traits[:3]  # 最高的3个
        low_traits = sorted_traits[-2:]  # 最低的2个
        
        lines = []
        lines.append("【优势特质】")
        for name, value in high_traits:
            lines.append(f"  - {name}: {value:.1f}")
        lines.append("【劣势特质】")
        for name, value in low_traits:
            lines.append(f"  - {name}: {value:.1f}")
        
        return "\n".join(lines)
    
    async def _call_llm(self, prompt: str) -> str | None:
        """调用 LLM 获取描述"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # 使用流式调用收集完整响应
            full_response = []
            async for chunk in self.router.complete(
                messages,
                capability="speciation",  # 使用分化能力的配置
                temperature=0.8,
                max_tokens=300,
            ):
                if chunk:
                    full_response.append(chunk)
            
            return "".join(full_response)
        except Exception as e:
            logger.error(f"[描述增强] LLM 调用失败: {e}")
            return None
    
    def _clean_response(self, response: str) -> str:
        """清理 LLM 响应"""
        # 去除可能的 markdown 代码块
        if response.startswith("```"):
            lines = response.split("\n")
            # 去除首尾的 ``` 行
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        # 去除可能的引号包裹
        response = response.strip()
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        
        # 去除可能的前缀
        prefixes_to_remove = [
            "描述：", "描述:", "Description:", "物种描述：",
            "以下是", "生物学描述：",
        ]
        for prefix in prefixes_to_remove:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        return response.strip()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_enhanced": self._enhancement_count,
            "queue_size": len(self._pending_queue),
        }


def create_description_enhancer(router: 'ModelRouter') -> DescriptionEnhancerService:
    """创建描述增强服务实例"""
    return DescriptionEnhancerService(router)

