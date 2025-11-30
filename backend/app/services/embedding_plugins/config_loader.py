"""插件配置加载器

从 embedding_plugins.yaml 和 stage_config.yaml 加载插件配置，支持：
- enable: bool - 是否启用
- update_frequency: int - 更新频率
- params: dict - 插件特定参数

加载优先级（后者覆盖前者）：
1. embedding_plugins.yaml 中的插件默认配置
2. embedding_plugins.yaml 中的 mode_presets
3. stage_config.yaml 中的 embedding_plugins.plugins 配置
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import yaml

from .base import PluginConfig

logger = logging.getLogger(__name__)

# 配置文件路径
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
_PLUGIN_CONFIG_FILE = _CONFIG_DIR / "embedding_plugins.yaml"
_STAGE_CONFIG_FILE = Path(__file__).parent.parent.parent / "simulation" / "stage_config.yaml"

# 缓存
_config_cache: dict[str, Any] = {}
_cache_time: float = 0
_CACHE_TTL = 60  # 秒


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """加载 YAML 文件"""
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"[PluginConfig] 加载 {path} 失败: {e}")
        return {}


def _get_plugin_base_config() -> dict[str, Any]:
    """获取插件基础配置（带缓存）"""
    global _config_cache, _cache_time
    
    now = time.time()
    if _config_cache and (now - _cache_time) < _CACHE_TTL:
        return _config_cache
    
    _config_cache = _load_yaml_file(_PLUGIN_CONFIG_FILE)
    _cache_time = now
    return _config_cache


def load_plugin_configs(
    yaml_path: Path | str | None = None,
    mode: str = "full"
) -> dict[str, PluginConfig]:
    """从 YAML 配置加载插件配置
    
    Args:
        yaml_path: stage_config.yaml 路径（可选）
        mode: 模式名称（minimal/standard/full/debug）
        
    Returns:
        {plugin_name: PluginConfig} 字典
    """
    result: dict[str, PluginConfig] = {}
    
    # 1. 加载插件基础配置
    base_config = _get_plugin_base_config()
    defaults = base_config.get("defaults", {})
    plugins_config = base_config.get("plugins", {})
    
    # 2. 应用插件默认配置
    for name, cfg in plugins_config.items():
        if not isinstance(cfg, dict):
            cfg = {}
        
        result[name] = PluginConfig(
            enabled=cfg.get("enabled", defaults.get("enabled", True)),
            update_frequency=cfg.get("update_frequency", defaults.get("update_frequency", 1)),
            cache_ttl=cfg.get("cache_ttl", defaults.get("cache_ttl", 10)),
            fallback_on_error=cfg.get("fallback_on_error", defaults.get("fallback_on_error", True)),
            params=cfg.get("params", {}),
        )
    
    # 3. 应用模式预设
    mode_presets = base_config.get("mode_presets", {})
    if mode in mode_presets:
        preset = mode_presets[mode]
        enabled_plugins = set(preset.get("enabled_plugins", []))
        overrides = preset.get("overrides", {})
        
        # 更新启用状态
        for name in result:
            result[name] = PluginConfig(
                enabled=name in enabled_plugins,
                update_frequency=result[name].update_frequency,
                cache_ttl=result[name].cache_ttl,
                fallback_on_error=result[name].fallback_on_error,
                params=result[name].params.copy(),
            )
        
        # 应用覆盖
        for name, override in overrides.items():
            if name in result:
                result[name] = PluginConfig(
                    enabled=result[name].enabled,
                    update_frequency=override.get("update_frequency", result[name].update_frequency),
                    cache_ttl=override.get("cache_ttl", result[name].cache_ttl),
                    fallback_on_error=override.get("fallback_on_error", result[name].fallback_on_error),
                    params={**result[name].params, **override.get("params", {})},
                )
    
    # 4. 加载 stage_config.yaml 中的覆盖（最高优先级）
    if yaml_path is None:
        yaml_path = _STAGE_CONFIG_FILE
    elif isinstance(yaml_path, str):
        yaml_path = Path(yaml_path)
    
    stage_overrides = _parse_stage_config_plugins(yaml_path, mode)
    for name, cfg in stage_overrides.items():
        if name in result:
            result[name] = PluginConfig(
                enabled=cfg.enabled,
                update_frequency=cfg.update_frequency if cfg.update_frequency != 1 else result[name].update_frequency,
                cache_ttl=cfg.cache_ttl if cfg.cache_ttl != 10 else result[name].cache_ttl,
                fallback_on_error=cfg.fallback_on_error,
                params={**result[name].params, **cfg.params},
            )
        else:
            result[name] = cfg
    
    logger.info(f"[PluginConfig] 模式 {mode}: 启用 {sum(1 for c in result.values() if c.enabled)}/{len(result)} 个插件")
    return result


def _parse_stage_config_plugins(yaml_path: Path, mode: str) -> dict[str, PluginConfig]:
    """解析 stage_config.yaml 中的插件配置"""
    result: dict[str, PluginConfig] = {}
    
    config = _load_yaml_file(yaml_path)
    if not config:
        return result
    
    modes = config.get("modes", {})
    mode_config = modes.get(mode, {})
    
    # 查找 embedding_plugins stage 配置
    stages = mode_config.get("stages", [])
    for stage in stages:
        if isinstance(stage, dict) and stage.get("name") == "embedding_plugins":
            stage_enabled = stage.get("enabled", True)
            plugins_config = stage.get("plugins", {})
            
            for plugin_name, plugin_cfg in plugins_config.items():
                if not isinstance(plugin_cfg, dict):
                    plugin_cfg = {}
                
                result[plugin_name] = PluginConfig(
                    enabled=plugin_cfg.get("enabled", True) and stage_enabled,
                    update_frequency=plugin_cfg.get("update_frequency", 1),
                    cache_ttl=plugin_cfg.get("cache_ttl", 10),
                    fallback_on_error=plugin_cfg.get("fallback_on_error", True),
                    params=plugin_cfg.get("params", {}),
                )
            break
    
    return result


def get_default_plugin_config(plugin_name: str) -> PluginConfig:
    """获取插件的默认配置（从 embedding_plugins.yaml 读取）"""
    base_config = _get_plugin_base_config()
    defaults = base_config.get("defaults", {})
    plugins = base_config.get("plugins", {})
    
    if plugin_name in plugins:
        cfg = plugins[plugin_name]
        return PluginConfig(
            enabled=cfg.get("enabled", defaults.get("enabled", True)),
            update_frequency=cfg.get("update_frequency", defaults.get("update_frequency", 1)),
            cache_ttl=cfg.get("cache_ttl", defaults.get("cache_ttl", 10)),
            fallback_on_error=cfg.get("fallback_on_error", defaults.get("fallback_on_error", True)),
            params=cfg.get("params", {}),
        )
    
    return PluginConfig()


def merge_configs(
    yaml_configs: dict[str, PluginConfig],
    plugin_name: str
) -> PluginConfig:
    """合并配置：yaml_configs 优先于默认配置"""
    default = get_default_plugin_config(plugin_name)
    
    if plugin_name not in yaml_configs:
        return default
    
    yaml_cfg = yaml_configs[plugin_name]
    
    # YAML 配置优先
    merged_params = {**default.params, **yaml_cfg.params}
    
    return PluginConfig(
        enabled=yaml_cfg.enabled,
        index_name=yaml_cfg.index_name or default.index_name,
        update_frequency=yaml_cfg.update_frequency,
        cache_ttl=yaml_cfg.cache_ttl,
        fallback_on_error=yaml_cfg.fallback_on_error,
        params=merged_params,
    )


def clear_config_cache() -> None:
    """清除配置缓存（测试用）"""
    global _config_cache, _cache_time
    _config_cache = {}
    _cache_time = 0


def get_all_plugin_names() -> list[str]:
    """获取所有已配置的插件名称"""
    base_config = _get_plugin_base_config()
    return list(base_config.get("plugins", {}).keys())

