"""
大脑数据更新模块
从 econ_worker 获取数据，更新 brain/market_data.md
支持去重：相同数据不重复记录，只记录时间戳

可被 app.py 直接调用（打包模式），也可被 update_brain.py 调用（开发模式）
"""
import json
import hashlib
import os
import sys
import subprocess
import unicodedata
from datetime import datetime


def _get_base_dir():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _get_base_dir()
BRAIN_DIR = os.path.join(BASE_DIR, "brain")
MARKET_DATA_FILE = os.path.join(BRAIN_DIR, "market_data.md")
FETCH_LOG_FILE = os.path.join(BRAIN_DIR, "fetch_log.md")
HISTORY_DIR = os.path.join(BASE_DIR, "config", "brain_history")
DEDUP_FILE = os.path.join(BRAIN_DIR, "last_hash.json")


def _ensure_dir(path):
    if os.path.splitext(path)[1]:
        d = os.path.dirname(path)
    else:
        d = path
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


# ===== econ_worker 调用 =====

def _run_econ_worker() -> dict:
    """通过子进程运行 econ_worker 并返回 JSON 数据"""
    if getattr(sys, 'frozen', False):
        cmd = [sys.executable, '--econ-worker']
    else:
        run_py = os.path.join(BASE_DIR, 'run.py')
        cmd = [sys.executable, run_py, '--econ-worker']

    kw = {"capture_output": True, "text": True, "timeout": 120}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW

    result = subprocess.run(cmd, **kw)
    if result.returncode != 0:
        raise RuntimeError(f"econ_worker 失败: {result.stderr[:200]}")
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON 解析失败: {e}")


# ===== 去重 =====

def _data_hash(data: dict) -> str:
    key_data = {}
    for section in ['profit', 'topchange', 'restock']:
        if section in data and 'data' in data[section]:
            key_data[section] = data[section]['data']
    raw = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode()).hexdigest()


def _check_dedup(new_hash: str) -> tuple:
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
    _ensure_dir(DEDUP_FILE)
    with open(DEDUP_FILE, 'w', encoding='utf-8') as f:
        json.dump({'hash': hash_val, 'times': times}, f, ensure_ascii=False)


# ===== 表格对齐 =====

def _display_width(s: str) -> int:
    w = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ('F', 'W'):
            w += 2
        else:
            w += 1
    return w


def _pad(s: str, target_width: int) -> str:
    current = _display_width(s)
    return s + ' ' * max(0, target_width - current)


def _aligned_table(headers: list, rows: list) -> str:
    col_widths = [_display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], _display_width(str(cell)))
    header_line = '| ' + ' | '.join(_pad(h, col_widths[i]) for i, h in enumerate(headers)) + ' |'
    sep_line = '|' + '|'.join('-' * (w + 2) for w in col_widths) + '|'
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

    # 综合数据表
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

    # 补货时间表
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

    # 昨日收益
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

    # 涨跌排行
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

    # 价值分级
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


# ===== 拉取日志 =====

def _extract_summary(data: dict) -> str:
    """从原始数据提取关键摘要，用于日志记录"""
    lines = []

    # 昨日收益
    if 'profit' in data and 'data' in data['profit']:
        items = _parse_profit(data['profit']['data'])
        g3 = sorted([p for p in items if p.get('grade') == 3],
                     key=lambda x: x.get('bl', 0), reverse=True)
        if g3:
            parts = [f"{p['name']} {p['bl']}%" for p in g3[:3]]
            lines.append(f"  - 昨日收益Top: {', '.join(parts)}")

    # 今日涨幅
    if 'topchange' in data and 'data' in data['topchange']:
        tc = _parse_vue_data(data['topchange']['data'])
        today_up = _grade3_only(tc.get('tops_2', []))
        if today_up:
            parts = [f"{i['name']} {i['bl']:+.2f}%" for i in today_up[:3]]
            lines.append(f"  - 今日涨幅Top: {', '.join(parts)}")
        today_down = _grade3_only(tc.get('tops_1', []))
        if today_down:
            parts = [f"{i['name']} {i['bl']:+.2f}%" for i in today_down[:3]]
            lines.append(f"  - 今日跌幅Top: {', '.join(parts)}")

    return '\n'.join(lines) if lines else '  - （无三级弹数据）'


