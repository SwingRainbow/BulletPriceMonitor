"""
pywebview 应用桥接层
"""
import json
import os
import sys
import webview
from src.monitor import MonitorEngine
from src.config import load_settings, save_settings
from src.notifier import send_toast
from version import __version__
from updater import check_update


def _get_frontend_path():
    if getattr(sys, 'frozen', False):
        base = os.path.join(sys._MEIPASS, 'src')
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'frontend', 'index.html')


class Api:
    """暴露给 JavaScript 的 API 接口"""

    def __init__(self):
        self._engine = MonitorEngine()
        self._window = None
        self._setup_callbacks()

    def _setup_callbacks(self):
        self._engine.on_log = self._on_log
        self._engine.on_alert = self._on_alert
        self._engine.on_update = self._on_update

    def _eval_js(self, js: str):
        try:
            if self._window:
                self._window.evaluate_js(js)
        except Exception:
            pass

    def _on_log(self, msg: str):
        safe = msg.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
        self._eval_js(f"window.onPyLog('{safe}')")

    def _on_alert(self, msg: str, level: str = "warning"):
        safe = msg.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
        self._eval_js(f"window.onPyAlert('{safe}', '{level}')")

    def _on_update(self):
        self._eval_js("window.onPyUpdate()")
        if self._engine.scraper.total_pages > 0:
            self._eval_js(f"window.onPySpeed('{self._engine.scraper.total_pages}页')")
        if not self._engine.running:
            self._eval_js("window.onPyStatusChange('idle', '已停止')")

    # ===== 公开方法 =====
    def get_version(self):
        return __version__

    def check_for_update(self):
        return check_update()

    def start_monitor(self):
        return self._engine.start()

    def stop_monitor(self):
        self._engine.stop()

    def add_bullet(self, name: str):
        return self._engine.add_bullet(name)

    def remove_bullet(self, name: str):
        self._engine.remove_bullet(name)

    def set_buy_threshold(self, name: str, threshold: int):
        self._engine.set_buy_threshold(name, threshold)

    def set_sell_threshold(self, name: str, threshold: int):
        self._engine.set_sell_threshold(name, threshold)

    def get_status(self):
        return self._engine.get_status()

    def test_notification(self):
        send_toast("测试通知", "通知功能正常!")

    def set_interval(self, seconds: int):
        settings = load_settings()
        settings['check_interval'] = max(1, seconds)
        save_settings(settings)

    def get_settings(self):
        return load_settings()


def create_window():
    api = Api()
    frontend = _get_frontend_path()

    window = webview.create_window(
        title=f'⚡ 子弹价格闪电监视 v{__version__}',
        url=frontend,
        js_api=api,
        width=1100,
        height=760,
        min_size=(900, 600),
        background_color='#0d1117',
    )
    api._window = window

    webview.start(debug=False, gui='edgechromium')