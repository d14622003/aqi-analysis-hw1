import os
import requests
import folium
import pandas as pd
from dotenv import load_dotenv
import json
from datetime import datetime
import math

# Load environment variables
load_dotenv()

def get_aqi_data():
    """獲取環境部 AQI 數據"""
    api_key = os.getenv('MOENV_API_KEY')
    if not api_key:
        print("錯誤：請在 .env 檔案中設定 MOENV_API_KEY")
        return None
    
    url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?format=json&api_key=" + api_key
    
    try:
        print("正在獲取 AQI 數據...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        # Handle both list and dict response formats
        if isinstance(data, list):
            records = data
            print(f"成功獲取 {len(records)} 筆測站數據")
            return {'records': records}
        else:
            records = data.get('records', [])
            print(f"成功獲取 {len(records)} 筆測站數據")
            return data
        
    except requests.exceptions.RequestException as e:
        print(f"API 請求錯誤：{e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON 解析錯誤：{e}")
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """計算兩點之間的距離（公里）"""
    # 將角度轉換為弧度
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine 公式
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # 地球半徑（公里）
    r = 6371
    return c * r

def get_aqi_color(aqi_value):
    """根據 AQI 數值返回對應顏色"""
    try:
        aqi = int(aqi_value)
    except (ValueError, TypeError):
        return 'gray'
    
    if aqi <= 50:
        return 'green'
    elif aqi <= 100:
        return 'yellow'
    else:
        return 'red'

def get_aqi_level(aqi_value):
    """根據 AQI 數值返回空氣品質等級"""
    try:
        aqi = int(aqi_value)
    except (ValueError, TypeError):
        return '未知'
    
    if aqi <= 50:
        return '良好'
    elif aqi <= 100:
        return '普通'
    else:
        return '不健康'

def create_aqi_map(data):
    """建立 AQI 地圖"""
    if not data or 'records' not in data:
        print("錯誤：無效的數據格式")
        return None
    
    records = data['records']
    if not records:
        print("錯誤：沒有測站數據")
        return None
    
    # 計算台灣中心點
    valid_stations = [r for r in records if r.get('latitude') and r.get('longitude')]
    if not valid_stations:
        print("錯誤：沒有有效的座標數據")
        return None
    
    lats = [float(r['latitude']) for r in valid_stations]
    lons = [float(r['longitude']) for r in valid_stations]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    # 建立地圖
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # 添加測站標記
    for record in valid_stations:
        try:
            lat = float(record['latitude'])
            lon = float(record['longitude'])
            aqi = record.get('aqi', 'N/A')
            site = record.get('sitename', '未知測站')
            county = record.get('county', '未知縣市')
            pollutant = record.get('mainpollutant', 'N/A')
            
            color = get_aqi_color(aqi)
            level = get_aqi_level(aqi)
            
            # 建立彈出視窗內容
            popup_content = f"""
            <div style="font-size: 14px;">
                <b>{site}</b><br>
                <b>所在地：</b>{county}<br>
                <b>即時 AQI：</b><span style="color: {color}; font-weight: bold;">{aqi}</span>
            </div>
            """
            
            # 建立圓形標記
            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                popup=folium.Popup(popup_content, max_width=200),
                color='black',
                weight=1,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(m)
            
        except (ValueError, KeyError) as e:
            print(f"跳過無效數據：{record.get('sitename', '未知')} - {e}")
            continue
    
    # 添加圖例
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 120px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h4>AQI 等級</h4>
    <i class="fa fa-circle" style="color:green"></i> 0-50 良好<br>
    <i class="fa fa-circle" style="color:yellow"></i> 51-100 普通<br>
    <i class="fa fa-circle" style="color:red"></i> 101+ 不健康
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def save_data_to_csv(data, filename=None):
    """保存數據到 CSV 檔案"""
    if not data or 'records' not in data:
        return
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outputs/aqi_data_{timestamp}.csv"
    
    # 確保 outputs 目錄存在
    os.makedirs('outputs', exist_ok=True)
    
    # 轉換為 DataFrame 並計算距離
    records = data['records']
    processed_records = []
    
    # 台北車站座標
    taipei_lat, taipei_lon = 25.0478, 121.5170
    
    for record in records:
        try:
            lat = float(record.get('latitude', 0))
            lon = float(record.get('longitude', 0))
            
            # 計算到台北車站的距離
            if lat and lon:
                distance = calculate_distance(lat, lon, taipei_lat, taipei_lon)
            else:
                distance = 0
            
            # 添加距離到記錄中
            record_copy = record.copy()
            record_copy['distance_to_taipei'] = round(distance, 2)
            processed_records.append(record_copy)
            
        except (ValueError, TypeError):
            # 如果座標無效，添加原始記錄並設距離為 0
            record_copy = record.copy()
            record_copy['distance_to_taipei'] = 0
            processed_records.append(record_copy)
    
    df = pd.DataFrame(processed_records)
    
    # 重新排列欄位順序
    columns = ['sitename', 'county', 'aqi', 'distance_to_taipei', 'latitude', 'longitude', 'mainpollutant']
    existing_columns = [col for col in columns if col in df.columns]
    other_columns = [col for col in df.columns if col not in existing_columns]
    final_columns = existing_columns + other_columns
    df = df[final_columns]
    
    # 保存到 CSV
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"數據已保存到：{filename}")
    
    return filename

def main():
    """主程式"""
    print("=" * 50)
    print("台灣即時 AQI 數據地圖生成器")
    print("=" * 50)
    
    # 獲取 AQI 數據
    aqi_data = get_aqi_data()
    if aqi_data is None:
        return
    
    # 建立地圖
    print("正在建立地圖...")
    aqi_map = create_aqi_map(aqi_data)
    if aqi_map is None:
        return
    
    # 保存地圖
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    map_filename = f"outputs/aqi_map_{timestamp}.html"
    os.makedirs('outputs', exist_ok=True)
    aqi_map.save(map_filename)
    print(f"地圖已保存到：{map_filename}")
    
    # 保存數據
    save_data_to_csv(aqi_data)
    
    # 統計信息
    records = aqi_data.get('records', [])
    print(f"\n統計信息：")
    print(f"總測站數：{len(records)}")
    
    # AQI 分佈統計
    aqi_levels = {}
    for record in records:
        aqi = record.get('aqi')
        if aqi and aqi != 'N/A':
            try:
                aqi_int = int(aqi)
                level = get_aqi_level(aqi_int)
                aqi_levels[level] = aqi_levels.get(level, 0) + 1
            except ValueError:
                continue
    
    print("AQI 等級分佈：")
    for level, count in aqi_levels.items():
        print(f"  {level}：{count} 個測站")
    
    print(f"\n程式執行完成！請開啟 {map_filename} 查看地圖。")

if __name__ == "__main__":
    main()
