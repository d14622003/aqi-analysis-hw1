@echo off
echo 正在安裝 Python 環境依賴套件...
echo.

REM 檢查 Python 是否已安裝
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 錯誤：未找到 Python，請先安裝 Python
    pause
    exit /b 1
)

echo Python 已安裝，正在安裝依賴套件...
echo.

REM 安裝依賴套件
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo 安裝失敗，請檢查網路連線或嘗試手動安裝：
    echo pip install requests python-dotenv folium pandas
    pause
    exit /b 1
)

echo.
echo 環境安裝完成！
echo.
echo 請確保 .env 檔案中已設定 MOENV_API_KEY
echo 然後執行：python aqi_mapper.py
echo.
pause
