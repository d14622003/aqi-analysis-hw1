import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path

def validate_and_clean_shelters():
    # 1. 路徑設定 (使用要求的相對路徑邏輯)
    current_file_path = Path(__file__).resolve()
    # 假設腳本在 scripts 子目錄，向上跳兩層到根目錄，再進入 data
    data_dir = current_file_path.parent.parent / "data"
    
    input_csv = data_dir / "避難收容處所點位檔案v9.csv"
    input_shp = data_dir / "台灣縣市界" / "TOWN_MOI_1140318.shp"
    output_path = data_dir / "shelters_cleaned.csv"
    
    if not input_csv.exists() or not input_shp.exists():
        print(f"❌ 錯誤：找不到必要的檔案。\nCSV: {input_csv}\nSHP: {input_shp}")
        return

    # 2. 讀取資料 (保留原始字串以檢查小數點精度)
    print("📖 正在讀取資料...")
    df = pd.read_csv(input_csv, dtype={'經度': str, '緯度': str})
    
    # 轉換為數值供計算使用
    df['lon_num'] = pd.to_numeric(df['經度'], errors='coerce')
    df['lat_num'] = pd.to_numeric(df['緯度'], errors='coerce')

    # 3. 定義縣市矩形邊界 (初步篩選用)
    county_bounds = {
        '臺北': (121.4, 121.7, 24.9, 25.3), '新北': (121.2, 122.1, 24.6, 25.4),
        '桃園': (120.9, 121.5, 24.5, 25.2), '臺中': (120.4, 121.5, 24.0, 24.5),
        '臺南': (120.0, 120.7, 22.8, 23.5), '高雄': (120.1, 121.1, 22.4, 23.5),
        '基隆': (121.6, 121.9, 25.0, 25.2), '新竹': (120.8, 121.4, 24.5, 25.0),
        '苗栗': (120.6, 121.2, 24.2, 24.8), '彰化': (120.3, 120.7, 23.8, 24.2),
        '南投': (120.6, 121.4, 23.4, 24.3), '雲林': (120.1, 120.8, 23.5, 23.9),
        '嘉義': (120.1, 120.9, 23.2, 23.6), '屏東': (120.3, 121.0, 21.8, 22.9),
        '宜蘭': (121.3, 122.0, 24.3, 25.0), '花蓮': (121.0, 121.8, 23.1, 24.4),
        '臺東': (120.7, 121.6, 22.0, 23.5), '澎湖': (119.4, 119.8, 23.1, 23.8),
        '金門': (118.2, 118.6, 24.3, 24.6), '連江': (119.8, 120.6, 25.9, 26.4),
    }

    def check_logical_quality(row):
        issues = []
        lon, lat = row['lon_num'], row['lat_num']
        lon_str, lat_str = str(row['經度']), str(row['緯度'])
        addr = str(row['縣市及鄉鎮市區'])
        
        # A. 基礎缺失與座標系判定
        if pd.isna(lon) or pd.isna(lat) or lon == 0 or lat == 0:
            return "異常", "座標缺失或為零", "未知"
        
        if lon > 180 or lat > 90:
            return "異常", "疑似二度分帶座標(EPSG:3826)", "EPSG:3826"
        
        crs = "EPSG:4326"

        # B. 精度檢查
        if '.' not in lon_str or len(lon_str.split('.')[1]) < 3:
            issues.append("解析度不足(小數點<3位)")
        if lon % 1 == 0 or lat % 1 == 0:
            issues.append("整數點位(疑似預設值)")

        # C. 行政區邏輯檢查
        for county, bounds in county_bounds.items():
            if county in addr:
                ln_min, ln_max, lt_min, lt_max = bounds
                if not (ln_min <= lon <= ln_max and lt_min <= lat <= lt_max):
                    issues.append(f"位置與行政區({county})範圍不符")
                break
        
        # D. 異常特徵
        if lon_str.split('.')[-1] == lat_str.split('.')[-1]:
            issues.append("經緯度小數點完全相同(疑似假資料)")
            
        return ("有效" if not issues else "異常"), ";".join(issues), crs

    # 4. 執行邏輯品質分析
    print("🚀 執行邏輯與精度檢查...")
    results = df.apply(check_logical_quality, axis=1, result_type='expand')
    df['座標有效性'] = results[0]
    df['座標問題'] = results[1]
    df['座標系統'] = results[2]

    # 5. 執行 SHP 精確空間驗證 (Point-in-Polygon)
    print(f"📂 載入 SHP 圖資並進行空間校驗：{input_shp.name}")
    taiwan_land = gpd.read_file(input_shp)
    if taiwan_land.crs != "EPSG:4326":
        taiwan_land = taiwan_land.to_crs("EPSG:4326")

    # 建立 GeoDataFrame (僅針對數值有效的點位)
    valid_mask = df['lon_num'].notna() & df['lat_num'].notna()
    geometry = [Point(xy) for xy in zip(df.loc[valid_mask, 'lon_num'], df.loc[valid_mask, 'lat_num'])]
    gdf_shelters = gpd.GeoDataFrame(df[valid_mask], geometry=geometry, crs="EPSG:4326")

    # 空間連結
    print("🛰️ 正在比對點位是否位於陸地行政區內...")
    res_spatial = gpd.sjoin(gdf_shelters, taiwan_land, how='left', predicate='within')
    
    # 將 SHP 驗證結果回填至原 DataFrame
    df.loc[valid_mask, '在陸地上'] = res_spatial['index_right'].notna()
    
    # 更新空間異常標記
    mask_offshore = (df['在陸地上'] == False) & (df['座標有效性'] == '有效')
    df.loc[mask_offshore, '座標有效性'] = '異常'
    df.loc[mask_offshore, '座標問題'] = '點位偏移至海面或國境之外'

    # 6. 處理其他欄位 (is_indoor)
    df['is_indoor'] = df['室內'].map({'是': True, '否': False}).fillna(False)

    # 7. 統計與輸出
    total = len(df)
    valid_count = (df['座標有效性'] == '有效').sum()
    print(f"\n=== 最終清理統計 ===")
    print(f"總筆數：{total}")
    print(f"✅ 最終合規 (含空間校驗)：{valid_count} ({valid_count/total:.1%})")
    print(f"🌊 偵測到海上/境外點位：{len(df[df['在陸地上'] == False])} 筆")
    
    # 顯示座標系統統計
    print("\n座標系統分佈：")
    print(df['座標系統'].value_counts())

    # 移除輔助欄位並儲存
    df_final = df.drop(columns=['lon_num', 'lat_num', '在陸地上'])
    df_final.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n💾 清理完成！產出檔案：{output_path}")

if __name__ == "__main__":
    validate_and_clean_shelters()