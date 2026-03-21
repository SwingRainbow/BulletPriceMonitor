"""
通知模块
Windows 系统托盘气泡 + 蜂鸣声
"""
import subprocess
import sys


def _balloon(title: str, msg: str):
    """发送 Windows 托盘气泡通知"""
    try:
        st = title.replace("'", "''")
        sm = msg.replace("'", "''")
        ps = f"""
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.BalloonTipTitle = '{st}'
$n.BalloonTipText = '{sm}'
$n.BalloonTipIcon = 'Warning'
$n.ShowBalloonTip(5000)
Start-Sleep -Milliseconds 5500
$n.Dispose()
"""
        kw = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
        if sys.platform == 'win32':
            kw['creationflags'] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps],
            **kw
        )
    except Exception:
        pass


def send_toast(title: str, msg: str):
    """发送轻量通知（仅气泡）"""
    _balloon(title, msg)


def send_alert(title: str, msg: str):
    """发送警报通知（气泡 + 蜂鸣声）"""
    _balloon(title, msg)
    try:
        import winsound
        winsound.Beep(1000, 200)
        winsound.Beep(1200, 200)
        winsound.Beep(1000, 200)
    except Exception:
        pass
