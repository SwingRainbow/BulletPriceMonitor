"""
配置管理模块
负责加载/保存监控列表和应用设置
"""
import json
import os
import sys

# ---------- 路径 ----------
def _get_base_dir():
    """获取基础目录（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = _get_base_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "config", "watchlist.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "config", "settings.json")

# ---------- 默认配置 ----------
DEFAULT_SETTINGS = {
    "check_interval": 10,
    "timeout": 10,
    "max_retries": 5,
    "url": "https://orzice.com/v/ammo",
    "theme": "dark",
}

# ---------- 工具函数 ----------
def _ensure_dir(filepath):
    d = os.path.dirname(filepath)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

# ---------- 监控列表 ----------
def load_watchlist() -> list:
    """
    加载监控子弹列表
    返回 [{'name': str, 'buy_threshold': int, 'sell_threshold': int}, ...]
    兼容旧格式自动迁移
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data.get('bullets', [])
                if not items:
                    return []
                # 兼容旧格式（纯字符串列表）
                if isinstance(items[0], str):
                    return [{'name': b, 'buy_threshold': 0, 'sell_threshold': 0} for b in items]
                # 兼容旧格式（单 threshold）
                migrated = []
                for b in items:
                    if 'buy_threshold' not in b:
                        migrated.append({
                            'name': b.get('name', ''),
                            'buy_threshold': b.get('threshold', 0),
                            'sell_threshold': 0,
                        })
                    else:
                        migrated.append(b)
                return migrated
    except Exception:
        pass
    return []

def save_watchlist(bullets: list):
    """保存监控子弹列表"""
    try:
        _ensure_dir(CONFIG_FILE)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'bullets': bullets}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Config] 保存监控列表失败: {e}")

# ---------- 应用设置 ----------
def load_settings() -> dict:
    """加载应用设置"""
    settings = DEFAULT_SETTINGS.copy()
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                settings.update(saved)
    except Exception:
        pass
    return settings

def save_settings(settings: dict):
    """保存应用设置"""
    try:
        _ensure_dir(SETTINGS_FILE)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Config] 保存设置失败: {e}")