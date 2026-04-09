import os
import json
import pandas as pd
import requests
import google.generativeai as genai
from PIL import Image
import time
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted

# ==========================================
# 1. 初始化設定
# ==========================================
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def load_taiwan_drug_database(csv_path):
    print(f"📦 [系統啟動] 載入資料庫...")
    try:
        columns_needed = ['中文品名', '英文品名', '適應症', '主成分略述']
        df = pd.read_csv(csv_path, usecols=columns_needed, dtype=str)
        df = df.dropna(subset=['中文品名'])
        return df
    except Exception as e:
        print(f"❌ 載入失敗：{e}")
        return None

# ==========================================
# 2. 影像辨識 (附帶防護裝甲)
# ==========================================
def extract_drugs_from_image(image_path):
    print(f"👁️  [AI 視覺辨識] 正在閱讀藥單...")
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"❌ 無法開啟圖片：{e}")
        return []

    prompt = """
    這是一張藥單照片。請擷取所有藥品並整理成 JSON：
    {
        "drug_name_raw": "原始藥名",
        "search_keyword": "去劑量與雜質後的核心藥名(如 IBUPROFEN)",
        "quantity": "數量與頻率 (例如: 1顆/每日三次)"
    }
    只輸出純 JSON，不含標籤。
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    for attempt in range(3):
        try:
            response = model.generate_content(
                [prompt, img], 
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except ResourceExhausted:
            print(f"   ⚠️ [系統提示] 影像辨識撞到測速照相！自動冷卻 60 秒... (第 {attempt+1}/3 次重試)")
            time.sleep(60)
        except Exception as e:
            print(f"❌ 解析失敗：{e}")
            return []
    return []

# ==========================================
# 3. 資料庫比對
# ==========================================
def search_drug_in_db(df, search_name):
    search_term = str(search_name).strip().upper()
    match = df[df['中文品名'].str.contains(search_term, na=False, regex=False) | 
               df['英文品名'].str.contains(search_term, na=False, regex=False)]
    if not match.empty:
        first_match = match.iloc[0]
        raw_ingredient = str(first_match['主成分略述'])
        clean_ingredient = raw_ingredient.split(';;')[0].split('(')[0].strip()
        
        return {
            "官方中文名": first_match['中文品名'], 
            "純淨主成分": clean_ingredient,
            "適應症": str(first_match['適應症']).strip()
        }
    return None

# ==========================================
# 4. openFDA 狀態判定
# ==========================================
def query_openfda_interactions(ingredient):
    base_url = "https://api.fda.gov/drug/label.json"
    url = f"{base_url}?search=openfda.generic_name:\"{ingredient}\"&limit=1"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                interactions = results[0].get("drug_interactions", [])
                if interactions:
                    return "HAS_CONFLICT", str(interactions)
                else:
                    return "NO_CONFLICT", "無交互衝突"
        return "NO_DATA", "無資料"
    except Exception:
        return "NO_DATA", "無資料"

# ==========================================
# 5. Gemini 衝突精簡翻譯 (附帶防護裝甲)
# ==========================================
def summarize_conflict_with_gemini(fda_text):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    請將以下FDA藥物交互作用的英文文獻，翻譯並摘要成簡單的白話文警告。
    請嚴格依照此格式輸出：
    【衝突成分】：(列出主要會衝突的藥物成分或食物，用逗號隔開)
    【後果】：(用一句話解釋一起吃的後果)
    
    文獻：{fda_text}
    """
    
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except ResourceExhausted:
            print(f"      ⚠️ [系統提示] 翻譯時撞到測速照相！自動冷卻 20 秒... (第 {attempt+1}/3 次重試)")
            time.sleep(20)
        except Exception:
            return "翻譯失敗"
    return "翻譯失敗"

# ==========================================
# 主程式執行區：組裝最終報告
# ==========================================
if __name__ == "__main__":
    IMAGE_PATH = "test_images/sample_prescription3.JPG" # 記得確認你的圖片路徑
    CSV_PATH = "全部藥品許可證資料集.csv"
    
    db_df = load_taiwan_drug_database(CSV_PATH)

    if db_df is not None:
        drugs_list = extract_drugs_from_image(IMAGE_PATH)

        if drugs_list:
            print("\n" + "="*60)
            print(" 🏥 藥單最終解析報告 ")
            print("="*60)

            for i, drug in enumerate(drugs_list, 1):
                raw_name = drug.get('drug_name_raw', '未知藥名')
                search_kw = drug.get('search_keyword', '')
                quantity = drug.get('quantity', '未知數量')
                
                # 預設變數
                official_name = "查無官方名稱"
                pure_ingredient = "無資料"
                indication = "無資料"
                fda_result = "無資料"
                
                # 1. 查本地資料庫
                db_info = search_drug_in_db(db_df, search_kw)

                if db_info:
                    official_name = db_info['官方中文名']
                    pure_ingredient = db_info['純淨主成分']
                    
                    raw_indication = db_info['適應症']
                    indication = raw_indication if len(raw_indication) < 40 else raw_indication[:38] + "..."
                    
                    # 2. 查 openFDA
                    status, fda_raw_text = query_openfda_interactions(pure_ingredient)
                    
                    # 3. 根據狀態決定要不要請 Gemini 翻譯
                    if status == "HAS_CONFLICT":
                        fda_result = summarize_conflict_with_gemini(fda_raw_text)
                    elif status == "NO_CONFLICT":
                        fda_result = "無交互衝突"
                    else:
                        fda_result = "無資料"
                
                # 🌟 印出你要求的最乾淨排版 (新增「原藥單名」欄位)
                print(f"💊 藥品 {i}:")
                print(f"   ► 原藥單名 : {raw_name}")         # <--- 新增在這裡！
                print(f"   ► 官方藥名 : {official_name}")
                print(f"   ► 適應症   : {indication}")
                print(f"   ► 純成分   : {pure_ingredient}")
                print(f"   ► 數量     : {quantity}")
                print(f"   ► FDA資料  : \n     {fda_result.replace('【', '     【') if '【' in fda_result else fda_result}")
                print("-" * 60)
                
                if i < len(drugs_list) and fda_result not in ["無資料", "無交互衝突"]:
                    time.sleep(4)