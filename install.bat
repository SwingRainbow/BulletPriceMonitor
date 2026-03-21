@echo off
REM ========================================
REM  安装依赖（避免 pythonnet 编译问题）
REM ========================================

echo.
echo Installing dependencies...
echo.

REM 先单独装 pywebview (不拉 pythonnet)
pip install pywebview --no-deps
pip install Pillow bottle proxy_tools typing_extensions

echo.
echo ============================================
echo   Done! Run: python run.py
echo ============================================
pause
