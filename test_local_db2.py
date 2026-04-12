import os
import json
import re
import pandas as pd
import requests
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# ==========================================
# 1. 初始化設定 & 載入資料庫
# ==========================================
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def load_databases(permit_csv, nhi_csv, appearance_csv):
    print(f"📦 [系統啟動] 載入三重交叉資料庫...")
    try:
        df_permit = pd.read_csv(permit_csv, usecols=['許可證字號', '中文品名', '英文品名', '適應症', '主成分略述'], dtype=str)
        df_nhi = pd.read_csv(nhi_csv, usecols=['藥品代號', '藥品英文名稱', '藥品中文名稱', '成分'], dtype=str)
        df_appearance = pd.read_csv(appearance_csv, usecols=['許可證字號', '外觀圖檔連結'], dtype=str)
        return df_permit, df_nhi, df_appearance
    except Exception as e:
        print(f"❌ 資料庫載入失敗：{e}")
        return None, None, None

# ==========================================
# 2. 影像辨識
# ==========================================
def extract_drugs_from_image(image_path):
    print(f"👁️  [AI 視覺辨識] 正在閱讀藥單：{image_path}...")
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # 🌟 這裡換成新的 Prompt，強制 AI 拆分數量資訊
    prompt = """這是一張藥單照片。請擷取所有藥品整理成 JSON。格式：
    {
        "nhi_code": "健保代碼", 
        "drug_name_raw": "原始藥名", 
        "search_keyword": "核心藥名", 
        "frequency": "服藥頻率(例如: 每日一次、三餐飯後、每六小時一次等)",
        "days": "給藥天數(例如: 3天、7天)",
        "total_amount": "給藥總數量(例如: 21顆、1瓶)"
    }"""
    
    try:
        response = model.generate_content([prompt, Image.open(image_path)], 
                                          generation_config=genai.GenerationConfig(response_mime_type="application/json"))
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ 解析失敗：{e}")
        return []

# ==========================================
# 3. 三表關聯搜尋邏輯 (含成分清洗)
# ==========================================
def search_drug_full_info(df_permit, df_nhi, df_appearance, search_kw, nhi_code):
    target_permit_no = None
    ch_name = "查無官方名稱"
    en_name = ""
    pure_ingredient = "無資料"
    indication = "無資料"
    img_link = "無外觀圖檔"
    match_type = "比對失敗"
    
    # --- 步驟 A：健保碼精準定位 ---
    if nhi_code and pd.notna(nhi_code) and str(nhi_code).strip() != "":
        match_nhi = df_nhi[df_nhi['藥品代號'] == str(nhi_code).strip().upper()]
        if not match_nhi.empty:
            ch_name = str(match_nhi.iloc[0]['藥品中文名稱']).strip()
            en_name = str(match_nhi.iloc[0]['藥品英文名稱']).strip()
            
            # 先用正則把健保檔的 5mg 等雜質切掉當備案
            raw_nhi_ing = str(match_nhi.iloc[0]['成分']).strip()
            pure_ingredient = re.sub(r'[0-9\.]+\s*(mg|ml|g|mcg|iu|u|%).*', '', raw_nhi_ing, flags=re.IGNORECASE).strip()
            match_type = "健保碼精準命中"

    # --- 步驟 B：許可證檔抓細節 ---
    query_name = en_name if en_name else search_kw
    if query_name:
        match_permit = df_permit[df_permit['英文品名'].str.contains(query_name, na=False, case=False, regex=False) | 
                                 df_permit['中文品名'].str.contains(ch_name, na=False, case=False, regex=False)]
        
        if not match_permit.empty:
            permit_info = match_permit.iloc[0]
            target_permit_no = permit_info['許可證字號']
            indication = str(permit_info['適應症']).strip()
            
            # 使用許可證的乾淨成分
            raw_ing = str(permit_info['主成分略述'])
            pure_ingredient = raw_ing.split(';;')[0].split('(')[0].strip()
            ch_name = permit_info['中文品名'] 
            if match_type == "比對失敗":
                match_type = "藥名模糊搜尋"
            
            # --- 步驟 C：外觀檔抓圖片 ---
            if target_permit_no:
                match_img = df_appearance[df_appearance['許可證字號'] == target_permit_no]
                if not match_img.empty:
                    img_link = str(match_img.iloc[0]['外觀圖檔連結']).strip()

    return {
        "官方中文名": ch_name, 
        "純淨主成分": pure_ingredient,
        "適應症": indication,
        "外觀連結": img_link,
        "比對方式": match_type
    }

# ==========================================
# 4. FDA 查詢與翻譯
# ==========================================
def query_openfda_interactions(ingredient):
    url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:\"{ingredient}\"&limit=1"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                interactions = results[0].get("drug_interactions", [])
                return "HAS_CONFLICT", str(interactions) if interactions else "無交互衝突"
        return "NO_DATA", "無資料"
    except Exception:
        return "NO_DATA", "無資料"

