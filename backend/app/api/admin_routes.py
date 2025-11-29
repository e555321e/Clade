from __future__ import annotations

import shutil
import sys
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import SQLModel, delete, select, Session

from ..core.database import session_scope, init_db, engine
from ..core.seed import A_SCENARIO, seed_defaults
from ..core.config import get_settings
from ..models.species import Species
from ..models.environment import MapState
from ..models.history import TurnLog
from ..repositories.species_repository import species_repository
from ..repositories.environment_repository import environment_repository

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()
logger = logging.getLogger(__name__)

class ResetRequest(BaseModel):
    keep_saves: bool = False
    keep_map: bool = False

@router.get("/health")
def check_health() -> dict:
    """系统健康检查"""
    status = {
        "api": "online",
        "database": "unknown",
        "directories": {},
        "initial_species": "unknown"
    }
    
    # 1. 检查数据库
    try:
        with session_scope() as session:
            # 检查初始物种
            initial_codes = ['A1', 'B1', 'C1']
            missing = []
            for code in initial_codes:
                sp = species_repository.get_by_lineage(code)
                if not sp:
                    missing.append(code)
            
            if missing:
                status["initial_species"] = f"missing: {missing}"
                status["database"] = "degraded"
            else:
                status["initial_species"] = "ok"
                status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
    
    # 2. 检查目录 (使用 Settings 中的配置)
    current_settings = get_settings()
    required_dirs = {
        "db": Path(current_settings.database_url.replace("sqlite:///", "")).parent,
        "logs": Path(current_settings.log_dir),
        "reports": Path(current_settings.reports_dir),
        "saves": Path(current_settings.saves_dir),
        "exports": Path(current_settings.exports_dir)
    }
    
    for name, path in required_dirs.items():
        if path.exists():
            status["directories"][name] = "ok"
        else:
            status["directories"][name] = "missing"
            
    return status

@router.post("/reset")
def reset_world(request: ResetRequest) -> dict:
    """重置世界状态"""
    try:
        # 1. 重置数据库
        with session_scope() as session:
            # 删除历史记录
            session.exec(delete(TurnLog))
            
            # 删除非初始物种
            initial_codes = {s['lineage_code'] for s in A_SCENARIO}
            all_species = session.exec(select(Species)).all()
            deleted_count = 0
            
            for sp in all_species:
                if sp.lineage_code not in initial_codes:
                    session.delete(sp)
                    deleted_count += 1
                else:
                    # 重置初始物种
                    scenario = next(s for s in A_SCENARIO if s['lineage_code'] == sp.lineage_code)
                    sp.population = 1000
                    sp.status = 'alive'
                    sp.created_turn = 0
                    sp.parent_code = None
                    sp.morphology_stats = scenario['morphology_stats']
                    sp.abstract_traits = scenario['abstract_traits']
                    sp.description = scenario['description']
                    session.add(sp)
            
            # 重置地图
            if not request.keep_map:
                session.exec(delete(MapState))
                # 重置初始地图状态
                initial_state = MapState(
                    turn_index=0,
                    stage_name="稳定期",
                    stage_progress=0,
                    stage_duration=50,
                    sea_level=0.0,
                    global_avg_temperature=15.0
                )
                session.add(initial_state)
        
        # 2. 清理文件
        current_settings = get_settings()
        if not request.keep_saves:
            _clear_directory(Path(current_settings.saves_dir))
            _clear_directory(Path(current_settings.exports_dir))
        
        _clear_directory(Path(current_settings.reports_dir))
        # 不清理 logs，因为当前正在写入日志
        
        return {"success": True, "message": f"重置完成。删除了 {deleted_count} 个演化物种。"}
        
    except Exception as e:
        logger.error(f"重置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _clear_directory(dir_path: Path):
    if not dir_path.exists():
        return
    for item in dir_path.glob("*"):
        if item.is_file():
            try:
                item.unlink()
            except Exception:
                pass
        elif item.is_dir():
            try:
                shutil.rmtree(item)
            except Exception:
                pass


class DropDatabaseRequest(BaseModel):
    confirm: bool = False  # 必须确认


@router.post("/drop-database")
def drop_and_recreate_database(request: DropDatabaseRequest) -> dict:
    """完全清空数据库并重新创建所有表
    
    ⚠️ 危险操作：这将删除所有数据！
    """
    if not request.confirm:
        raise HTTPException(status_code=400, detail="必须设置 confirm=true 才能执行此操作")
    
    try:
        logger.warning("⚠️ 开始清空数据库...")
        
        # 1. 删除所有表
        SQLModel.metadata.drop_all(engine)
        logger.info("✓ 已删除所有表")
        
        # 2. 重新创建所有表
        init_db()
        logger.info("✓ 已重新创建所有表")
        
        # 3. 重新填充初始数据
        seed_defaults()
        logger.info("✓ 已重新填充初始数据")
        
        # 4. 清理所有数据目录
        current_settings = get_settings()
        _clear_directory(Path(current_settings.saves_dir))
        _clear_directory(Path(current_settings.exports_dir))
        _clear_directory(Path(current_settings.reports_dir))
        
        # 清理embedding缓存
        cache_dir = Path(current_settings.embedding_cache_dir) if hasattr(current_settings, 'embedding_cache_dir') else Path("data/cache/embeddings")
        _clear_directory(cache_dir)
        logger.info("✓ 已清理数据目录")
        
        return {
            "success": True, 
            "message": "数据库已完全重置。所有表已删除并重新创建，初始数据已重新填充。"
        }
        
    except Exception as e:
        logger.error(f"清空数据库失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空数据库失败: {str(e)}")
