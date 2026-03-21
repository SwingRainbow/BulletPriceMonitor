@echo off
chcp 65001 >nul
REM ========================================
REM  提交代码 + 自动打包 exe
REM  用法: commit.bat "提交信息"
REM  发版: commit.bat "提交信息" v3.0.1
REM ========================================

if "%~1"=="" (
    set /p MSG="输入提交信息: "
) else (
    set MSG=%~1
)

echo.
echo [1/3] Git 提交...
git add -A
git commit -m "%MSG%"

if not "%~2"=="" (
    echo.
    echo [TAG] 打标签 %~2 并推送...
    git tag %~2
    git push origin main --tags
    echo [TAG] 已推送，GitHub Actions 将自动打包发布 exe
    echo.
    pause
    exit /b 0
)

echo.
echo [2/3] 本地打包 exe...
pyinstaller build.spec --noconfirm --clean

echo.
echo ============================================
echo   完成! exe: dist\BulletPriceMonitor.exe
echo   提交信息: %MSG%
echo ============================================
pause
