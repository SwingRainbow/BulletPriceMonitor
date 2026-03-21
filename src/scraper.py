"""
抓取模块
通过子进程启动独立 webview 抓取价格
开发模式: python run.py (子进程调 python run.py --worker)
打包模式: BulletPriceMonitor.exe (子进程调 BulletPriceMonitor.exe --worker)
"""
import json
import os
import re
import subprocess
import sys


def normalize(text: str) -> str:
    text = text.replace('\u00d7', 'x').replace('\uff58', 'x')
    text = text.replace('\u2715', 'x').replace('\u2716', 'x')
    return re.sub(r'\s+', ' ', text).strip()


def _get_run_py():
    """获取 run.py 路径（开发模式下子进程需要从 run.py 启动）"""
    if getattr(sys, 'frozen', False):
        return None  # 打包模式不需要
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'run.py')


class WebViewScraper:
    """通过子进程抓取价格，与主 UI 完全隔离"""

    def __init__(self):
        self.total_pages = 0
        self.error_msg = None

    def scrape(self) -> dict:
        self.error_msg = None

        try:
            # 构建子进程命令
            if getattr(sys, 'frozen', False):
                # 打包模式: 用自身 exe + --worker
                cmd = [sys.executable, '--worker']
            else:
                # 开发模式: python run.py --worker
                cmd = [sys.executable, _get_run_py(), '--worker']

            kw = {
                'capture_output': True,
                'text': True,
                'timeout': 45,
            }
            if sys.platform == 'win32':
                kw['creationflags'] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(cmd, **kw)

            if result.returncode != 0:
                stderr = result.stderr.strip()
                self.error_msg = f"子进程退出码 {result.returncode}: {stderr[:200]}"
                return {}

            stdout = result.stdout.strip()
            if not stdout:
                self.error_msg = "子进程无输出"
                return {}

            data = json.loads(stdout)

            if 'error' in data:
                self.error_msg = data['error']
                return {}

            self.total_pages = data.get('pages', 1)
            bullets = self._parse_raw(data.get('page1', ''))
            extra_raw = data.get('extra', '')
            if extra_raw:
                bullets.update(self._parse_raw(extra_raw))

            if not bullets:
                self.error_msg = "未提取到价格数据"

            return bullets

        except subprocess.TimeoutExpired:
            self.error_msg = "抓取超时(45s)"
            return {}
        except json.JSONDecodeError as e:
            self.error_msg = f"JSON解析失败: {e}"
            return {}
        except Exception as e:
            self.error_msg = str(e)
            return {}

    def _parse_raw(self, raw) -> dict:
        result = {}
        if not raw or not isinstance(raw, str):
            return result
        for line in raw.strip().split('\n'):
            line = line.strip()
            if '|' not in line:
                continue
            parts = line.split('|', 1)
            if len(parts) == 2:
                name = parts[0].strip()
                try:
                    price = int(parts[1].strip().replace(',', ''))
                    result[name] = price
                except ValueError:
                    continue
        return result
