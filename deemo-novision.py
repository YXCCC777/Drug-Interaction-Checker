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
    """步驟 1 & 2 合併：讓 Gemini 直接看圖片並抓出所有藥品"""
    print("👀 啟動 Gemini 多模態視覺神經網路，直接解析圖片表格...")
    
    img = Image.open(image_path)
    
    # 🔥 修改 1：在提示詞中新增「total_quantity (總量)」欄位
    prompt = """
    這是一張台灣醫療院所開立的藥單照片。請仔細觀察圖片中的「藥品名稱與劑量單位」表格區塊。
    
    請幫我擷取表格中的**所有**藥品，並嚴格整理成一個 JSON 清單 (JSON List of Objects)。
    清單中的每個藥品物件需要包含以下欄位：
    {
        "drug_name_tw": "藥品中文或原始名稱（圖片上顯示的名字）",
        "drug_name_en": "藥品英文學名（Generic Name）。請務必將圖片上的藥名轉成 openFDA 查得到的英文學名",
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
    """步驟 3: 將藥名丟給 openFDA 查詢交互作用資訊，並精簡字數"""
    url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:\"{drug_name_en}\"&limit=1"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        try:
            results = data.get("results", [])
            if not results:
                 return "查無此藥物的 Label 資料。"
            interactions_raw = results[0].get("drug_interactions", [])
            if not interactions_raw:
                return "查無具體的藥物交互作用說明欄位。"
            
            # 將結果轉成純文字字串
            if isinstance(interactions_raw, list):
                combined_text = "\n".join(interactions_raw)
            else:
                combined_text = str(interactions_raw)
            
            # 🔥 修改 2：精簡文字！只保留前 1000 個字元，剩下的卡掉
            if len(combined_text) > 1000:
                return combined_text[:1000] + "\n\n...(原文過長，系統已自動截斷精簡)..."
            
            return combined_text

        except KeyError:
            return "查無具體的藥物交互作用說明欄位。"
    else:
        return f"openFDA 找不到此藥物或 API 呼叫失敗。 (HTTP {response.status_code})"

def translate_interactions_with_llm(drug_tw, drug_en, raw_interactions):
    """步驟 4: 藥師白話文翻譯"""
    prompt = f"""
    你現在是一位專業但親切的台灣藥師。
    以下是從美國 FDA 資料庫查到的關於藥品「{drug_tw} ({drug_en})」的藥物交互作用原始英文資料：
    ---
    {raw_interactions}
    ---
    請幫我把這段資料翻譯成「一般台灣民眾能輕鬆看懂的繁體中文」，並進行摘要。
    請務必使用以下格式輸出（使用 Markdown 條列式排版）：
    
    ### 🏥 【{drug_tw} ({drug_en})】用藥安全提醒
    * ⚠️ **主要警告**：(用一句話總結最危險的交互作用)
    * 💊 **應避免一起服用的藥物或食物**：(列出重點清單)
    * 👨‍⚕️ **藥師白話建議**：(一般人平常吃這款藥該注意什麼)
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    return response.text

# --- 主程式執行區 ---
if __name__ == "__main__":
    test_image = "sample_prescription2.JPG" 
    
    if not os.path.exists(test_image):
        print(f"請準備一張名為 {test_image} 的照片放在專案資料夾下！")
    else:
        try:
            structured_drugs_list = extract_drugs_from_image(test_image)
            
            print(f"\n--- 1. Gemini 直接視覺解析結果 (共抓取到 {len(structured_drugs_list)} 項藥品) ---")
            print(json.dumps(structured_drugs_list, indent=4, ensure_ascii=False))
            
            count = 1
            for drug_info in structured_drugs_list:
                drug_tw = drug_info.get("drug_name_tw", "")
                drug_en = drug_info.get("drug_name_en", "")
                
                print(f"\n>>>>>>>>> 正在處理第 {count} 項藥品: {drug_tw} <<<<<<<<<")

                if drug_en:
                    print(f"啟動 openFDA 查詢：{drug_en} 的交互作用...")
                    interactions_info = query_openfda_interactions(drug_en)
                    
                    if "查無" not in interactions_info and "找不到" not in interactions_info:
                        print("啟動 Gemini 藥師翻譯與摘要系統...")
                        translated_info = translate_interactions_with_llm(drug_tw, drug_en, interactions_info)
                        print("\n💡 系統最終輸出：民眾版衛教資訊")
                        print(translated_info)
                    else:
                        print(f"\n💡 系統提示: 藥品【{drug_tw}】{interactions_info} (略過翻譯步驟)")
                else:
                    print(f"\n💡 系統提示: 藥品【{drug_tw}】未成功辨識出英文學名，無法查詢 openFDA。")
                
                count += 1
                
        except Exception as e:
            print(f"發生錯誤: {e}")