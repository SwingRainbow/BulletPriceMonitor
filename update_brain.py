"""
大脑数据更新脚本（命令行入口）
直接运行: python update_brain.py

打包后此文件不需要，exe 通过 app.py -> brain_updater 内部调用
"""
import sys
import os

# 确保能 import src 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.brain_updater import run_update

if __name__ == '__main__':
    print("[Brain] 正在抓取 orzice 数据...")
    result = run_update()
    if result['status'] == 'ok':
        print(f"[Brain] ✅ {result['message']}")
    elif result['status'] == 'dup':
        print(f"[Brain] ℹ️ {result['message']}")
    else:
        print(f"[Brain] ❌ {result['message']}")