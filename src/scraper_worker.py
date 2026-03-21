"""
独立抓取 worker
可以直接运行: python src/scraper_worker.py
也可以通过 run.py --worker 调用
"""
import webview
import time
import threading
import json
import sys

JS_EXTRACT_PAGE1 = """
(function() {
    var rows = document.querySelectorAll('tr.table-row');
    var results = [];
    rows.forEach(function(row) {
        var nameEl = row.querySelector('.item-name');
        var priceCells = row.querySelectorAll('td.price-cell');
        if (nameEl && priceCells.length >= 2) {
            var priceSpan = priceCells[1].querySelector('.icon-gold');
            if (priceSpan) {
                var name = nameEl.textContent.trim();
                var price = priceSpan.textContent.trim().replace(/,/g, '');
                if (name && price && !isNaN(price)) {
                    results.push(name + '|' + price);
                }
            }
        }
    });
    return results.join('\\n');
})()
"""

JS_COUNT = """
(function() {
    try {
        if (typeof AppDataVue !== 'undefined' && AppDataVue.count) {
            return '' + AppDataVue.count;
        }
    } catch(e) {}
    return '0';
})()
"""

JS_FETCH_ALL_EXTRA = """
(function() {
    var totalPages = %d;
    var allResults = [];
    for (var p = 2; p <= totalPages; p++) {
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/v/ammo?p=' + p + '&', false);
            xhr.send();
            if (xhr.status === 200) {
                var html = xhr.responseText;
                var pattern = /<div class="item-name">(.*?)<\\/div>[\\s\\S]*?<td class="price-cell">\\s*<span class="icon-gold">\\{\\{\\s*aebs\\(['"](.*?)['"]\\)\\s*\\}\\}<\\/span>/g;
                var match;
                while ((match = pattern.exec(html)) !== null) {
                    try {
                        var name = match[1].trim();
                        var decrypted = aeb(match[2]);
                        if (name && decrypted) {
                            allResults.push(name + '|' + decrypted.replace(/,/g, ''));
                        }
                    } catch(e) {}
                }
            }
        } catch(e) {}
    }
    return allResults.join('\\n');
})()
"""


def _run(window):
    try:
        time.sleep(1)
        window.load_url('https://orzice.com/v/ammo')
        time.sleep(6)

        page1 = window.evaluate_js(JS_EXTRACT_PAGE1) or ''
        count_str = window.evaluate_js(JS_COUNT)
        try:
            count = int(count_str)
        except (TypeError, ValueError):
            count = 10
        total_pages = max(1, (count + 9) // 10)

        extra = ''
        if total_pages > 1:
            extra = window.evaluate_js(JS_FETCH_ALL_EXTRA % total_pages) or ''

        output = {
            'page1': page1,
            'extra': extra,
            'count': count,
            'pages': total_pages,
        }
        sys.stdout.write(json.dumps(output, ensure_ascii=False))
        sys.stdout.flush()

    except Exception as e:
        sys.stdout.write(json.dumps({'error': str(e)}))
        sys.stdout.flush()
    finally:
        window.destroy()


def run_worker():
    """入口函数，供 run.py --worker 调用"""
    w = webview.create_window(
        'scraper',
        html='<html><body></body></html>',
        hidden=True,
        width=800,
        height=600,
    )
    threading.Thread(target=_run, args=(w,), daemon=True).start()
    webview.start(gui='edgechromium')


if __name__ == '__main__':
    run_worker()
