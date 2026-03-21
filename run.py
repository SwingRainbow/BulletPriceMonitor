"""
入口文件
支持 --worker 模式（打包后子进程调用）
支持 --econ-worker 模式（经济学数据抓取子进程）
"""
import sys

if __name__ == "__main__":
    if '--worker' in sys.argv:
        # 子进程模式：执行抓取 worker
        from src.scraper_worker import run_worker
        run_worker()
    elif '--econ-worker' in sys.argv:
        # 子进程模式：执行经济学数据抓取
        from src.econ_worker import run_econ_worker
        run_econ_worker()
    else:
        # 正常模式：启动 UI
        from src.main import main
        main()