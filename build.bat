@echo off
REM ========================================
REM  子弹价格闪电监视 - 打包脚本
REM  用法: 双击运行 或 命令行执行 build.bat
REM ========================================

echo.
echo ============================================
echo   Building BulletPriceMonitor ...
echo ============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.9+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] Installing dependencies...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

REM 打包
echo [2/3] Building exe...
pyinstaller build.spec --noconfirm --clean

REM 复制配置目录
echo [3/3] Preparing output...
if not exist "dist\BulletPriceMonitor\config" mkdir "dist\BulletPriceMonitor\config"

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\BulletPriceMonitor\
echo ============================================
echo.
pause
