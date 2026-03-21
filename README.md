# ⚡ 子弹价格闪电监视 v3

**BulletPriceMonitor** — 三角洲行动弹药交易价格实时监控工具

从 [orzice.com](https://orzice.com/v/ammo) 抓取弹药价格数据，实时监控价格变动，低价补货自动提醒。

## ✨ 特性

- 🖥️ **现代 UI** — pywebview + HTML/CSS/JS 深色主题仪表盘
- ⚡ **精准抓取** — 隐藏 webview 子进程，直接提取渲染后的真实价格
- 🔔 **智能提醒** — 价格低于检测线自动弹窗 + 蜂鸣
- 📊 **实时面板** — 价格变动、补货警报、运行日志一目了然
- 🔄 **自动更新** — 启动时检查 GitHub Release，自动下载新版 exe
- 📦 **一键打包** — PyInstaller 单文件 exe + GitHub Actions 自动发版

## 🚀 快速开始

### 下载 exe（推荐）

前往 [Releases](https://github.com/SwingRainbow/BulletPriceMonitor/releases) 下载最新 exe，双击运行。

### 开发运行

```bash
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

## 📁 项目结构

```
BulletPriceMonitor/
├── run.py                  # 入口（支持 --worker 子进程模式）
├── version.py              # 版本号（打包和更新都读这里）
├── updater.py              # 自动更新模块
├── src/
│   ├── main.py             # 主函数
│   ├── app.py              # pywebview 窗口 & JS API 桥接
│   ├── monitor.py          # 监控引擎
│   ├── scraper.py          # 抓取调度（启动子进程）
│   ├── scraper_worker.py   # 抓取 worker（隐藏 webview）
│   ├── notifier.py         # 系统通知
│   ├── config.py           # 配置管理
│   └── frontend/
│       └── index.html      # UI 界面
├── .github/workflows/
│   └── build.yml           # GitHub Actions 自动打包发版
├── build.spec              # PyInstaller 单文件 exe 配置
├── commit.bat              # 一键提交 / 发版
└── README.md
```

## 🔧 开发流程

```bash
# 日常提交（本地打包 exe）
commit.bat "修复了xxx"

# 发版（推送 tag → GitHub Actions 自动打包发布 exe）
commit.bat "发版 v3.0.1" v3.0.1

# 或手动：
git tag v3.0.1
git push origin main --tags
```

## ⚙️ 技术栈

| 组件 | 技术 |
|------|------|
| UI 框架 | pywebview (HTML/CSS/JS) |
| 价格抓取 | 隐藏 webview 子进程 + DOM 提取 |
| 通知 | Windows 托盘气泡 + winsound |
| 打包 | PyInstaller 单文件 exe |
| CI/CD | GitHub Actions |
| 更新 | GitHub Releases 自动检测+替换 |

## 📄 License

MIT
