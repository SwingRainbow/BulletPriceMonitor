"""
监控引擎
核心监控逻辑，与 UI 解耦
通过回调函数向 UI 层推送状态更新
"""
import threading
import time
from datetime import datetime
from src.scraper import WebViewScraper, normalize
from src.config import load_watchlist, save_watchlist, load_settings
from src.notifier import send_alert


class MonitorEngine:
    """
    监控引擎
    通过 on_update / on_log / on_alert 回调向外层推送事件
    """

    def __init__(self):
        self.scraper = WebViewScraper()
        self.running = False
        self._thread = None
        self.bullet_list = load_watchlist()
        self.prev_prices = {}
        self.cur_prices = {}
        self.notified = {}  # {name: price} 已通知的补货
        self.logs = []
        self.alerts = []

        # 回调（由 UI 层设置）
        self.on_update = None   # fn() -> 刷新 UI
        self.on_log = None      # fn(msg: str) -> 写日志
        self.on_alert = None    # fn(msg: str, level: str) -> 写警报

    # ---------- 监控列表管理 ----------
    def add_bullet(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False
        if any(b['name'] == name for b in self.bullet_list):
            return False
        self.bullet_list.append({'name': name, 'threshold': 0})
        save_watchlist(self.bullet_list)
        self._log(f"✅ 添加: {name}")
        return True

    def remove_bullet(self, name: str):
        self.bullet_list = [b for b in self.bullet_list if b['name'] != name]
        save_watchlist(self.bullet_list)
        for d in (self.notified, self.prev_prices, self.cur_prices):
            d.pop(name, None)
        self._log(f"🗑 删除: {name}")

    def set_threshold(self, name: str, threshold: int):
        for b in self.bullet_list:
            if b['name'] == name:
                b['threshold'] = threshold
                save_watchlist(self.bullet_list)
                self.notified.pop(name, None)
                label = str(threshold) if threshold > 0 else '关闭'
                self._log(f"✏ {name} 检测线 → {label}")
                return

    def get_status(self) -> list:
        """返回当前所有子弹的状态列表"""
        result = []
        for b in self.bullet_list:
            name = b['name']
            threshold = b['threshold']
            price = self.cur_prices.get(name)
            prev = self.prev_prices.get(name)

            if price is None:
                status = "waiting"
                status_text = "等待数据"
            elif threshold > 0 and price <= threshold:
                status = "restock"
                status_text = f"⚠ 疑似补货 (≤{threshold})"
            elif prev is not None and price > prev:
                status = "up"
                status_text = f"↑ {prev}→{price}"
            elif prev is not None and price < prev:
                status = "down"
                status_text = f"↓ {prev}→{price}"
            else:
                status = "stable"
                status_text = "稳定"

            result.append({
                'name': name,
                'price': price,
                'threshold': threshold,
                'status': status,
                'status_text': status_text,
            })
        return result

    # ---------- 启停 ----------
    def start(self) -> bool:
        if self.running:
            return False
        if not self.bullet_list:
            return False
        self.running = True
        self._log(f"⚡ 启动监控 {len(self.bullet_list)} 种子弹")
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self.running = False
        self._log("⏸ 已停止")

    # ---------- 内部 ----------
    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self.logs.append(entry)
        # 保留最近200条
        if len(self.logs) > 200:
            self.logs = self.logs[-150:]
        if self.on_log:
            self.on_log(entry)

    def _alert(self, msg: str, level: str = "warning"):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self.alerts.append({'text': entry, 'level': level})
        if len(self.alerts) > 200:
            self.alerts = self.alerts[-150:]
        if self.on_alert:
            self.on_alert(entry, level)

    def _match(self, scraped: dict) -> dict:
        """将抓取到的数据与监控列表匹配"""
        matched = {}
        for b in self.bullet_list:
            target = normalize(b['name']).lower()

            # 第1轮：精确匹配
            for sn, p in scraped.items():
                if normalize(sn).lower() == target:
                    matched[b['name']] = p
                    break
            if b['name'] in matched:
                continue

            # 第2轮：子串匹配（带边界检查，防止 M855 匹配 M855A1）
            for sn, p in scraped.items():
                s = normalize(sn).lower()
                idx = s.find(target)
                if idx >= 0:
                    end = idx + len(target)
                    if end >= len(s) or not s[end].isalnum():
                        matched[b['name']] = p
                        break
            if b['name'] in matched:
                continue

            # 第3轮：反向子串
            for sn, p in scraped.items():
                s = normalize(sn).lower()
                idx = target.find(s)
                if idx >= 0:
                    end = idx + len(s)
                    if end >= len(target) or not target[end].isalnum():
                        matched[b['name']] = p
                        break

        return matched

    def _check_changes(self, matched: dict):
        """检测价格变动并触发警报"""
        for b in self.bullet_list:
            name = b['name']
            threshold = b['threshold']
            new_p = matched.get(name)
            old_p = self.prev_prices.get(name)

            if new_p is None or old_p is None or new_p == old_p:
                continue

            self._alert(f"{name}: {old_p}→{new_p}")

            if threshold > 0 and new_p <= threshold:
                if self.notified.get(name) != new_p:
                    self.notified[name] = new_p
                    self._alert(f"⚠ {name} 疑似补货! ({new_p} ≤ {threshold})", "critical")
                    send_alert(f"{name} 疑似补货", f"当前: {new_p}  检测线: {threshold}")
            else:
                self.notified.pop(name, None)

    def _loop(self):
        settings = load_settings()
        fails = 0

        while self.running:
            try:
                t0 = time.time()
                scraped = self.scraper.scrape()
                elapsed = time.time() - t0

                if self.scraper.error_msg:
                    self._log(f"❌ {self.scraper.error_msg}")

                if not scraped:
                    fails += 1
                    self._log(f"⚠ 读取失败 ({fails}/{settings['max_retries']})")
                    if fails >= settings['max_retries']:
                        self._log("❌ 连续失败，停止监控")
                        self.running = False
                        if self.on_update:
                            self.on_update()
                        return
                    time.sleep(settings['check_interval'])
                    continue

                fails = 0
                matched = self._match(scraped)
                self._check_changes(matched)
                self.prev_prices = self.cur_prices.copy()
                self.cur_prices = matched

                miss = [b['name'] for b in self.bullet_list if b['name'] not in matched]
                pages = f" ({self.scraper.total_pages}页)" if self.scraper.total_pages > 1 else ""

                if miss:
                    self._log(f"✓ {elapsed:.1f}s {len(matched)}种{pages} | 未找到: {', '.join(miss)}")
                else:
                    self._log(f"✓ {elapsed:.1f}s {len(matched)}种{pages}")

                if self.on_update:
                    self.on_update()

                time.sleep(settings['check_interval'])

            except Exception as e:
                self._log(f"❌ {e}")
                time.sleep(settings['check_interval'])
