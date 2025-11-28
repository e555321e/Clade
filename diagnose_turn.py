#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回合执行诊断脚本
自动化测试后端API，分析回合卡住的原因
"""

import asyncio
import aiohttp
import time
import json
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

class TurnDiagnostics:
    def __init__(self):
        self.events = []
        self.start_time = None
        self.sse_connected = False
        
    def log(self, msg: str, level: str = "INFO"):
        elapsed = f"{time.time() - self.start_time:.2f}s" if self.start_time else "0.00s"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{elapsed}] [{level}] {msg}")
        
    async def check_health(self, session: aiohttp.ClientSession) -> bool:
        """检查后端健康状态"""
        try:
            async with session.get(f"{BASE_URL}/api/queue", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log(f"✅ 后端健康: 队列状态={data}")
                    return True
                else:
                    self.log(f"❌ 后端响应异常: {resp.status}", "ERROR")
                    return False
        except Exception as e:
            self.log(f"❌ 后端连接失败: {e}", "ERROR")
            return False
    
    async def get_species_count(self, session: aiohttp.ClientSession) -> int:
        """获取当前存活物种数量"""
        try:
            async with session.get(f"{BASE_URL}/api/species/list", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    species = data.get("species", [])
                    alive = [s for s in species if s.get("status") == "alive"]
                    self.log(f"📊 物种状态: 总计{len(species)}个, 存活{len(alive)}个")
                    for sp in alive[:5]:  # 只显示前5个
                        pop = sp.get("population", 0)
                        self.log(f"   - {sp.get('lineage_code')}: {sp.get('common_name')} (种群: {pop:,})")
                    if len(alive) > 5:
                        self.log(f"   ... 还有 {len(alive) - 5} 个物种")
                    return len(alive)
                return 0
        except Exception as e:
            self.log(f"❌ 获取物种列表失败: {e}", "ERROR")
            return 0
    
    async def listen_sse(self, session: aiohttp.ClientSession, stop_event: asyncio.Event):
        """监听SSE事件流"""
        self.log("🔌 连接SSE事件流...")
        try:
            async with session.get(
                f"{BASE_URL}/api/events/stream",
                timeout=aiohttp.ClientTimeout(total=None, connect=10)
            ) as resp:
                if resp.status != 200:
                    self.log(f"❌ SSE连接失败: {resp.status}", "ERROR")
                    return
                
                self.sse_connected = True
                self.log("✅ SSE已连接，等待事件...")
                
                async for line in resp.content:
                    if stop_event.is_set():
                        break
                    
                    line = line.decode('utf-8').strip()
                    if line.startswith('data:'):
                        try:
                            data = json.loads(line[5:].strip())
                            event_type = data.get("type", "unknown")
                            message = data.get("message", "")
                            source = data.get("source", "")
                            
                            self.events.append({
                                "time": time.time() - self.start_time,
                                "type": event_type,
                                "message": message,
                                "source": source
                            })
                            
                            # 根据事件类型使用不同的图标
                            icons = {
                                "stage": "🔄",
                                "extinction": "💀",
                                "speciation": "🌱",
                                "warning": "⚠️",
                                "error": "❌",
                                "complete": "✅",
                                "turn_complete": "🎉",
                                "narrative_token": "",  # 不打印每个token
                            }
                            
                            icon = icons.get(event_type, "📌")
                            if event_type != "narrative_token":  # 跳过叙事token
                                self.log(f"{icon} [{event_type}] {message}")
                            
                            # 检测完成事件
                            if event_type in ["complete", "turn_complete", "error"]:
                                self.log(f"🏁 检测到结束事件: {event_type}")
                                
                        except json.JSONDecodeError:
                            pass
                            
        except asyncio.CancelledError:
            self.log("SSE监听已取消")
        except Exception as e:
            self.log(f"SSE错误: {e}", "ERROR")
        finally:
            self.sse_connected = False
    
    async def run_turn(self, session: aiohttp.ClientSession) -> dict:
        """执行一个回合"""
        self.log("🚀 发送回合请求...")
        request_start = time.time()
        
        try:
            # 设置较长的超时时间（10分钟）
            timeout = aiohttp.ClientTimeout(total=600, connect=10)
            
            async with session.post(
                f"{BASE_URL}/api/turns/run",
                json={"rounds": 1, "pressures": []},
                timeout=timeout
            ) as resp:
                request_time = time.time() - request_start
                self.log(f"📥 收到响应: 状态={resp.status}, 耗时={request_time:.2f}s")
                
                if resp.status != 200:
                    error_text = await resp.text()
                    self.log(f"❌ 请求失败: {error_text[:500]}", "ERROR")
                    return {"success": False, "error": error_text, "time": request_time}
                
                # 读取响应体
                read_start = time.time()
                body = await resp.read()
                read_time = time.time() - read_start
                self.log(f"📦 响应体大小: {len(body)} 字节, 读取耗时: {read_time:.3f}s")
                
                # 解析JSON
                parse_start = time.time()
                try:
                    data = json.loads(body)
                    parse_time = time.time() - parse_start
                    self.log(f"✅ JSON解析成功, 耗时: {parse_time:.3f}s")
                except json.JSONDecodeError as e:
                    self.log(f"❌ JSON解析失败: {e}", "ERROR")
                    self.log(f"响应内容预览: {body[:200]}", "ERROR")
                    return {"success": False, "error": str(e), "time": request_time}
                
                # 分析响应内容
                if isinstance(data, list) and len(data) > 0:
                    report = data[-1]
                    turn_index = report.get("turn_index", "?")
                    species_count = len(report.get("species", []))
                    branching_count = len(report.get("branching_events", []))
                    narrative_len = len(report.get("narrative", ""))
                    
                    self.log(f"📊 回合 {turn_index} 报告:")
                    self.log(f"   - 物种快照数: {species_count}")
                    self.log(f"   - 分化事件数: {branching_count}")
                    self.log(f"   - 叙事长度: {narrative_len} 字符")
                    
                    if species_count == 0:
                        self.log("⚠️ 警告: 物种快照为空！可能所有物种都灭绝了", "WARN")
                    
                    return {
                        "success": True,
                        "turn_index": turn_index,
                        "species_count": species_count,
                        "branching_count": branching_count,
                        "time": request_time,
                        "body_size": len(body)
                    }
                else:
                    self.log(f"⚠️ 响应数据格式异常: {type(data)}", "WARN")
                    return {"success": False, "error": "Invalid response format", "time": request_time}
                    
        except asyncio.TimeoutError:
            elapsed = time.time() - request_start
            self.log(f"❌ 请求超时 ({elapsed:.1f}s)", "ERROR")
            return {"success": False, "error": "Timeout", "time": elapsed}
        except Exception as e:
            elapsed = time.time() - request_start
            self.log(f"❌ 请求异常: {e}", "ERROR")
            return {"success": False, "error": str(e), "time": elapsed}
    
    def analyze_events(self):
        """分析收集到的事件，找出瓶颈"""
        self.log("\n" + "=" * 60)
        self.log("📈 事件分析报告")
        self.log("=" * 60)
        
        if not self.events:
            self.log("没有收集到任何事件")
            return
        
        # 按时间排序
        self.events.sort(key=lambda x: x["time"])
        
        # 计算各阶段耗时
        stages = []
        prev_time = 0
        for event in self.events:
            if event["type"] == "stage":
                stages.append({
                    "name": event["message"],
                    "start": prev_time,
                    "end": event["time"],
                    "duration": event["time"] - prev_time
                })
                prev_time = event["time"]
        
        # 打印阶段耗时
        self.log("\n阶段耗时分析:")
        for stage in stages:
            duration = stage["duration"]
            bar_len = int(duration * 2)  # 每秒2个字符
            bar = "█" * min(bar_len, 50)
            status = "⚠️ 较慢" if duration > 10 else "✅"
            self.log(f"  {stage['name'][:30]:<30} {duration:>6.2f}s {bar} {status}")
        
        # 找出最慢的阶段
        if stages:
            slowest = max(stages, key=lambda x: x["duration"])
            self.log(f"\n🐢 最慢阶段: {slowest['name']} ({slowest['duration']:.2f}s)")
        
        # 统计事件类型
        event_types = {}
        for event in self.events:
            t = event["type"]
            event_types[t] = event_types.get(t, 0) + 1
        
        self.log("\n事件统计:")
        for t, count in sorted(event_types.items(), key=lambda x: -x[1]):
            self.log(f"  {t}: {count}次")
        
        # 检查错误和警告
        errors = [e for e in self.events if e["type"] in ["error", "warning"]]
        if errors:
            self.log("\n⚠️ 错误/警告事件:")
            for e in errors:
                self.log(f"  [{e['time']:.2f}s] {e['message']}")
    
    async def run_diagnostics(self):
        """运行完整诊断"""
        self.start_time = time.time()
        self.log("=" * 60)
        self.log("🔬 回合执行诊断工具")
        self.log("=" * 60)
        
        connector = aiohttp.TCPConnector(limit=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            # 1. 检查后端健康
            if not await self.check_health(session):
                self.log("诊断终止: 后端不可用", "ERROR")
                return
            
            # 2. 获取当前物种状态
            species_count = await self.get_species_count(session)
            if species_count == 0:
                self.log("⚠️ 警告: 没有存活物种，回合可能无法正常执行", "WARN")
            
            # 3. 启动SSE监听
            stop_event = asyncio.Event()
            sse_task = asyncio.create_task(self.listen_sse(session, stop_event))
            
            # 等待SSE连接
            await asyncio.sleep(1)
            
            # 4. 执行回合
            result = await self.run_turn(session)
            
            # 5. 停止SSE监听
            await asyncio.sleep(2)  # 等待最后的事件
            stop_event.set()
            sse_task.cancel()
            try:
                await sse_task
            except asyncio.CancelledError:
                pass
            
            # 6. 分析结果
            self.analyze_events()
            
            # 7. 总结
            total_time = time.time() - self.start_time
            self.log("\n" + "=" * 60)
            self.log("📋 诊断总结")
            self.log("=" * 60)
            self.log(f"总耗时: {total_time:.2f}s")
            self.log(f"回合执行: {'✅ 成功' if result.get('success') else '❌ 失败'}")
            
            if result.get("success"):
                self.log(f"响应大小: {result.get('body_size', 0)} 字节")
                self.log(f"物种快照: {result.get('species_count', 0)} 个")
                
                if result.get('species_count', 0) == 0:
                    self.log("\n⚠️ 问题诊断: 物种快照为0")
                    self.log("  可能原因:")
                    self.log("  1. 所有物种都灭绝了")
                    self.log("  2. 物种筛选逻辑有问题")
                    self.log("  3. mortality计算结果为空")
            else:
                self.log(f"错误信息: {result.get('error', 'Unknown')}")
            
            # 检查是否卡住
            if total_time > 60 and not result.get("success"):
                self.log("\n🔍 可能的卡住原因:")
                self.log("  1. AI请求超时")
                self.log("  2. 数据库操作阻塞")
                self.log("  3. 大量物种导致计算缓慢")
                self.log("  4. 嵌入向量服务不可用")


async def main():
    diag = TurnDiagnostics()
    await diag.run_diagnostics()


if __name__ == "__main__":
    print("启动诊断...")
    asyncio.run(main())

