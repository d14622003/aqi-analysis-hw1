import requests
import os
from dotenv import load_dotenv
import folium
import pandas as pd
from datetime import datetime
import json
import math
from geopy.distance import geodesic

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

class AQIMonitor:
    def __init__(self):
        self.api_key = os.getenv('MOENV_API_KEY')
        self.base_url = "https://data.epa.gov.tw/api/v1"
        self.aqi_data = None
        self.taipei_station = (25.0478, 121.5170)  # 台北車站坐標
        
    def fetch_aqi_data(self):
        """獲取全台即時 AQI 數據"""
        if not self.api_key:
            print("警告: 未找到 API Key，使用測試數據")
            self.aqi_data = self.get_test_data()
            return True
            
        url = f"{self.base_url}/aqx_p_432"
        params = {
            'api_key': self.api_key,
            'format': 'json'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'fields' in data and 'records' in data:
                self.aqi_data = data['records']
                print(f"成功獲取 {len(self.aqi_data)} 個測站數據")
                return True
            else:
                print("API 回應格式錯誤")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"API 請求失敗: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"JSON 解析失敗: {e}")
            return False
    
    def get_aqi_color(self, aqi_value):
        """根據 AQI 值返回對應顏色"""
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
    
    def calculate_distance_to_taipei(self, lat, lon):
        """計算測站到台北車站的距離（公里）"""
        try:
            station_coords = (float(lat), float(lon))
            distance = geodesic(station_coords, self.taipei_station).kilometers
            return round(distance, 2)
        except (ValueError, TypeError):
            return None
    
    def create_aqi_map(self):
        """創建 AQI 地圖"""
        if not self.aqi_data:
            print("沒有 AQI 數據，請先獲取數據")
            return None
            
        # 計算地圖中心點 (台灣中心)
        taiwan_center = [23.8, 120.9]
        
        # 創建地圖
        m = folium.Map(
            location=taiwan_center,
            zoom_start=7,
            tiles='OpenStreetMap'
        )
        
        # 添加 AQI 圖例
        legend_html = '''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 150px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>AQI 指標</h4>
        <p><i class="fa fa-circle" style="color:green"></i> 0-50 良好</p>
        <p><i class="fa fa-circle" style="color:yellow"></i> 51-100 普通</p>
        <p><i class="fa fa-circle" style="color:red"></i> 101+ 不健康</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # 添加測站標記
        for station in self.aqi_data:
            try:
                # 獲取坐標
                lat = float(station['Latitude']) if station['Latitude'] else None
                lon = float(station['Longitude']) if station['Longitude'] else None
                
                if lat and lon:
                    # 獲取 AQI 值和顏色
                    aqi_value = station.get('AQI', 'N/A')
                    color = self.get_aqi_color(aqi_value)
                    
                    # 創建彈出窗口內容
                    popup_content = f"""
                    <div style="font-size: 14px; min-width: 200px;">
                    <h4 style="margin: 5px 0; color: #333;">{station.get('SiteName', '未知測站')}</h4>
                    <p style="margin: 3px 0;"><b>所在地:</b> {station.get('County', '未知')} {station.get('SiteName', '')}</p>
                    <p style="margin: 3px 0;"><b>即時 AQI:</b> <span style="font-size: 16px; font-weight: bold; color: {color};">{aqi_value}</span></p>
                    <p style="margin: 3px 0;"><b>空氣品質:</b> {station.get('Status', '未知')}</p>
                    </div>
                    """
                    
                    # 添加標記
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=8,
                        popup=popup_content,
                        color='black',
                        weight=1,
                        fillColor=color,
                        fillOpacity=0.7
                    ).add_to(m)
                    
            except (ValueError, KeyError) as e:
                print(f"處理測站數據時發生錯誤: {e}")
                continue
        
        return m
    
    def save_data_to_csv(self, filename=None):
        """保存數據到 CSV 檔案，包含距離計算"""
        if not self.aqi_data:
            print("沒有數據可保存")
            return False
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"outputs/aqi_data_{timestamp}.csv"
            
        # 確保 outputs 目錄存在
        os.makedirs('outputs', exist_ok=True)
        
        try:
            # 創建包含距離的數據
            enhanced_data = []
            for station in self.aqi_data:
                station_copy = station.copy()
                
                # 計算到台北車站的距離
                lat = station.get('Latitude')
                lon = station.get('Longitude')
                if lat and lon:
                    distance = self.calculate_distance_to_taipei(lat, lon)
                    station_copy['Distance_to_Taipei_km'] = distance
                else:
                    station_copy['Distance_to_Taipei_km'] = None
                
                enhanced_data.append(station_copy)
            
            df = pd.DataFrame(enhanced_data)
            
            # 重新排列欄位順序，將重要欄位放在前面
            important_columns = ['SiteName', 'County', 'AQI', 'Status', 'Distance_to_Taipei_km', 'Latitude', 'Longitude']
            other_columns = [col for col in df.columns if col not in important_columns]
            column_order = important_columns + other_columns
            df = df[column_order]
            
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"數據已保存到: {filename}")
            print(f"包含 {len(df)} 個測站的距離計算結果")
            return True
        except Exception as e:
            print(f"保存 CSV 檔案時發生錯誤: {e}")
            return False
    
    def save_map(self, map_obj, filename=None):
        """保存地圖到 HTML 檔案"""
        if not map_obj:
            print("沒有地圖可保存")
            return False
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"outputs/aqi_map_{timestamp}.html"
            
        # 確保 outputs 目錄存在
        os.makedirs('outputs', exist_ok=True)
        
        try:
            map_obj.save(filename)
            print(f"地圖已保存到: {filename}")
            return True
        except Exception as e:
            print(f"保存地圖檔案時發生錯誤: {e}")
            return False

def main():
    """主程式"""
    print("=== 台灣 AQI 即時監測系統 ===")
    
    # 創建 AQI 監測器
    monitor = AQIMonitor()
    
    # 獲取數據
    print("正在獲取 AQI 數據...")
    if not monitor.fetch_aqi_data():
        print("獲取數據失敗，程式結束")
        return
    
    # 創建地圖
    print("正在創建地圖...")
    aqi_map = monitor.create_aqi_map()
    
    if aqi_map:
        # 保存地圖
        monitor.save_map(aqi_map)
        
        # 保存數據
        monitor.save_data_to_csv()
        
        print("地圖和數據已保存到 outputs 目錄")
        print("可以在瀏覽器中打開 HTML 檔案查看地圖")
    else:
        print("創建地圖失敗")

if __name__ == "__main__":
    main()
