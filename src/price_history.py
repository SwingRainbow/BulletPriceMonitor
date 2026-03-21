"""
价格历史记录模块
每次抓取成功后，将所有子弹价格写入历史记录
按天分文件存储，格式为 JSON Lines（每行一条记录）

文件位置: config/price_history/YYYY-MM-DD.jsonl
每条记录格式:
{
    "ts": "2026-03-21 20:15:03",
    "prices": {"5.45x39mm PS": 484, "7.62x51mm BPZ": 612, ...},
    "matched": 12,
    "pages": 3
}
"""
import json
import os
from datetime import datetime
from src.config import BASE_DIR, _ensure_dir


HISTORY_DIR = os.path.join(BASE_DIR, "config", "price_history")


def _get_today_file() -> str:
    """获取今天的历史文件路径"""
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(HISTORY_DIR, f"{today}.jsonl")


def record_prices(scraped: dict, matched: dict, pages: int = 0):
    """
    记录一次抓取的价格数据

    参数:
        scraped: 抓取到的所有子弹价格 {name: price, ...}
        matched: 与监控列表匹配后的价格 {name: price, ...}
        pages: 抓取的页数
    """
    if not scraped:
        return

    filepath = _get_today_file()
    _ensure_dir(filepath)

    record = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "all_prices": scraped,
        "matched": matched,
        "total_items": len(scraped),
        "matched_items": len(matched),
        "pages": pages,
    }

    try:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"[PriceHistory] 写入失败: {e}")


def get_today_records() -> list:
    """读取今天的所有价格记录"""
    return _load_file(_get_today_file())


def get_records_by_date(date_str: str) -> list:
    """
    读取指定日期的价格记录
    date_str 格式: "2026-03-21"
    """
    filepath = os.path.join(HISTORY_DIR, f"{date_str}.jsonl")
    return _load_file(filepath)


def get_available_dates() -> list:
    """获取所有有记录的日期列表"""
    if not os.path.exists(HISTORY_DIR):
        return []
    dates = []
    for f in sorted(os.listdir(HISTORY_DIR)):
        if f.endswith('.jsonl'):
            dates.append(f.replace('.jsonl', ''))
    return dates


def get_price_series(bullet_name: str, date_str: str = None) -> list:
    """
    获取某种子弹在指定日期的价格序列
    返回: [{"ts": "...", "price": 123}, ...]
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    records = get_records_by_date(date_str)
    series = []
    for r in records:
        # 先在 all_prices 里找，再在 matched 里找
        price = r.get('all_prices', {}).get(bullet_name)
        if price is None:
            price = r.get('matched', {}).get(bullet_name)
        if price is not None:
            series.append({"ts": r["ts"], "price": price})
    return series


def get_latest_prices() -> dict:
    """获取最近一次抓取的所有价格"""
    records = get_today_records()
    if records:
        return records[-1].get('all_prices', {})
    return {}


def _load_file(filepath: str) -> list:
    """加载一个 JSONL 文件的所有记录"""
    records = []
    if not os.path.exists(filepath):
        return records
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return records
