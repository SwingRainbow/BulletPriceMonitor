"""
入口文件
支持 --worker 模式（打包后子进程调用）
"""
import sys

if __name__ == "__main__":
    if '--worker' in sys.argv:
        # 子进程模式：执行抓取 worker
        from src.scraper_worker import run_worker
        run_worker()
    else:
        # 正常模式：启动 UI
        from src.main import main
        main()
