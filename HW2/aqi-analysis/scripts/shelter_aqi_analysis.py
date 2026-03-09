import os
import requests
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import math
from pathlib import Path
from datetime import datetime

# 1. 建立相對路徑邏輯
load_dotenv()
current_file_path = Path(__file__).resolve()
# 向上跳兩層回到專案根目錄，然後進入 data 目錄
PROJECT_ROOT = current_file_path.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_aqi_data():
    """獲取環境部即時 AQI 數據"""
    api_key = os.getenv('MOENV_API_KEY')
    if not api_key:
        print("⚠️ 警告：找不到 API Key，請在 .env 中設定 MOENV_API_KEY")
        return None
    
    url = f"https://data.moenv.gov.tw/api/v2/aqx_p_432?format=json&api_key={api_key}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        records = data if isinstance(data, list) else data.get('records', [])
            
        processed = []
        for r in records:
            try:
                # 確保數值型態正確
                r['aqi'] = int(r['aqi']) if r.get('aqi') and r['aqi'] != '' else 0
                r['latitude'] = float(r['latitude'])
                r['longitude'] = float(r['longitude'])
                processed.append(r)
            except (ValueError, TypeError):
                continue
        
        print(f"✅ 成功獲取 {len(processed)} 筆測站數據")
        return processed
    except Exception as e:
        print(f"❌ API 請求失敗：{e}")
        return None

def apply_scenario_injection(records):
    """【修正】Task 3: 情境注入：將第 5 個測站 AQI 強制設為 150"""
    if len(records) >= 5:
        # Python 索引從 0 開始，第 5 個測站索引為 4
        target_station = records[4]['sitename']
        print(f"💡 執行情境注入：手動將第 5 個測站「{target_station}」的 AQI 設為 150 以測試風險邏輯。")
        records[4]['aqi'] = 150
    else:
        print("⚠️ 測站數量不足 5 筆，無法執行第 5 站注入。")
    return records

def calculate_haversine(lat1, lon1, lat2, lon2):
    """Haversine 公式計算球面距離 (km)"""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371

def run_nearest_neighbor_analysis(shelters_df, aqi_records):
    """Task 3: 最近鄰分析與風險標籤"""
    print("🚀 正在執行空間分析 (對應最近測站)...")
    aqi_df = pd.DataFrame(aqi_records)
    analysis_results = []

    for _, shelter in shelters_df.iterrows():
        s_lat, s_lon = shelter['緯度'], shelter['經度']
        
        # 計算到所有測站的距離
        distances = aqi_df.apply(
            lambda r: calculate_haversine(s_lat, s_lon, r['latitude'], r['longitude']), axis=1
        )
        
        idx = distances.idxmin()
        nearest = aqi_df.iloc[idx]
        
        aqi_val = nearest['aqi']
        # 修正：讀取原始 CSV 中的「室內」欄位
        is_indoor = shelter.get('室內', '否') == '是'
        
        # 風險邏輯判定
        risk = "Normal"
        if aqi_val > 100:
            risk = "High Risk"
        elif aqi_val > 50 and not is_indoor:
            risk = "Warning"
            
        analysis_results.append({
            '最近測站': nearest['sitename'],
            '最近測站AQI': aqi_val,
            '距離測站_km': round(distances.min(), 2),
            '風險分級': risk
        })
    
    return pd.concat([shelters_df.reset_index(drop=True), pd.DataFrame(analysis_results)], axis=1)

