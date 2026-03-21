# -*- coding: utf-8 -*-
"""
自动更新模块
启动时检查 GitHub Releases，如果有新版本就下载替换当前 exe
"""
import json
import os
import sys
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from version import __version__

# ★ 改成你自己的 GitHub 用户名和仓库名 ★
GITHUB_OWNER = 'SwingRainbow'
GITHUB_REPO  = 'BulletPriceMonitor'

RELEASES_API = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest'
CHECK_TIMEOUT = 8


def _is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def _current_exe() -> Path:
    return Path(sys.executable)


def _parse_version(tag: str) -> tuple[int, ...]:
    return tuple(int(x) for x in tag.lstrip('v').split('.'))


def _fetch_latest() -> dict | None:
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={
                'User-Agent': 'BulletPriceMonitor-Updater',
                'Accept': 'application/vnd.github+json',
            },
        )
        with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _find_exe_asset(release: dict) -> str | None:
    for asset in release.get('assets', []):
        if asset['name'].lower().endswith('.exe'):
            return asset['browser_download_url']
    return None


def _download_and_replace(url: str):
    current = _current_exe()
    tmp_dir = tempfile.mkdtemp(prefix='bp_update_')
    new_exe = os.path.join(tmp_dir, current.name)

    urllib.request.urlretrieve(url, new_exe)

    bat_path = os.path.join(tmp_dir, '_update.bat')
    bat_content = f'''@echo off
timeout /t 2 /nobreak >nul
copy /y "{new_exe}" "{current}" >nul
rmdir /s /q "{tmp_dir}" >nul 2>&1
start "" "{current}"
'''
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)

    subprocess.Popen(
        ['cmd', '/c', bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    sys.exit(0)


def check_update() -> str:
    if not _is_frozen():
        return json.dumps({'status': 'dev', 'message': '开发模式'})

    release = _fetch_latest()
    if not release:
        return json.dumps({'status': 'offline', 'message': '无法连接'})

    tag = release.get('tag_name', '')
    try:
        remote_ver = _parse_version(tag)
        local_ver  = _parse_version(__version__)
    except (ValueError, AttributeError):
        return json.dumps({'status': 'error', 'message': f'版本号异常: {tag}'})

    if remote_ver <= local_ver:
        return json.dumps({'status': 'latest', 'message': f'v{__version__} 已是最新'})

    exe_url = _find_exe_asset(release)
    if not exe_url:
        return json.dumps({'status': 'no_asset', 'message': f'{tag} 无下载'})

    try:
        _download_and_replace(exe_url)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'下载失败: {e}'})

    return json.dumps({'status': 'updating', 'message': '正在更新...'})
