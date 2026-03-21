"""
交易数据存储模块
负责读写交易流水 txt 文件
支持通过 set_trade_file() 切换文件路径
"""
import os
from datetime import datetime
from src.config import BASE_DIR, _ensure_dir

# 当前交易文件路径（可通过 set_trade_file 切换）
_trade_file = os.path.join(BASE_DIR, "config", "trades.txt")


def set_trade_file(filepath: str):
    """切换交易文件路径"""
    global _trade_file
    _trade_file = filepath


def get_trade_file_name() -> str:
    """获取当前文件名"""
    if os.path.exists(_trade_file):
        return os.path.basename(_trade_file)
    return ''


def _load_lines() -> list:
    try:
        if os.path.exists(_trade_file):
            with open(_trade_file, 'r', encoding='utf-8') as f:
                return [l.rstrip('\n\r') for l in f.readlines() if l.strip()]
    except Exception:
        pass
    return []


def _save_lines(lines: list):
    try:
        _ensure_dir(_trade_file)
        with open(_trade_file, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line + '\n')
    except Exception as e:
        print(f"[TradeStore] 保存失败: {e}")


def get_all_trades() -> list:
    return _load_lines()


def append_trade(action: str, name: str, unit_price: int, qty: int) -> str:
    now = datetime.now()
    time_str = f"{now.year}/{now.month}/{now.day} {now.hour}:{now.minute:02d}"
    line = f"{time_str}\t{action.ljust(4)}\t{name.ljust(10)}\t单价:{str(unit_price).ljust(8)}\t数量:{qty}只"
    lines = _load_lines()
    lines.append(line)
    _save_lines(lines)
    return line


def delete_trade(index: int) -> str:
    lines = _load_lines()
    if 0 <= index < len(lines):
        deleted = lines.pop(index)
        _save_lines(lines)
        return deleted
    return ''


def undo_delete_trade(line: str, index: int):
    lines = _load_lines()
    index = min(index, len(lines))
    lines.insert(index, line)
    _save_lines(lines)


def get_trades_by_date(date_key: str) -> list:
    lines = _load_lines()
    return [l for l in lines if l.startswith(date_key)]