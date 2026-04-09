import os
import json
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# 載入環境變數
load_dotenv()

# 初始化 Google Gemini API 客戶端
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_drugs_from_image(image_path):
    img = Image.open(image_path)
    
    # 🌟 強化版 Prompt：嚴格要求只給「純英文有效成分」
    prompt = """
    這是一張台灣醫療院所開立的藥單照片。請仔細觀察圖片中的「藥品名稱與劑量單位」表格區塊。
    
    請幫我擷取表格中的**所有**藥品，並嚴格整理成一個 JSON 清單。
    清單中的每個藥品物件需要包含以下欄位：
    {
        "drug_name_tw": "藥品中文或原始名稱（圖片上顯示的名字）",
        "drug_name_en": "藥物的純粹英文有效成分 (Active Ingredient)。⚠️非常重要：請務必去除所有劑量(如 500mg)、劑型(如 Tablet/Capsule)、鹽類綴詞(如 Hydrochloride/Maleate)，只保留最核心的英文學名單字，否則資料庫會查不到！",
        "frequency": "服用方法（例如：'每日一次'）",
        "quantity": "數量（例如：'1'）",
        "days": "天數（例如：'7'）",
        "total_quantity": "總量（例如表格上的 '7' 或 '14'）"
    }
    
    只輸出純 JSON 清單資料，絕對不要包含任何 Markdown 標籤 (例如 ```json ) 或其他廢話。
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(
        [prompt, img],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
    )
    
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        print(f"Gemini 輸出的 JSON 解析失敗！\n{response.text}")
        raise e

def query_openfda_interactions(drug_name_en):
    # 確保轉成小寫，並去除前後多餘的空白，以符合 openFDA 搜尋習慣
    clean_drug_name = drug_name_en.strip().lower()
    
    base_url = "[https://api.fda.gov/drug/label.json](https://api.fda.gov/drug/label.json)"
    url = f"{base_url}?search=openfda.generic_name:\"{clean_drug_name}\"&limit=1"
    
    try:
        # 加上 timeout 避免網路卡住
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            # 如果 FDA 回傳成功，但裡面沒有結果
            if not results:
                 return "查無資料"
                 
            # 嘗試抓取交互作用欄位
            interactions_raw = results[0].get("drug_interactions", [])
            
            # 如果這顆藥剛好沒有填寫交互作用
            if not interactions_raw:
                return "查無資料"
            
            # 成功抓到資料，進行字串整理
            if isinstance(interactions_raw, list):
                combined_text = "\n".join(interactions_raw)
            else:
                combined_text = str(interactions_raw)
            
            if len(combined_text) > 1000:
                return combined_text[:1000] + "\n\n...(原文過長自動截斷)..."
            
            return combined_text
            
        else:
            # 如果 HTTP 狀態碼不是 200 (例如 404 找不到)
            return "查無資料"

    except Exception as e:
        print(f"    ⚠️ 呼叫 openFDA 時發生錯誤: {e}")
        return "查無資料"

def summarize_all_interactions(interactions_dict):
    """步驟 4：使用自定義固定格式進行總結"""
    print("\n [Gemini 啟動] 正在依照您的固定格式整理總結清單...")
    
    # 這裡定義你想要的「固定格式」範本
    my_format_template = """
    ===  [藥物中文名] ([英文學名]) ===
    *  【禁忌成分】：(舉例含有此成分食品)
    *  【結果】：(請用一句話白話解釋後果)
    -------------------------------------------
    """

    prompt = f"""
    你現在是一位專業的台灣藥師。
    以下是我從美國 FDA 資料庫查到的藥物交互作用原始資料：
    ---
    """
    for drug_tw, raw_interactions in interactions_dict.items():
        prompt += f"【{drug_tw}】\n{raw_interactions}\n\n"
        
    prompt += f"""
    ---
    請幫我根據以上資料進行總結。
    **嚴格遵守以下輸出規則**：
    1. 每一項藥物都必須嚴格遵守這個格式：
    {my_format_template}
    2. 如果某項藥物有多個禁忌成分，請在「禁忌成分」欄位用逗號隔開。
    3. 文字要讓台灣一般大眾（甚至是長輩）都能一眼看懂。
    4. 絕對不要輸出 Markdown 以外的廢話。
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    return response.text

# --- 主程式執行區 ---
if __name__ == "__main__":
    test_image ="test_images/sample1.JPG"

    if not os.path.exists(test_image):
        print(f"請準備一張名為 {test_image} 的照片放在專案資料夾下！")
    else:
        try:
            structured_drugs_list = extract_drugs_from_image(test_image)
            print(f"\n--- 1. Gemini 直接視覺解析結果 (共抓取到 {len(structured_drugs_list)} 項藥品) ---")
            
            # ✅ 這裡保留了你要的 JSON 輸出，方便你核對抓取的結果！
            print(json.dumps(structured_drugs_list, indent=4, ensure_ascii=False))
            
            # 準備一個空字典，用來「暫存」FDA 查到的所有資料
            collected_interactions = {} 
            
            count = 1
            for drug_info in structured_drugs_list:
                drug_tw = drug_info.get("drug_name_tw", "")
                drug_en = drug_info.get("drug_name_en", "")
                
                print(f"\n 正在查詢 FDA [{count}/{len(structured_drugs_list)}]: {drug_tw}...")

                if drug_en:
                    interactions_info = query_openfda_interactions(drug_en)
                    if "查無" not in interactions_info and "找不到" not in interactions_info:
                        print(f"    成功抓取 FDA 資料，已存入暫存區！")
                        # 找到資料就先存起來，不要翻譯！
                        collected_interactions[drug_tw] = interactions_info 
                    else:
                        print(f"    系統提示: {interactions_info}")
                else:
                    print(f"    未成功辨識出英文學名。")
                
                count += 1
                
            # 迴圈跑完後，一次把所有資料送給 Gemini 總結！
            if collected_interactions:
                print("\n==================================================")
                print(" FDA 資料收集完畢！準備進行最終統整翻譯...")
                final_summary = summarize_all_interactions(collected_interactions)
                print("\n 系統最終輸出：民眾版衛教資訊")
                print(final_summary)
            else:
                print("\n無交互作用")
                
        except Exception as e:
            print(f"發生錯誤: {e}")