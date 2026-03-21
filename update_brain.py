"""
大脑数据更新脚本
读取 econ_worker 的输出，自动更新 brain/market_data.md
支持去重：相同数据不重复记录，只记录时间戳

用法:
  方式1（推荐）: 直接运行，自动调用 econ_worker 抓取数据然后更新
    python update_brain.py

  方式2: 手动传入 econ_worker 的 JSON 输出
    python update_brain.py econ_data.json
"""
import json
import hashlib
import os
import sys
import subprocess
from datetime import datetime
import unicodedata

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(BASE_DIR, "brain")
MARKET_DATA_FILE = os.path.join(BRAIN_DIR, "market_data.md")
HISTORY_DIR = os.path.join(BASE_DIR, "config", "brain_history")
DEDUP_FILE = os.path.join(BRAIN_DIR, "last_hash.json")


def _ensure_dir(path):
    """确保目录存在"""
    if os.path.splitext(path)[1]:
        d = os.path.dirname(path)
    else:
        d = path
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _run_econ_worker() -> dict:
    """运行 econ_worker 并返回 JSON 数据"""
    print("[Brain] 正在抓取 orzice 数据...")
    cmd = [sys.executable, os.path.join(BASE_DIR, "src", "econ_worker.py")]
    kw = {"capture_output": True, "text": True, "timeout": 120}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    result = subprocess.run(cmd, **kw)
    if result.returncode != 0:
        print(f"[Brain] econ_worker 失败: {result.stderr[:200]}")
        return {}
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        print(f"[Brain] JSON 解析失败: {e}")
        return {}


def _data_hash(data: dict) -> str:
    """计算数据的哈希值用于去重"""
    # 只对实际价格数据做哈希，忽略时间戳
    key_data = {}
    for section in ['profit', 'topchange', 'restock']:
        if section in data and 'data' in data[section]:
            key_data[section] = data[section]['data']
    raw = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode()).hexdigest()


def _check_dedup(new_hash: str) -> tuple:
    """检查是否和上次数据相同。返回 (is_dup, last_times)"""
    if not os.path.exists(DEDUP_FILE):
        return False, []
    try:
        with open(DEDUP_FILE, 'r', encoding='utf-8') as f:
            info = json.load(f)
        if info.get('hash') == new_hash:
            return True, info.get('times', [])
        return False, []
    except Exception:
        return False, []


def _save_dedup(hash_val: str, times: list):
    """保存去重信息"""
    _ensure_dir(DEDUP_FILE)
    with open(DEDUP_FILE, 'w', encoding='utf-8') as f:
        json.dump({'hash': hash_val, 'times': times}, f, ensure_ascii=False)


# ===== 表格对齐工具 =====

def _display_width(s: str) -> int:
    """计算字符串显示宽度（中文占2，英文占1）"""
    w = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ('F', 'W'):
            w += 2
        else:
            w += 1
    return w


def _pad(s: str, target_width: int) -> str:
    """用空格填充字符串到目标显示宽度"""
    current = _display_width(s)
    return s + ' ' * max(0, target_width - current)


def _aligned_table(headers: list, rows: list) -> str:
    """生成对齐的 Markdown 表格"""
    # 计算每列最大宽度
    col_widths = [_display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], _display_width(str(cell)))

    # 生成表头
    header_line = '| ' + ' | '.join(_pad(h, col_widths[i]) for i, h in enumerate(headers)) + ' |'
    sep_line = '|' + '|'.join('-' * (w + 2) for w in col_widths) + '|'

    # 生成数据行
    data_lines = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            w = col_widths[i] if i < len(col_widths) else 10
            cells.append(_pad(str(cell), w))
        data_lines.append('| ' + ' | '.join(cells) + ' |')

    return '\n'.join([header_line, sep_line] + data_lines)


# ===== 数据解析 =====

def _parse_profit(raw_data: str) -> list:
    items = []
    for line in raw_data.strip().split('\n'):
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def _parse_vue_data(raw_data: str) -> dict:
    if raw_data.startswith('VUE:'):
        raw_data = raw_data[4:]
    try:
        return json.loads(raw_data)
    except json.JSONDecodeError:
        return {}


