"""
经济学数据抓取 worker
抓取 orzice.com 的子弹经济学页面数据：
  - 昨日倒子弹最高收益
  - 子弹涨跌Top
  - 子弹低价补货预测

与 scraper_worker.py 同样的原理：用 webview 加载页面，执行 JS 提取渲染后的数据

可以直接运行: python src/econ_worker.py
也可以通过 run.py --econ-worker 调用
"""
import webview
import time
import threading
import json
import sys


# === 昨日倒子弹最高收益 ===
# 页面结构：每条数据包含弹种名、最低价(时间)、最高价(时间)、利润、收益率
JS_EXTRACT_PROFIT = """
(function() {
    var results = [];
    // 页面用 Vue 渲染，数据在 DOM 中
    var cards = document.querySelectorAll('.card, .box, [class*="item"], [class*="row"]');
    
    // 尝试从 Vue 实例直接拿数据
    try {
        var app = document.querySelector('#app') || document.querySelector('[id]');
        if (app && app.__vue__) {
            var vm = app.__vue__;
            // 尝试常见的数据属性名
            var data = vm.list || vm.items || vm.data || vm.ammoList || vm.$data;
            if (data && Array.isArray(data)) {
                data.forEach(function(item) {
                    results.push(JSON.stringify(item));
                });
                if (results.length > 0) return results.join('\\n');
            }
        }
    } catch(e) {}
    
    // 备选：从页面文本提取
    var allText = document.body.innerText;
    return 'RAW:' + allText.substring(0, 8000);
})()
"""

# === 子弹涨跌Top ===
JS_EXTRACT_TOPCHANGE = """
(function() {
    var results = [];
    try {
        var app = document.querySelector('#app') || document.querySelector('[id]');
        if (app && app.__vue__) {
            var vm = app.__vue__;
            var data = vm.list || vm.items || vm.data || vm.upList || vm.downList || vm.$data;
            if (data) {
                return 'VUE:' + JSON.stringify(vm.$data);
            }
        }
    } catch(e) {}
    var allText = document.body.innerText;
    return 'RAW:' + allText.substring(0, 8000);
})()
"""

# === 子弹低价补货预测 ===
JS_EXTRACT_RESTOCK = """
(function() {
    var results = [];
    try {
        var app = document.querySelector('#app') || document.querySelector('[id]');
        if (app && app.__vue__) {
            var vm = app.__vue__;
            var data = vm.list || vm.items || vm.data || vm.$data;
            if (data) {
                return 'VUE:' + JSON.stringify(vm.$data);
            }
        }
    } catch(e) {}
    var allText = document.body.innerText;
    return 'RAW:' + allText.substring(0, 8000);
})()
"""


PAGES = [
    {
        'key': 'profit',
        'url': 'https://orzice.com/v/ammo_zr_yz',
        'js': JS_EXTRACT_PROFIT,
        'desc': '昨日倒子弹最高收益',
    },
    {
        'key': 'topchange',
        'url': 'https://orzice.com/v/ammo_pay',
        'js': JS_EXTRACT_TOPCHANGE,
        'desc': '子弹涨跌Top',
    },
    {
        'key': 'restock',
        'url': 'https://orzice.com/v/ammo_day',
        'js': JS_EXTRACT_RESTOCK,
        'desc': '子弹低价补货预测',
    },
]


def _run(window):
    output = {}
    try:
        for page in PAGES:
            try:
                time.sleep(1)
                window.load_url(page['url'])
                time.sleep(6)  # 等待页面加载和 JS 渲染

                raw = window.evaluate_js(page['js']) or ''
                output[page['key']] = {
                    'desc': page['desc'],
                    'url': page['url'],
                    'data': raw,
                }
            except Exception as e:
                output[page['key']] = {
                    'desc': page['desc'],
                    'url': page['url'],
                    'error': str(e),
                }

        sys.stdout.write(json.dumps(output, ensure_ascii=False))
        sys.stdout.flush()

    except Exception as e:
        sys.stdout.write(json.dumps({'error': str(e)}))
        sys.stdout.flush()
    finally:
        window.destroy()


def run_econ_worker():
    """入口函数"""
    w = webview.create_window(
        'econ_scraper',
        html='<html><body></body></html>',
        hidden=True,
        width=800,
        height=600,
    )
    threading.Thread(target=_run, args=(w,), daemon=True).start()
    webview.start(gui='edgechromium')


if __name__ == '__main__':
    run_econ_worker()