def _write_fetch_log(time_str: str, is_dup: bool, summary: str = ''):
    """追加写入拉取日志"""
    _ensure_dir(FETCH_LOG_FILE)

    today = datetime.now().strftime("%Y-%m-%d")
    time_only = time_str.split(' ')[-1] if ' ' in time_str else time_str

    # 读取已有内容
    existing = ''
    if os.path.exists(FETCH_LOG_FILE):
        with open(FETCH_LOG_FILE, 'r', encoding='utf-8') as f:
            existing = f.read()

    # 检查今天的日期标题是否已存在
    date_header = f"## {today}"
    if date_header not in existing:
        # 新的一天，在文件开头插入日期标题（保持倒序，最新在上面）
        header = "# 拉取日志\n\n> 用于分析 orzice 数据刷新规律\n\n"
        if existing.startswith("# 拉取日志"):
            # 已有文件头，在第一个 ## 之前插入新日期
            pos = existing.find('\n## ')
            if pos >= 0:
                existing = existing[:pos] + f"\n{date_header}\n\n" + existing[pos+1:]
            else:
                existing = existing.rstrip() + f"\n\n{date_header}\n\n"
        else:
            existing = header + f"{date_header}\n\n"

    # 构造日志条目
    if is_dup:
        entry = f"### {time_only} — 数据未变化\n\n"
    else:
        entry = f"### {time_only} — 新数据\n\n{summary}\n\n"

    # 在今天的日期标题后面追加条目
    insert_pos = existing.find(date_header) + len(date_header)
    # 跳过日期标题后的换行
    while insert_pos < len(existing) and existing[insert_pos] == '\n':
        insert_pos += 1

    existing = existing[:insert_pos] + entry + existing[insert_pos:]

    with open(FETCH_LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(existing)


# ===== 主入口 =====

def run_update(data: dict = None) -> dict:
    """
    执行大脑数据更新
    参数 data: 如果传入则直接使用，否则自动调用 econ_worker 抓取
    返回: {'status': 'ok'|'dup'|'error', 'message': str}
    """
    try:
        if data is None:
            data = _run_econ_worker()

        if not data:
            return {'status': 'error', 'message': '无数据'}

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_hash = _data_hash(data)
        is_dup, last_times = _check_dedup(new_hash)

        if is_dup:
            last_times.append(now_str)
            _save_dedup(new_hash, last_times)
            md_content = _build_market_data_md(data, last_times)
            _ensure_dir(MARKET_DATA_FILE)
            with open(MARKET_DATA_FILE, 'w', encoding='utf-8') as f:
                f.write(md_content)
            # 写入拉取日志（重复数据）
            _write_fetch_log(now_str, is_dup=True)
            return {'status': 'dup', 'message': f'数据未变化（第{len(last_times)}次拉取）'}

        fetch_times = [now_str]
        _save_dedup(new_hash, fetch_times)

        # 提取数据摘要用于日志
        summary = _extract_summary(data)

        # 保存原始数据到历史
        _ensure_dir(HISTORY_DIR)
        today = datetime.now().strftime("%Y-%m-%d")
        history_file = os.path.join(HISTORY_DIR, f"{today}.json")
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 生成 market_data.md
        _ensure_dir(BRAIN_DIR)
        md_content = _build_market_data_md(data, fetch_times)
        with open(MARKET_DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # 写入拉取日志（新数据）
        _write_fetch_log(now_str, is_dup=False, summary=summary)

        return {'status': 'ok', 'message': '数据已更新'}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}