def batch_translate_fda_warnings(drugs_to_translate):
    if not drugs_to_translate:
        return {} 
        
    print(f"🧠 [AI 批次翻譯] 發現 {len(drugs_to_translate)} 筆 FDA 英文資料，發送一次性請求 (消耗 1 次額度)...")
    payload = json.dumps(drugs_to_translate, ensure_ascii=False)
    
    prompt = f"""
        你是一位具備豐富臨床經驗的專業藥師。我會給你一個 JSON，裡面包含多個藥品的 FDA 英文仿單節錄（可能包含交互作用、警語 Warnings、或用藥前須知 Ask a doctor）。

        請幫我從這些資料中，精準「揪出」與其他藥物併用的衝突、以及重大疾病禁忌，並翻譯摘要成一般台灣長輩也能看懂的白話文。

        【關鍵判斷指示】：
        請注意！有些成藥（OTC）不會有獨立的交互作用欄位，併用危險會藏在「Warnings」或「Ask a doctor before use」裡面（例如：正在服用阿斯匹靈、抗凝血劑等）。請務必仔細抓出這些隱藏的併用衝突！

        【嚴格排版規定】：
        1. 不要拆分成分與後果，必須將「衝突的成分或特定疾病」與「發生的後果」寫在同一行。
        2. 請挑選出 3~4 點「最嚴重或最常見」的交互作用或禁忌就好，不要囉嗦，刪除不重要的細節。
        3. 每一點的說明請控制在一句話以內。
        4. 開頭請統一使用「⚠️ 與【xxx】併用」或「⚠️ 【xxx】患者」。

        請回傳一個 JSON 陣列，格式如下：
        [
            {{
                "drug_name": "你收到的原藥品名稱",
                "summary": "⚠️ 與【阿斯匹靈、抗凝血劑】併用：會大幅增加嚴重胃出血的風險。\n⚠️ 與【類鴉片藥物、酒精】併用：會大幅增加呼吸抑制或嗜睡的風險。\n⚠️ 【胃部疾病、年滿60歲】患者：使用此藥引發嚴重出血的機率較高。"
            }}
        ]

        這是要翻譯的資料：
        {payload}
        """
    model = genai.GenerativeModel('gemini-2.5-flash')
    try:
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json"))
        translated_list = json.loads(response.text)
        return {item['drug_name']: item['summary'] for item in translated_list}
    except Exception as e:
        print(f"❌ 批次翻譯失敗：{e}")
        return {}

# ==========================================
# 主程式：大一統架構
# ==========================================
if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    IMAGE_PATH = os.path.join(BASE_DIR, "test_images", "sample1.JPG") 
    
    PERMIT_CSV = os.path.join(BASE_DIR, "data", "全部藥品許可證資料集.csv")
    NHI_CSV = os.path.join(BASE_DIR, "data", "健保用藥品項查詢檔.csv")
    APPEAR_CSV = os.path.join(BASE_DIR, "data", "藥品外觀資料集.csv")
    
    df_permit, df_nhi, df_appearance = load_databases(PERMIT_CSV, NHI_CSV, APPEAR_CSV)

    if df_permit is not None and df_nhi is not None:
        drugs_list = extract_drugs_from_image(IMAGE_PATH)
        
        if drugs_list:
            final_report_data = []
            drugs_to_translate = []

            for drug in drugs_list:
                # 取得三表整合的詳細資訊
                info = search_drug_full_info(df_permit, df_nhi, df_appearance, drug.get('search_keyword'), drug.get('nhi_code'))
                
                # 初始化報告單品資料
                report_item = {
                    "raw_name": drug.get('drug_name_raw', '未知藥名'),
                    "official_name": info["官方中文名"],
                    "indication": info["適應症"] if len(info["適應症"]) < 40 else info["適應症"][:38] + "...",
                    "pure_ingredient": info["純淨主成分"],
                    
                    "frequency": drug.get('frequency', '未註明'),     # 新增頻率
                    "days": drug.get('days', '未註明'),               # 新增天數
                    "total_amount": drug.get('total_amount', '未註明'), # 新增總數量
                    
                    "img_link": info["外觀連結"],
                    "match_type": info["比對方式"],
                    "fda_result": "無資料" 
                }
                
                # 查詢 FDA 交互作用
                if report_item["pure_ingredient"] != "無資料":
                    status, fda_raw_text = query_openfda_interactions(report_item["pure_ingredient"])
                    
                    if status == "HAS_CONFLICT":
                        # 收集起來等一下整批丟給 Gemini 翻譯
                        drugs_to_translate.append({
                            "drug_name": report_item["raw_name"],
                            "english_text": fda_raw_text
                        })
                    else:
                        report_item["fda_result"] = "無交互衝突" if status == "NO_CONFLICT" else "無資料"
                
                final_report_data.append(report_item)

            # 執行批次翻譯
            translations_dict = batch_translate_fda_warnings(drugs_to_translate)

            # 把翻譯結果塞回報告裡
            for data in final_report_data:
                name = data["raw_name"]
                if name in translations_dict:
                    data["fda_result"] = translations_dict[name]

            # 印出最終完美報告
            print("\n" + "="*60)
            print(" 🏥 藥單最終解析報告 (含外觀辨識) ")
            print("="*60)
            for i, data in enumerate(final_report_data, 1):
                print(f"💊 藥品 {i}:")
                print(f"   ► 原藥單名 : {data['raw_name']}")
                print(f"   ► 官方藥名 : {data['official_name']}")
                print(f"   ► 適應症   : {data['indication']}")
                print(f"   ► 純成分   : {data['pure_ingredient']}")
                print(f"   ► 服藥指示 : {data['frequency']} (共 {data['days']}，總計 {data['total_amount']})") # 🌟 組合排版看起來最專業！
                print(f"   ► 外觀連結 : {data['img_link']}")
                
                fda_out = data['fda_result'].replace('\n', '\n     ')
                print(f"   ► FDA資料  : \n     {fda_out}")
                print("-" * 60)