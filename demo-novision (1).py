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
    # 確保這裡的 URL 是乾淨的，沒有混入 Markdown 的超連結符號 []()
    # 把網址拆成兩半，徹底防止編輯器自動把它變成超連結！
    base_url = "https://api.fda.gov/drug/label.json"
    url = f"{base_url}?search=openfda.generic_name:\"{drug_name_en}\"&limit=1"
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
            
            if isinstance(interactions_raw, list):
                combined_text = "\n".join(interactions_raw)
            else:
                combined_text = str(interactions_raw)
            
            if len(combined_text) > 1000:
                return combined_text[:1000] + "\n\n...(原文過長，系統已自動截斷精簡)..."
            
            return combined_text

        except KeyError:
            return "查無具體的藥物交互作用說明欄位。"
    else:
        return f"openFDA 找不到此藥物或 API 呼叫失敗。 (HTTP {response.status_code})"

def summarize_all_interactions(interactions_dict):
    """步驟 4：使用自定義固定格式進行總結"""
    print("\n🧠 [Gemini 啟動] 正在依照您的固定格式整理總結清單...")
    
    # 這裡定義你想要的「固定格式」範本
    my_format_template = """
    === 💊 [藥物中文名] ([英文學名]) ===
    * 🛑 【禁忌成分】：(舉例含有此成分食品)
    * ⚠️ 【結果】：(請用一句話白話解釋後果)
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
    test_image = "sample_prescription2.JPG" 
    
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
                
                print(f"\n🔍 正在查詢 FDA [{count}/{len(structured_drugs_list)}]: {drug_tw}...")

                if drug_en:
                    interactions_info = query_openfda_interactions(drug_en)
                    if "查無" not in interactions_info and "找不到" not in interactions_info:
                        print(f"   ✅ 成功抓取 FDA 資料，已存入暫存區！")
                        # 找到資料就先存起來，不要翻譯！
                        collected_interactions[drug_tw] = interactions_info 
                    else:
                        print(f"   💡 系統提示: {interactions_info}")
                else:
                    print(f"   💡 未成功辨識出英文學名。")
                
                count += 1
                
            # 迴圈跑完後，一次把所有資料送給 Gemini 總結！
            if collected_interactions:
                print("\n==================================================")
                print("🚀 FDA 資料收集完畢！準備進行最終統整翻譯...")
                final_summary = summarize_all_interactions(collected_interactions)
                print("\n✨ 系統最終輸出：民眾版衛教資訊")
                print(final_summary)
            else:
                print("\n🎉 太棒了！這張藥單上的藥物，目前沒有在 FDA 查到需要特別注意的交互作用資料。")
                
        except Exception as e:
            print(f"發生錯誤: {e}")