def _grade3_only(items: list) -> list:
    return [i for i in items if i.get('grade') == 3]


def _build_restock_table(restock_data: dict) -> dict:
    table = {}
    for hour_block in restock_data.get('data', []):
        hour = hour_block.get('hour', -1)
        for item in hour_block.get('data', []):
            if item.get('grade') != 3:
                continue
            name = item['name']
            price = item['price']
            if name not in table:
                table[name] = {}
            table[name][hour] = price
    return table


# ===== Markdown 生成 =====

def _build_market_data_md(data: dict, fetch_times: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append("# 三角洲行动 · 市场数据（自动更新）\n")
    lines.append(f"> **最后更新**：{now}")
    if len(fetch_times) > 1:
        lines.append(f"> **本次数据与上次相同**，已拉取 {len(fetch_times)} 次：{', '.join(fetch_times)}")
    lines.append("> **维护方式**：由 `update_brain.py` 自动生成")
    lines.append("> **配套文件**：`knowledge.md`（固定知识）\n")
    lines.append("---\n")

    # 解析数据
    profit_items = []
    topchange = {}
    restock = {}

    if 'profit' in data and 'data' in data['profit']:
        profit_items = _parse_profit(data['profit']['data'])
    if 'topchange' in data and 'data' in data['topchange']:
        topchange = _parse_vue_data(data['topchange']['data'])
    if 'restock' in data and 'data' in data['restock']:
        restock = _parse_vue_data(data['restock']['data'])

    today_up = _grade3_only(topchange.get('tops_2', []))
    today_down = _grade3_only(topchange.get('tops_1', []))
    week_up = _grade3_only(topchange.get('tops_4', []))
    week_down = _grade3_only(topchange.get('tops_3', []))
    month_up = _grade3_only(topchange.get('tops_6', []))
    month_down = _grade3_only(topchange.get('tops_5', []))

    restock_table = _build_restock_table(restock)
    profit_g3 = sorted([p for p in profit_items if p.get('grade') == 3],
                       key=lambda x: x.get('bl', 0), reverse=True)

    # 汇总所有三级弹
    all_g3_names = set()
    for item in restock_table:
        all_g3_names.add(item)
    for lst in [today_up, today_down, week_up, week_down, month_up, month_down]:
        for item in lst:
            all_g3_names.add(item['name'])
    for item in profit_g3:
        all_g3_names.add(item['name'])

    summary = {}
    for name in sorted(all_g3_names):
        summary[name] = {'rp': None, 'cp': None, 'tb': None, 'wb': None, 'mb': None}
        if name in restock_table:
            summary[name]['rp'] = min(restock_table[name].values())
    for item in today_up + today_down:
        if item['name'] in summary:
            summary[item['name']]['cp'] = item.get('price')
            summary[item['name']]['tb'] = item.get('bl')
    for item in week_up + week_down:
        if item['name'] in summary:
            if summary[item['name']]['cp'] is None:
                summary[item['name']]['cp'] = item.get('price')
            summary[item['name']]['wb'] = item.get('bl')
    for item in month_up + month_down:
        if item['name'] in summary:
            if summary[item['name']]['cp'] is None:
                summary[item['name']]['cp'] = item.get('price')
            summary[item['name']]['mb'] = item.get('bl')

    # === 综合数据表 ===
    lines.append("## 一、三级弹完整数据\n")
    headers = ['弹种名称', '补货价', '当前价', '今日涨跌', '7日涨跌', '30日涨跌']
    rows = []
    for name in sorted(summary.keys()):
        d = summary[name]
        rows.append([
            name,
            str(d['rp']) if d['rp'] else '—',
            str(d['cp']) if d['cp'] else '—',
            f"{d['tb']:+.2f}%" if d['tb'] is not None else '—',
            f"{d['wb']:+.2f}%" if d['wb'] is not None else '—',
            f"{d['mb']:+.2f}%" if d['mb'] is not None else '—',
        ])
    lines.append(_aligned_table(headers, rows))

    # === 补货时间表 ===
    lines.append("\n---\n")
    lines.append("## 二、补货时间表\n")
    h2 = ['弹种', '0时', '1时', '2时', '3时', '4时', '5时', '6时', '7时', '8时+']
    r2 = []
    for name in sorted(restock_table.keys()):
        hours = restock_table[name]
        cols = [name]
        for h in range(8):
            cols.append(f"✓{hours[h]}" if h in hours else "")
        late = [f"{h}时✓{hours[h]}" for h in sorted(hours.keys()) if h >= 8]
        cols.append(", ".join(late) if late else "")
        r2.append(cols)
    lines.append(_aligned_table(h2, r2))

    # === 昨日收益 ===
    lines.append("\n---\n")
    lines.append("## 三、昨日收益率排行（三级弹）\n")
    if profit_g3:
        h3 = ['弹种', '最低价', '最低时间', '最高价', '最高时间', '单发利润', '收益率']
        r3 = []
        for p in profit_g3:
            r3.append([
                p['name'], str(p['price_min']), f"{p['hour_min']}时",
                str(p['price_max']), f"{p['hour_max']}时",
                f"{p['profit']:.0f}", f"{p['bl']}%"
            ])
        lines.append(_aligned_table(h3, r3))
    else:
        lines.append("（无数据）")

    # === 涨跌排行 ===
    for title, items in [
        ("四、今日涨幅Top（三级弹）", today_up),
        ("五、今日跌幅Top（三级弹）", today_down),
        ("六、7日涨幅Top（三级弹）", week_up),
        ("七、7日跌幅Top（三级弹）", week_down),
        ("八、30日涨幅Top（三级弹）", month_up),
        ("九、30日跌幅Top（三级弹）", month_down),
    ]:
        lines.append(f"\n## {title}\n")
        if items:
            ht = ['弹种', '当前价', '涨跌幅']
            rt = [[i['name'], str(i['price']), f"{i['bl']:+.2f}%"] for i in items]
            lines.append(_aligned_table(ht, rt))
        else:
            lines.append("（无三级弹数据）")

    # === 价值分级 ===
    lines.append("\n---\n")
    lines.append("## 十、价值分级（基于当日数据）\n")
    s_tier = [p['name'] for p in profit_g3[:2]] if len(profit_g3) >= 2 else []
    a_tier_names = []
    for i in (today_up + week_up):
        if i['name'] not in s_tier and i['name'] not in a_tier_names:
            a_tier_names.append(i['name'])
    c_tier = [i['name'] for i in month_down]

    lines.append(f"- **S级（高利润）**：{', '.join(s_tier) if s_tier else '（数据不足）'}")
    lines.append(f"- **A级（涨势好）**：{', '.join(a_tier_names[:5]) if a_tier_names else '（数据不足）'}")
    lines.append(f"- **C级（近期下跌）**：{', '.join(c_tier) if c_tier else '无'}")

    lines.append(f"\n---\n\n> 数据快照时间：{now}")
    lines.append("> ⚠️ 单日数据仅供参考，需连续多日积累才能确认规律")

    return '\n'.join(lines)


# ===== 主入口 =====

def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = _run_econ_worker()

    if not data:
        print("[Brain] 无数据，退出")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 去重检查
    new_hash = _data_hash(data)
    is_dup, last_times = _check_dedup(new_hash)

    if is_dup:
        last_times.append(now_str)
        _save_dedup(new_hash, last_times)
        # 即使重复也更新 md（刷新时间戳列表）
        md_content = _build_market_data_md(data, last_times)
        with open(MARKET_DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"[Brain] 数据未变化（第{len(last_times)}次拉取），已更新时间记录")
        return

    # 新数据
    fetch_times = [now_str]
    _save_dedup(new_hash, fetch_times)

    # 保存原始数据到历史
    _ensure_dir(HISTORY_DIR)
    today = datetime.now().strftime("%Y-%m-%d")
    history_file = os.path.join(HISTORY_DIR, f"{today}.json")
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[Brain] 原始数据已保存: {history_file}")

    # 生成 market_data.md
    _ensure_dir(BRAIN_DIR)
    md_content = _build_market_data_md(data, fetch_times)
    with open(MARKET_DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"[Brain] 已更新: {MARKET_DATA_FILE}")


if __name__ == '__main__':
    main()