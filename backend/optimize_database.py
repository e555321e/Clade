#!/usr/bin/env python3
"""数据库优化脚本

【功能】
1. 创建必要的数据库索引（加速查询 10-100x）
2. 清理历史栖息地数据（控制数据库膨胀）
3. 执行 VACUUM 和 ANALYZE（回收空间，优化查询计划）
4. 迁移旧存档到压缩格式（减少 60-80% 磁盘空间）

【使用方式】
    # 查看帮助
    python optimize_database.py --help
    
    # 完整优化（推荐）
    python optimize_database.py --all
    
    # 只创建索引
    python optimize_database.py --indexes
    
    # 清理历史数据（保留最近 3 回合）
    python optimize_database.py --cleanup --keep-turns 3
    
    # 压缩所有存档
    python optimize_database.py --compress-saves
    
    # 查看统计信息
    python optimize_database.py --stats

【注意事项】
- 在执行优化前建议先备份数据库
- VACUUM 操作可能需要较长时间（取决于数据库大小）
- 清理历史数据是不可逆的，请谨慎操作
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# 添加 app 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import init_db
from app.repositories.environment_repository import environment_repository
from app.services.system.save_manager import SaveManager
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def create_indexes():
    """创建数据库索引"""
    logger.info("=" * 50)
    logger.info("创建数据库索引...")
    logger.info("=" * 50)
    
    try:
        results = environment_repository.ensure_indexes()
        
        created = sum(1 for v in results.values() if v)
        existing = sum(1 for v in results.values() if not v)
        
        logger.info(f"索引创建完成: 新建 {created} 个, 已存在 {existing} 个")
        
        for name, is_new in results.items():
            status = "✓ 新建" if is_new else "- 已存在"
            logger.info(f"  {status}: {name}")
        
        return True
    except Exception as e:
        logger.error(f"创建索引失败: {e}")
        return False


def cleanup_history(keep_turns: int = 3):
    """清理历史栖息地数据"""
    logger.info("=" * 50)
    logger.info(f"清理历史栖息地数据 (保留最近 {keep_turns} 回合)...")
    logger.info("=" * 50)
    
    try:
        # 先获取统计信息
        stats_before = environment_repository.get_habitat_stats()
        logger.info(f"清理前: {stats_before['total_records']} 条记录")
        
        # 执行清理
        deleted = environment_repository.cleanup_old_habitats(keep_turns)
        
        # 获取清理后统计
        stats_after = environment_repository.get_habitat_stats()
        
        logger.info(f"清理完成: 删除 {deleted} 条记录")
        logger.info(f"清理后: {stats_after['total_records']} 条记录")
        
        return True
    except Exception as e:
        logger.error(f"清理历史数据失败: {e}")
        return False


def vacuum_analyze():
    """执行 VACUUM 和 ANALYZE"""
    logger.info("=" * 50)
    logger.info("执行数据库优化 (VACUUM + ANALYZE)...")
    logger.info("=" * 50)
    
    try:
        results = environment_repository.optimize_database()
        
        logger.info(f"VACUUM: {'成功' if results.get('vacuum') else '失败'}")
        logger.info(f"ANALYZE: {'成功' if results.get('analyze') else '失败'}")
        logger.info(f"耗时: {results.get('elapsed_seconds', 0):.2f} 秒")
        
        return results.get('vacuum') and results.get('analyze')
    except Exception as e:
        logger.error(f"数据库优化失败: {e}")
        return False


def compress_saves():
    """压缩所有存档"""
    logger.info("=" * 50)
    logger.info("压缩存档文件...")
    logger.info("=" * 50)
    
    settings = get_settings()
    saves_dir = Path(settings.data_dir) / "saves"
    
    if not saves_dir.exists():
        logger.warning(f"存档目录不存在: {saves_dir}")
        return False
    
    save_manager = SaveManager(saves_dir)
    saves = save_manager.list_saves()
    
    if not saves:
        logger.info("没有找到存档")
        return True
    
    compressed_count = 0
    total_saved_mb = 0
    
    for save in saves:
        save_name = save.get("save_name") or save.get("name")
        save_dir = save_manager._find_save_dir(save_name)
        
        if not save_dir:
            continue
        
        json_path = save_dir / "game_state.json"
        gz_path = save_dir / "game_state.json.gz"
        
        # 跳过已压缩的存档
        if gz_path.exists():
            logger.info(f"  - {save_name}: 已是压缩格式")
            continue
        
        if not json_path.exists():
            logger.warning(f"  - {save_name}: 缺少数据文件")
            continue
        
        # 执行压缩
        result = save_manager.migrate_save_to_compressed(save_name)
        
        if result.get("success"):
            compressed_count += 1
            saved_mb = result.get("original_size_mb", 0) - result.get("compressed_size_mb", 0)
            total_saved_mb += saved_mb
            logger.info(
                f"  ✓ {save_name}: "
                f"{result['original_size_mb']} MB -> {result['compressed_size_mb']} MB "
                f"(节省 {saved_mb:.2f} MB)"
            )
        else:
            logger.error(f"  ✗ {save_name}: {result.get('error')}")
    
    logger.info(f"压缩完成: {compressed_count} 个存档, 总共节省 {total_saved_mb:.2f} MB")
    return True


def show_stats():
    """显示统计信息"""
    logger.info("=" * 50)
    logger.info("存储统计信息")
    logger.info("=" * 50)
    
    try:
        # 栖息地统计
        habitat_stats = environment_repository.get_habitat_stats()
        
        logger.info("\n【栖息地数据】")
        logger.info(f"  总记录数: {habitat_stats.get('total_records', 0):,}")
        logger.info(f"  回合范围: {habitat_stats.get('min_turn')} - {habitat_stats.get('max_turn')}")
        logger.info(f"  物种数量: {habitat_stats.get('species_count', 0)}")
        logger.info(f"  每回合平均: {habitat_stats.get('avg_records_per_turn', 0):,.0f} 条")
        logger.info(f"  估算大小: {habitat_stats.get('estimated_size_mb', 0):.2f} MB")
        
        # 存档统计
        settings = get_settings()
        saves_dir = Path(settings.data_dir) / "saves"
        
        if saves_dir.exists():
            save_manager = SaveManager(saves_dir)
            storage_stats = save_manager.get_storage_stats()
            
            logger.info("\n【存档文件】")
            logger.info(f"  存档数量: {storage_stats.get('save_count', 0)}")
            logger.info(f"  总大小: {storage_stats.get('total_size_mb', 0):.2f} MB")
            
            if storage_stats.get("largest_save"):
                largest = storage_stats["largest_save"]
                logger.info(f"  最大存档: {largest['name']} ({largest['size_mb']} MB)")
        
        return True
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="数据库优化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="执行所有优化操作（推荐）"
    )
    parser.add_argument(
        "--indexes", "-i",
        action="store_true",
        help="创建数据库索引"
    )
    parser.add_argument(
        "--cleanup", "-c",
        action="store_true",
        help="清理历史栖息地数据"
    )
    parser.add_argument(
        "--keep-turns", "-k",
        type=int,
        default=3,
        help="清理时保留最近多少回合的数据（默认: 3）"
    )
    parser.add_argument(
        "--vacuum", "-v",
        action="store_true",
        help="执行 VACUUM 和 ANALYZE"
    )
    parser.add_argument(
        "--compress-saves", "-z",
        action="store_true",
        help="压缩所有存档文件"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="显示统计信息"
    )
    
    args = parser.parse_args()
    
    # 如果没有指定任何操作，显示帮助
    if not any([args.all, args.indexes, args.cleanup, args.vacuum, 
                args.compress_saves, args.stats]):
        parser.print_help()
        return 0
    
    # 初始化数据库
    logger.info("初始化数据库...")
    init_db()
    
    start_time = time.time()
    success = True
    
    # 显示统计信息
    if args.stats or args.all:
        success = show_stats() and success
    
    # 创建索引
    if args.indexes or args.all:
        success = create_indexes() and success
    
    # 清理历史数据
    if args.cleanup or args.all:
        success = cleanup_history(args.keep_turns) and success
    
    # VACUUM 和 ANALYZE
    if args.vacuum or args.all:
        success = vacuum_analyze() and success
    
    # 压缩存档
    if args.compress_saves or args.all:
        success = compress_saves() and success
    
    # 最终统计
    if args.all:
        show_stats()
    
    elapsed = time.time() - start_time
    logger.info("=" * 50)
    logger.info(f"优化完成，总耗时: {elapsed:.2f} 秒")
    logger.info("=" * 50)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
