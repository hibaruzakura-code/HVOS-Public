@echo off
chcp 65001
echo ==========================================
echo  HVOSに必要な部品を自動でインストールします
echo ==========================================
pip install flask pyautogui keyboard pygetwindow pillow google-genai
echo.
echo 準備が完了しました！この画面は閉じて大丈夫です。
pause
