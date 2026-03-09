# AQI 即時監測系統

台灣空氣品質指數 (AQI) 即時監測與空間分析系統。

## 功能特色

- 🌍 **即時數據獲取**: 串接環境部 API 獲取全台 AQI 測站數據
- 📍 **空間計算**: 計算各測站到台北車站的距離
- 🗺️ **地圖視覺化**: 使用 Folium 製作互動式 AQI 地圖
- 📊 **數據輸出**: 自動生成包含距離計算的 CSV 報表
- 🎨 **分色顯示**: 綠色(0-50)、黃色(51-100)、紅色(101+)

## 安裝與設定

### 1. 環境設定
```bash
python setup.py
```

### 2. 手動安裝依賴
```bash
pip install -r requirements.txt
```

### 3. 設定 API Key
在 `.env` 檔案中設定環境部 API Key：
```
EPA_API_KEY=your_api_key_here
```

## 使用方法

### 執行程式
```bash
python aqi_monitor.py
```

### 輸出檔案
- **地圖檔案**: `outputs/aqi_map_YYYYMMDD_HHMMSS.html`
- **數據檔案**: `outputs/aqi_data_YYYYMMDD_HHMMSS.csv`

## 檔案結構

```
.
├── aqi_monitor.py      # 主程式
├── requirements.txt    # Python 依賴套件
├── setup.py           # 環境設定腳本
├── .env               # 環境變數配置
├── .gitignore         # Git 忽略檔案
├── data/              # 資料目錄
└── outputs/           # 輸出目錄
```

## 主要功能

### AQI 數據獲取
- 串接環境部 `aqx_p_432` API
- 自動處理 API 回應格式
- 錯誤處理與重試機制

### 空間分析
- 計算各測站到台北車站 (25.0478, 121.5170) 的距離
- 使用 Geopy 套件進行精確距離計算
- 距離單位：公里

### 地圖視覺化
- 互動式 Folium 地圖
- 點擊測站顯示詳細資訊
- 彈出窗口包含：站名、所在地、即時 AQI、空氣品質狀態
- 右上角圖例說明

### 數據輸出
- CSV 格式輸出，支援中文編碼
- 包含距離計算結果
- 自動時間戳記檔名

## API 資料來源

- **來源**: 環境部空氣品質監測網
- **API**: `aqx_p_432` 即時測站數據
- **更新頻率**: 每小時更新

## 技術套件

- `requests`: HTTP 請求處理
- `python-dotenv`: 環境變數管理
- `folium`: 互動式地圖
- `pandas`: 數據處理
- `geopy`: 地理距離計算

## 開發資訊

- Python 3.7+
- Windows/Linux/macOS 支援
- 開源授權：MIT License