def generate_risk_map(final_df, aqi_records):
    """產出互動式整合地圖"""
    print("🗺️ 正在生成互動式地圖...")
    
    m = folium.Map(location=[23.8, 120.9], zoom_start=8)
    
    # 1. AQI 測站圖層
    aqi_layer = folium.FeatureGroup(name="🏭 即時 AQI 測站")
    for r in aqi_records:
        color = 'green' if r['aqi'] <= 50 else ('orange' if r['aqi'] <= 100 else 'red')
        folium.CircleMarker(
            location=[r['latitude'], r['longitude']],
            radius=10,
            popup=f"測站: {r['sitename']}<br>AQI: {r['aqi']}<br>座標: {r['latitude']:.4f}, {r['longitude']:.4f}",
            color='black', weight=1, fillColor=color, fillOpacity=0.7
        ).add_to(aqi_layer)
    aqi_layer.add_to(m)

    # 2. 避難所圖層 - 分為室內與室外
    indoor_cluster = MarkerCluster(name="🏠 室內避難收容處所")
    outdoor_cluster = MarkerCluster(name="� 室外避難收容處所")
    
    for _, row in final_df.iterrows():
        # 判斷室內外
        is_indoor = row.get('室內', '否') == '是'
        
        # 根據風險分級決定顏色
        icon_color = 'blue'  # Normal
        if row['風險分級'] == 'High Risk': icon_color = 'red'
        elif row['風險分級'] == 'Warning': icon_color = 'orange'
        
        # 根據室內外決定圖標
        icon_type = 'home' if is_indoor else 'glyphicon glyphicon-tower'
        
        # 建立標記點
        marker = folium.Marker(
            location=[row['緯度'], row['經度']],
            popup=folium.Popup(f"處所: {row['避難收容處所名稱']}<br>類型: {'室內' if is_indoor else '室外'}<br>風險: {row['風險分級']}<br>最近測站: {row['最近測站']}(AQI:{row['最近測站AQI']})<br>座標: {row['緯度']:.4f}, {row['經度']:.4f}", max_width=250),
            icon=folium.Icon(color=icon_color, icon=icon_type)
        )
        
        # 加入對應的群組
        if is_indoor:
            marker.add_to(indoor_cluster)
        else:
            marker.add_to(outdoor_cluster)
    
    indoor_cluster.add_to(m)
    outdoor_cluster.add_to(m)

    # 3. 圖例 Legend
    legend_html = '''
     <div style="position: fixed; bottom: 50px; left: 50px; width: 320px; height: 260px; 
     background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
     padding: 8px; border-radius: 8px; opacity: 0.9; overflow: auto;">
     <b>📊 圖例說明</b><br>
     <hr style="margin: 3px 0;">
     <b>🏭 AQI 測站</b><br>
     <i class="fa fa-circle" style="color:green"></i> AQI ≤ 50 (良好)<br>
     <i class="fa fa-circle" style="color:orange"></i> AQI 51-100 (普通)<br>
     <i class="fa fa-circle" style="color:red"></i> AQI > 100 (不健康)<br>
     <hr style="margin: 3px 0;">
     <b>🏠 室內避難所</b><br>
     <i class="fa fa-home" style="color:red"></i> 高風險 (AQI>100)<br>
     <i class="fa fa-home" style="color:orange"></i> 警告 (AQI>50)<br>
     <i class="fa fa-home" style="color:blue"></i> 正常<br>
     <b>🏢 室外避難所</b><br>
     <i class="glyphicon glyphicon-tower" style="color:red"></i> 高風險 (AQI>100)<br>
     <i class="glyphicon glyphicon-tower" style="color:orange"></i> 警告 (AQI>50)<br>
     <i class="glyphicon glyphicon-tower" style="color:blue"></i> 正常
     </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl().add_to(m)
    map_path = OUTPUT_DIR / "integrated_risk_map.html"
    m.save(map_path)
    return map_path

def main():
    input_csv = DATA_DIR / "shelters_cleaned.csv"
    if not input_csv.exists():
        print(f"❌ 錯誤：找不到輸入檔案 {input_csv}")
        return

    # 獲取資料
    aqi_records = get_aqi_data()
    if not aqi_records: return
    
    # 【注入】
    aqi_records = apply_scenario_injection(aqi_records)
    
    # 讀取避難所資料
    df = pd.read_csv(input_csv)
    
    # 確保有座標有效性欄位 (若無則手動過濾 0 座標)
    if '座標有效性' in df.columns:
        valid_df = df[df['座標有效性'] == '有效'].copy()
    else:
        valid_df = df[df['經度'] > 0].copy()
    
    # 執行分析
    final_df = run_nearest_neighbor_analysis(valid_df, aqi_records)
    
    # 輸出 CSV
    csv_output = OUTPUT_DIR / "shelter_aqi_analysis.csv"
    final_df.to_csv(csv_output, index=False, encoding='utf-8-sig')
    print(f"✅ 分析報表已儲存：{csv_output}")
    
    # 輸出互動地圖
    map_output = generate_risk_map(final_df, aqi_records)
    print(f"✅ 互動地圖已生成：{map_output}")

if __name__ == "__main__":
    main()
    