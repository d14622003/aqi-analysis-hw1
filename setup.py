#!/usr/bin/env python3
"""
環境設定腳本
自動安裝依賴套件並設定環境
"""

import subprocess
import sys
import os

def check_python_version():
    """檢查 Python 版本"""
    if sys.version_info < (3, 7):
        print("錯誤: 需要 Python 3.7 或更高版本")
        print(f"當前版本: {sys.version}")
        return False
    print(f"Python 版本檢查通過: {sys.version}")
    return True

def install_requirements():
    """安裝 requirements.txt 中的套件"""
    print("正在安裝依賴套件...")
    
    try:
        # 升级 pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # 安裝套件
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        print("依賴套件安裝完成")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"安裝套件時發生錯誤: {e}")
        return False

def check_env_file():
    """檢查 .env 檔案"""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print(f"警告: {env_file} 檔案不存在")
        return False
    
    # 檢查是否有 API Key
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "EPA_API_KEY=" not in content or "your_api_key_here" in content:
        print("警告: 請在 .env 檔案中設定您的 EPA_API_KEY")
        print("您可以從環境部空氣品質監測網取得 API Key")
        print("網址: https://airmap.epa.gov.tw/")
        return False
    
    print(".env 檔案檢查通過")
    return True

def create_directories():
    """創建必要的目錄"""
    directories = ["data", "outputs"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"創建目錄: {directory}")
        else:
            print(f"目錄已存在: {directory}")

def main():
    """主程式"""
    print("=== AQI 監測系統環境設定 ===\n")
    
    # 檢查 Python 版本
    if not check_python_version():
        sys.exit(1)
    
    # 創建目錄
    create_directories()
    
    # 安裝依賴套件
    if not install_requirements():
        print("依賴套件安裝失敗，請手動安裝")
        sys.exit(1)
    
    # 檢查 .env 檔案
    if not check_env_file():
        print("\n請設定 .env 檔案後重新執行")
        sys.exit(1)
    
    print("\n=== 環境設定完成 ===")
    print("現在可以執行: python aqi_monitor.py")

if __name__ == "__main__":
    main()
