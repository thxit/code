@echo off
cd /d "%~dp0"
title 一键上传代码到 GitHub
echo ================================================
echo    一键上传：把本项目的改动推送到 GitHub
echo ================================================
echo.
echo [1/3] 收集所有改动的文件...
git add -A
echo.
echo [2/3] 保存到本地版本库（自动生成备注）...
git commit -m "auto update %date% %time:~0,8%"
echo.
echo [3/3] 上传到 GitHub ...
git pull --rebase origin main
git push origin main
echo.
if %errorlevel% equ 0 (
    echo ================================================
    echo    [成功] 上传完成！可以关闭本窗口了
    echo ================================================
) else (
    echo ================================================
    echo    [失败] 上传出错。请按住鼠标左键选中本窗口
    echo    的报错文字，右键复制，发给 AI 助手处理
    echo ================================================
)
echo.
pause
